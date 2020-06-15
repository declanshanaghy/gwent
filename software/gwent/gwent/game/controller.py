import collections
from typing import Callable, List

import asyncio_mqtt

import gwent.game.errors
import gwent.messaging.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.choice
import gwent.messaging.sfx
import gwent.game
import gwent.hal.tts


class IGameStage(gwent.game.Component):
    async def activate(self, complete: Callable, cancel: Callable):
        self.complete = complete
        self.cancel = cancel
        await self.publish_game_stage(active=True)

    async def deactivate(self):
        await self.publish_game_stage(active=False)

    async def publish_game_stage(self, active: bool):
        ctrl = gwent.messaging.ctrl.Message.with_stage(
            self.stage, active=active)
        await self.publish(gwent.game.CH_GAMESTAGE, ctrl)

    @property
    def stage(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement '
                                  f'stage')

    async def process_card(self, card: gwent.messaging.card.Message):
        self._log.debug({
            'action': 'received card',
            'kind': card.kind,
            'faction': card.faction,
            'full_name': card.full_name,
            'rfid': card.rfid,
        })

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        self._log.debug({
            'action': 'received choice',
            'id': choice.id,
            'text': choice.text,
        })


class Controller(gwent.game.Component):
    active_stage = None
    register_leaders = None
    register_decks = None

    def __init__(self, loop, pubsub: asyncio_mqtt.Client):
        super().__init__(loop, pubsub)
        self.main_menu = MainMenuStage(self._loop, self._pubsub)
        self.register_leaders = RegisterLeadersStage(self._loop, self._pubsub)
        self.register_decks = RegisterDecksStage(self._loop, self._pubsub)

    async def init(self):
        await self.subscribe(gwent.game.CH_CARDS_RAW_READ,
                             gwent.messaging.card.KIND,
                             self.process_card)
        await self.subscribe(gwent.game.CH_MFD_CHOOSE,
                             gwent.messaging.choice.KIND,
                             self.process_choice)

    async def shutdown(self):
        await self.unsubscribe(gwent.game.CH_CARDS_RAW_READ)
        await self.unsubscribe(gwent.game.CH_MFD_CHOOSE)

    async def run(self):
        await self.start_main_menu()
        await super().run()

    async def set_active_stage(self, st: IGameStage, completed: Callable,
                               cancel: Callable):
        if self.active_stage is not None:
            await self.active_stage.deactivate()

        self.active_stage = st
        await self.active_stage.activate(completed, cancel)

    async def start_main_menu(self):
        self._log.info('Starting main menu stage')

        async def complete():
            self._log.info('main menu completed')
            await self.start_register_leaders()

        async def cancel():
            self._log._error("main menu can't be canceled")
            pass

        await self.set_active_stage(self.main_menu, complete, cancel)

    async def start_register_leaders(self):
        self._log.info('Starting register leaders stage')

        async def complete(leader1: gwent.messaging.card.Message,
                           leader2: gwent.messaging.card.Message):
            self._log.info({
                'action': 'complete register_leaders',
                'leader1': leader1.full_name,
                'leader2': leader2.full_name,
            })
            await self.start_register_decks()

        async def cancel():
            self._log.info('Register leaders canceled')
            await self.start_main_menu()

        await self.set_active_stage(self.register_leaders, complete, cancel)

    async def start_register_decks(self):
        self._log.info('Starting register decks stage')

        async def complete(deck1: List[gwent.messaging.card.Message],
                           deck2: List[gwent.messaging.card.Message]):
            self._log.info({
                'action': 'complete register_decks',
                'deck1': deck1[0].full_name,
                'deck2': deck2[0].full_name,
            })
            await self.start_main_menu()

        async def cancel():
            self._log.info('Register decks canceled')
            await self.start_main_menu()

        await self.set_active_stage(self.register_decks, complete, cancel)

    async def process_card(self, message: gwent.messaging.card.Message):
        await self.active_stage.process_card(message)

    async def process_choice(self, message: gwent.messaging.choice.Message):
        await self.active_stage.process_choice(message)


class RegisterDecksStage(IGameStage):
    _decks = None

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGSITER_DECKS

    async def activate(self, complete: Callable, cancel: Callable):
        await super().activate(complete, cancel)
        self._decks = collections.OrderedDict()
        await self.publish_start_prompt()

    async def publish_start_prompt(self):
        prompt = gwent.messaging.mfd.Message.with_prompt(
            prompt="Players...Register your decks",
            ok=True, cancel=True, clear_choices=True)
        await self.publish(gwent.game.CH_MFD_PRESENT, prompt)


class RegisterLeadersStage(IGameStage):
    _leaders = None

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_REGSITER_LEADERS

    async def activate(self, complete: Callable, cancel: Callable):
        await super().activate(complete, cancel)
        self._leaders = collections.OrderedDict()
        await self.publish_start_prompt()

    async def publish_start_prompt(self):
        prompt = gwent.messaging.mfd.Message.with_prompt(
            prompt="Players...Register your leaders",
            ok=True, cancel=True, clear_choices=True)
        await self.publish(gwent.game.CH_MFD_PRESENT, prompt)

    async def publish_error(self, error: str):
        e = gwent.messaging.mfd.Message.with_error(error=error)
        await self.publish(gwent.game.CH_MFD_PRESENT, e)

    async def publish_prompt(self, prompt: str):
        p = gwent.messaging.mfd.Message.with_prompt(prompt=prompt)
        await self.publish(gwent.game.CH_MFD_PRESENT, p)

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        await super().process_choice(choice)

        if choice.id == gwent.messaging.choice.OK:
            if len(self._leaders) < 2:
                await self.publish_error('2 Leaders are not registered yet!')
            else:
                leaders = [l for l in self._leaders.values()]
                await self.complete(leaders[0], leaders[1])
        elif choice.id == gwent.messaging.choice.CANCEL:
            await self.cancel()

    async def process_card(self, card: gwent.messaging.card.Message):
        await super().process_card(card)

        if not card.is_leader:
            await self.publish_error(f'{card.name} is not a leader')
            return

        if card.faction in self._leaders:
            self._leaders[card.faction] = card
            await self.publish_prompt(
                f'Replaced {card.faction} leader: {card.name}')
            return

        if len(self._leaders.keys()) < 2:
            self._leaders[card.faction] = card
            await self.publish_prompt(
                f'Player {len(self._leaders)} new leader: {card.name}')
            return
        else:
            await self.publish_error(
                f'{card.faction} is not in this game')


class MainMenuStage(IGameStage):
    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_MAIN_MENU

    async def activate(self, complete: Callable, cancel: Callable):
        await super().activate(complete, cancel)
        await self.publish_main_menu()

    async def publish_main_menu(self):
        choices = [
            gwent.messaging.choice.Message.from_properties(
                '1', 'Start Game')
        ]
        mfd = gwent.messaging.mfd.Message.with_choices(
            choices, clear_prompt=True)
        await self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    async def process_choice(self, choice: gwent.messaging.choice.Message):
        await super().process_choice(choice)
        await self.complete()
