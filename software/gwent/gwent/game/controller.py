from typing import Callable, List

import asyncio_mqtt

import gwent.game.errors
import gwent.game.stages.all
import gwent.messaging.base
import gwent.messaging.card
import gwent.messaging.card_play
import gwent.messaging.ctrl
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.choice
import gwent.messaging.sfx
import gwent.game
import gwent.hal.sfx


PLAYER_ONE = "player1"
PLAYER_TWO = "player2"


class Controller(gwent.game.PubSubComponent):
    active_stage = None
    register_leaders = None
    register_decks = None

    def __init__(self, loop, pubsub: asyncio_mqtt.Client):
        super().__init__(loop, pubsub)
        self.main_menu = gwent.game.stages.all.MainMenu(self._loop, self._pubsub)
        self.register_leaders = gwent.game.stages.all.RegisterLeaders(self._loop, self._pubsub)
        self.register_decks = gwent.game.stages.all.RegisterDecks(self._loop, self._pubsub)

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
        # await self.start_music()
        await super().run()

    async def set_active_stage(self, st: gwent.game.stages.base.GameStage, completed: Callable,
                               cancel: Callable):
        if self.active_stage is not None:
            await self.active_stage.deactivate()

        self.active_stage = st
        await self.active_stage.activate(completed, cancel)

    async def start_music(self):
        self._log.info('Starting music')
        await self.publish_music(music=gwent.messaging.sfx.MUSIC1)

    async def start_main_menu(self):
        self._log.info('Starting main menu stage')

        async def complete():
            self._log.info('main menu completed')
            await self.start_register_leaders()

        async def cancel():
            self._log._error("main menu can't be canceled")

        await self.set_active_stage(self.main_menu, complete, cancel)

    async def publish_card_play(
            self, player:str, card: gwent.messaging.card.Message):
        ch = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, player)
        cp = gwent.messaging.card_play.Message.with_add_to_deck(player, card)
        await self.publish(ch, cp)

    async def start_register_leaders(self):
        self._log.info('Starting register leaders stage')

        async def complete(leader1: gwent.messaging.card.Message,
                           leader2: gwent.messaging.card.Message):
            self._log.info({
                'action': 'complete register_leaders',
                'leader1': leader1.full_name,
                'leader2': leader2.full_name,
            })
            await self.publish_card_play(PLAYER_ONE, leader1)
            await self.publish_card_play(PLAYER_TWO, leader2)
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
