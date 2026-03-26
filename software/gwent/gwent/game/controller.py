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
        self.main_menu = gwent.game.stages.all.MainMenu(pubsub)
        self.register_leaders = gwent.game.stages.all.RegisterLeaders(pubsub)
        self.register_decks = gwent.game.stages.all.RegisterDecks(pubsub)
        self.deal_cards = gwent.game.stages.all.DealCards(pubsub)
        self.play_round = gwent.game.stages.all.PlayRound(pubsub)
        self.round_end = gwent.game.stages.all.RoundEnd(pubsub)
        self.build_deck = gwent.game.stages.all.BuildDeck(pubsub)
        self.display_winner = gwent.game.stages.all.DisplayWinner(pubsub)

    def init(self):
        super().init()
        # Initialize all stages so they subscribe to sfx/complete
        self.main_menu.init()
        self.register_leaders.init()
        self.register_decks.init()
        self.deal_cards.init()
        self.play_round.init()
        self.round_end.init()
        self.build_deck.init()
        self.display_winner.init()

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
        # self.start_music()
        gwent.game.decks.ensure_starter_decks()
        self.start_main_menu()
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

        def complete(choice):
            self._log.info(f'main menu completed with choice: {choice}')
            if choice == 'build_deck':
                self.start_build_deck()
            else:
                self.start_game_from_decks()

        def cancel():
            self._log.error("main menu can't be canceled")

        self.set_active_stage(self.main_menu, complete, cancel)

    def start_game_from_decks(self):
        self._log.info('Starting game from saved decks')

        result = gwent.game.decks.pick_two_random_decks()
        if result is None:
            self._log.error('Not enough saved decks with different factions')
            self.publish_error(
                "Need 2+ saved decks with different factions. "
                "Use Build Deck first.")
            self.start_main_menu()
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

    def start_build_deck(self):
        self._log.info('Starting build deck stage')

        def complete(owner, faction, deck):
            filepath = gwent.game.decks.save_deck(owner, faction, deck)
            self._log.info({
                'action': 'deck_saved',
                'owner': owner,
                'faction': faction,
                'cards': len(deck),
                'filepath': filepath,
            })
            self.publish_prompt(
                f"Deck saved! {owner}'s {faction} ({len(deck)} cards)",
                ok=True, cancel=False, clear_choices=True)
            self.start_main_menu()

        def cancel():
            self._log.info('Build deck canceled')
            self.start_main_menu()

        self.set_active_stage(self.build_deck, complete, cancel)

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
                self.start_display_winner(board)
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

    def start_display_winner(self, board):
        self._log.info('Displaying match winner')

        def complete():
            self._log.info('Winner displayed, returning to menu')
            self.start_main_menu()

        def cancel():
            self.start_main_menu()

        self.set_active_stage(self.display_winner, complete, cancel, board)

    def process_card(self, message: gwent.messaging.card.Message):
        if self.active_stage:
            self.active_stage.process_card(message)

    def process_choice(self, message: gwent.messaging.choice.Message):
        if self.active_stage:
            self.active_stage.process_choice(message)
