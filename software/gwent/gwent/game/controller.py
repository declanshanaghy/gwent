from typing import Callable, List

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


ROUND_KEEPER = "round-keeper"

from enum import Enum

class PLAYER(Enum):
    ONE = "player1"
    TWO = "player2"

class Controller(gwent.game.ThreadComponent):
    active_stage = None
    register_leaders = None
    register_decks = None

    def __init__(self, pubsub):
        super().__init__(pubsub)
        self.main_menu = gwent.game.stages.all.MainMenu(self._pubsub)
        self.register_leaders = gwent.game.stages.all.RegisterLeaders(self._pubsub)
        self.register_decks = gwent.game.stages.all.RegisterDecks(self._pubsub)

    def init(self):
        super().init()
        self.subscribe(gwent.game.CH_CARDS_RAW_READ,
                       gwent.messaging.card.KIND,
                       self.process_card)
        self.subscribe(gwent.game.CH_MFD_CHOOSE,
                       gwent.messaging.choice.KIND,
                       self.process_choice)

    def shutdown(self):
        self.unsubscribe(gwent.game.CH_CARDS_RAW_READ)
        self.unsubscribe(gwent.game.CH_MFD_CHOOSE)
        super().shutdown()

    def run(self):
        self.start_main_menu()
        self.start_music()
        super().run()

    def set_active_stage(self, st, completed: Callable, cancel: Callable, *args, **kwargs):
        if self.active_stage is not None:
            self.active_stage.deactivate()

        self.active_stage = st
        self.active_stage.activate(completed, cancel, *args, **kwargs)

    def start_music(self):
        self._log.info('Starting music')
        self.publish_music(music=gwent.messaging.sfx.MUSIC1)

    def start_main_menu(self):
        self._log.info('Starting main menu stage')

        def complete():
            self._log.info('main menu completed')
            self.start_register_leaders()

        def cancel():
            self._log.error("main menu can't be canceled")

        self.set_active_stage(self.main_menu, complete, cancel)

    def publish_card_play(self, player: PLAYER, card: gwent.messaging.card.Message):
        ch = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        cp = gwent.messaging.card_play.Message.with_add_to_deck(str(player), card)
        self.publish(ch, cp)

    def start_register_leaders(self):
        self._log.info('Starting register leaders stage')

        def complete(leader1: gwent.messaging.card.Message,
                     leader2: gwent.messaging.card.Message):
            self._log.info({
                'action': 'completed register_leaders',
                'leader1': leader1.full_name,
                'leader2': leader2.full_name,
            })
            self.start_register_decks(leader1, leader2)

        def cancel():
            self._log.info('Register leaders canceled')
            self.start_main_menu()

        self.set_active_stage(self.register_leaders, complete, cancel)

    def start_register_decks(self, leader1: gwent.messaging.card.Message, leader2: gwent.messaging.card.Message):
        self._log.info('Starting register decks stage')

        def complete(deck1_name: str, deck2_name: str):
            self._log.info({
                'action': 'complete register_decks',
                'deck1': deck1_name,
                'deck2': deck2_name,
            })
            self.start_main_menu()

        def cancel():
            self._log.info('Register decks canceled')
            self.start_main_menu()

        self.set_active_stage(self.register_decks, complete, cancel, leader1, leader2)

    def process_card(self, message: gwent.messaging.card.Message):
        if self.active_stage:
            self.active_stage.process_card(message)

    def process_choice(self, message: gwent.messaging.choice.Message):
        if self.active_stage:
            self.active_stage.process_choice(message)
