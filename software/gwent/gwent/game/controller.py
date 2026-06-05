from typing import Callable, List

import paho.mqtt.client as mqtt

import gwent.game.errors
import gwent.game.decks
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

from gwent.game.constants import PLAYER


class Controller(gwent.game.PubSubComponent):
    active_stage = None

    def __init__(self, pubsub: mqtt.Client):
        super().__init__(pubsub)
        self.register_leaders = gwent.game.stages.all.RegisterLeaders(pubsub)
        self.register_decks = gwent.game.stages.all.RegisterDecks(pubsub)
        self.deal_cards = gwent.game.stages.all.DealCards(pubsub)
        self.play_round = gwent.game.stages.all.PlayRound(pubsub)
        self.round_end = gwent.game.stages.all.RoundEnd(pubsub)
        self.game_over = gwent.game.stages.all.GameOver(pubsub)

    def init(self):
        super().init()
        # Initialize all stages so they subscribe to sfx/complete
        self.register_leaders.init()
        self.register_decks.init()
        self.deal_cards.init()
        self.play_round.init()
        self.round_end.init()
        self.game_over.init()

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
        self.start_music()
        if not getattr(self, '_skip_main_menu', False):
            self.start_main_menu()
        super().run()

    def set_active_stage(self, st, completed: Callable, cancel: Callable, *args, **kwargs):
        if self.active_stage is not None:
            self.active_stage.deactivate()
        self.active_stage = st
        self.active_stage.activate(completed, cancel, *args, **kwargs)

    def start_music(self):
        self._log.info('Starting random music')
        self.publish_music()  # random track from software/data/music/

    def start_main_menu(self):
        """There is no choice screen — go straight into a fresh random deal.

        Kept under the old name so every caller (startup, GameOver complete,
        in-game-menu reset) lands here unchanged."""
        self._log.info('start_main_menu: auto-starting a random deal')
        self.start_game_from_decks()

    def start_game_from_decks(self):
        self._log.info('Starting game from saved decks')

        result = gwent.game.decks.pick_two_random_decks(
            owner_filter=getattr(self, '_owner_filter', None))
        if result is None:
            # Do NOT call start_main_menu() here — it now routes straight
            # back into this method and would recurse forever.
            self._log.error('Not enough saved decks with different factions')
            self.publish_error(
                "Need 2+ factions with cards. "
                "Use write_next to chip cards first.")
            return

        deck1_data, deck2_data = result
        self._log.info({
            'action': 'decks_selected',
            'deck1_faction': deck1_data['faction'],
            'deck1_owner': deck1_data['owner'],
            'deck1_cards': len(deck1_data['cards']),
            'deck2_faction': deck2_data['faction'],
            'deck2_owner': deck2_data['owner'],
            'deck2_cards': len(deck2_data['cards']),
        })

        # DealCards will supplement missing leaders/cards from starters
        self.start_deal_cards(deck1_data['cards'], deck2_data['cards'])

    def publish_card_play(self, player: PLAYER, card: gwent.messaging.card.Message):
        ch = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
        cp = gwent.messaging.card_play.Message.with_add_to_deck(str(player), card)
        self.publish(ch, cp)

    def start_register_leaders(self):
        self._log.info('Starting register leaders stage')

        def complete(leader1, leader2):
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

    def start_register_decks(self, leader1, leader2):
        self._log.info('Starting register decks stage')

        def complete(deck1, deck2):
            self._log.info({
                'action': 'complete register_decks',
                'deck1_size': len(deck1),
                'deck2_size': len(deck2),
            })
            self.start_deal_cards(deck1, deck2)

        def cancel():
            self._log.info('Register decks canceled')
            self.start_register_leaders()

        self.set_active_stage(self.register_decks, complete, cancel, leader1, leader2)

    def start_deal_cards(self, deck1, deck2):
        self._log.info({
            'action': 'start_deal_cards',
            'deck1_size': len(deck1),
            'deck2_size': len(deck2),
        })

        # Single choke point for every game-start route (random, fresh,
        # wizard, LLM): record the game when the camera is on. Fail-soft —
        # never blocks or breaks the deal.
        cc = getattr(self, 'camera_client', None)
        if cc is not None:
            cc.try_start_recording()

        def complete(deck1, hand1, deck2, hand2):
            self._log.info({
                'action': 'complete deal_cards',
                'deck1_size': len(deck1),
                'hand1_size': len(hand1),
                'deck2_size': len(deck2),
                'hand2_size': len(hand2),
            })
            self.start_play_round(deck1, hand1, deck2, hand2)

        def cancel():
            self._log.info('Deal cards canceled')
            self.start_register_decks(
                self.register_decks._leader1,
                self.register_decks._leader2)

        self.set_active_stage(self.deal_cards, complete, cancel, deck1, deck2)

    def start_play_round(self, deck1, hand1, deck2, hand2, board=None):
        self._log.info({
            'action': 'start_play_round',
            'deck1_size': len(deck1),
            'hand1_size': len(hand1),
            'deck2_size': len(deck2),
            'hand2_size': len(hand2),
            'existing_board': board is not None,
        })

        def complete(board):
            self._log.info({
                'action': 'complete play_round',
                'round': board.round_number,
            })
            self.start_round_end(board)

        def cancel():
            self._log.info('Play round canceled')
            self.start_main_menu()

        self.set_active_stage(self.play_round, complete, cancel,
                              deck1, hand1, deck2, hand2, board=board)

    def start_round_end(self, board):
        self._log.info({
            'action': 'start_round_end',
            'round': board.round_number,
            'p1_gems': board.players[PLAYER.ONE].gems,
            'p2_gems': board.players[PLAYER.TWO].gems,
        })

        def complete(board, game_over):
            if game_over:
                self._log.info('Game over!')
                self.start_game_over(board)
            else:
                self._log.info(f'Starting round {board.round_number}')
                self.start_play_round(
                    board.decks[PLAYER.ONE], board.hands[PLAYER.ONE],
                    board.decks[PLAYER.TWO], board.hands[PLAYER.TWO],
                    board=board)

        def cancel():
            self._log.info('Round end canceled')
            self.start_main_menu()

        self.set_active_stage(self.round_end, complete, cancel, board)

    def start_game_over(self, board):
        self._log.info('Displaying match winner')

        def complete():
            self._log.info('Winner displayed, returning to menu')
            self.start_main_menu()

        def cancel():
            self.start_main_menu()

        self.set_active_stage(self.game_over, complete, cancel, board)

    def process_card(self, message: gwent.messaging.card.Message):
        self.publish_effect("card")
        if self.active_stage:
            self.active_stage.process_card(message)

    def process_choice(self, message: gwent.messaging.choice.Message):
        # A pending camera eviction prompt gets first dibs on y/n answers
        # (rare: only when saved recordings fill the storage budget).
        cc = getattr(self, 'camera_client', None)
        if cc is not None and cc.process_choice(message):
            return
        if self.active_stage:
            self.active_stage.process_choice(message)
