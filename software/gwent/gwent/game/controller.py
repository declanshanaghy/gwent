import collections
from typing import Callable

import asyncio_mqtt

import gwent.game.errors
import gwent.messaging.base
import gwent.messaging.card
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.choice
import gwent.messaging.sfx
import gwent.game
import gwent.hal.tts


class IGameStage(gwent.game.Component):
    async def activate(self, completed:Callable, cancel:Callable):
        self.completed = completed
        self.cancel = cancel

    async def deactivate(self):
        pass

    async def process_card(self, card: gwent.messaging.card.Message):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'process_card')

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'process_card')


class Controller(gwent.game.Component):
    active_state = None
    register_players = None

    def __init__(self, loop, pubsub: asyncio_mqtt.Client):
        super().__init__(loop, pubsub)
        self.main_menu = MainMenuStage(self._loop, self._pubsub)
        self.register_players = RegisterPlayersStage(self._loop, self._pubsub)

    async def init(self):
        await self.subscribe(gwent.game.CH_CARDS_RAW_READ,
                             gwent.messaging.card.KIND,
                             self.process_card)
        await self.subscribe(gwent.game.CH_MFD_CHOICE,
                             gwent.messaging.choice.KIND,
                             self.process_choice)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_CARDS_RAW_READ)
        await self.unsubscribe(gwent.game.CH_MFD_CHOICE)

    async def run(self):
        await self.start_main_menu()
        await super().run()

    async def set_active_state(self, st: IGameStage, completed:Callable, cancel:Callable):
        if self.active_state is not None:
            await self.active_state.deactivate()

        self.active_state = st
        await self.active_state.activate(completed, cancel)

    async def start_main_menu(self):
        self._log.info('Starting main menu stage')
        async def completed():
            self._log.info('main menu completed')
            await self.start_register_players()

        async def cancel():
            self._log.error("main menu can't be canceled")
            pass

        await self.set_active_state(self.main_menu, completed, cancel)

    async def start_register_players(self):
        self._log.info('Starting register players stage')
        async def completed():
            raise NotImplementedError('next stage not implemented')

        async def cancel():
            self._log.info('Register players canceled')
            await self.start_main_menu()

        await self.set_active_state(self.register_players, completed, cancel)

    async def process_card(self, message: gwent.messaging.card.Message):
        await self.active_state.process_card(message)

    async def process_choice(self, message: gwent.messaging.choice.Message):
        await self.active_state.process_choice(message)


class MainMenuStage(IGameStage):
    async def activate(self, completed:Callable, cancel:Callable):
        await super().activate(completed, cancel)
        await self.publish_main_menu()

    async def publish_main_menu(self):
        choices = [
            gwent.messaging.choice.Message.from_properties(
                '1', 'Start Game')
        ]
        mfd = gwent.messaging.mfd.Message.with_choices(choices)
        await self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    async def process_choice(self, message: gwent.messaging.choice.Message):
        await self.completed()


class RegisterPlayersStage(IGameStage):
    PlayerDeck = collections.namedtuple('PlayerDeck',
                                        'faction leader cards')
    players = []

    async def activate(self, completed:Callable, cancel:Callable):
        await super().activate(completed, cancel)
        self.players = []
        await self.publish_main_prompt()

    async def publish_main_prompt(self):
        mfd = gwent.messaging.mfd.Message.with_prompt(
            prompt="Players...register your decks", ok=True, cancel=True)
        await self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    async def deactivate(self):
        pass

    def find_deck(self, faction: str):
        for deck in self.players:
            if deck.faction == faction:
                return deck

        if len(self.players) == 2:
            raise gwent.game.errors.InvalidFactionError(
                f'{faction} is not participating in this game')
        else:
            self.players.append(self.PlayerDeck(faction=faction,
                                                leader=None, cards=[]))

    async def process_card(self, card: gwent.messaging.card.Message):
        self._log.debug({
            'action': 'received card',
            'kind': card.kind,
            'faction': card.faction,
            'full_name': card.full_name,
            'rfid': card.rfid,
        })

        try:
            deck = self.find_deck(card.faction)
        except gwent.game.errors.InvalidFactionError as ex:
            await self.publish_error(ex.message)
