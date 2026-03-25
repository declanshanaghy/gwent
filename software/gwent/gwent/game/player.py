import random
import gwent.game
import gwent.messaging.card_play
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.matrix

from gwent.game.constants import PLAYER


class Player(gwent.game.PubSubComponent):

    def __init__(self, player: PLAYER, pubsub, mux_channel):
        super().__init__(pubsub)
        self._player = player
        self._leader = None
        self._score = 0
        self._deck = []
        
        self._mux_channel = mux_channel
        self._channel_cards = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(self._player))
        self._channel_ctrl = gwent.game.make_channel(gwent.game.CH_CTRL)

    def init(self):
        super().init()
        self._matrix = gwent.hal.matrix.instance(channel=self._mux_channel)
        self._matrix.init()
        self.subscribe(self._channel_cards, gwent.messaging.card_play.KIND,
                       self.process_card_play)
        self.subscribe(self._channel_ctrl, gwent.messaging.ctrl.KIND,
                       self.process_ctrl)
        
        # Display initial score of zero
        self._update_display()

    def shutdown(self):
        self.unsubscribe(self._channel_cards)
        self.unsubscribe(self._channel_ctrl)
        self._matrix.shutdown()
        super().shutdown()
    
    def _update_display(self):
        """
        Update the score display with a centered digit and dots
        The number of dots displayed depends on which player this is
        """
        self._log.info(f"Updating display with score: {self._score}")
        
        # Use the display_centered_score method from the matrix class
        # Pass the player parameter to determine dot display
        self._matrix.display_centered_score(self._score, self._player)

    def process_ctrl(self, cp: gwent.messaging.ctrl.Message):
        self._log.info(f'received {cp.kind}', extra=cp.to_object())
        
        if cp.subkind == gwent.messaging.ctrl.STAGE:
            if cp.stage == gwent.messaging.ctrl.STAGE_MAIN_MENU:
                # When game starts, display initial score of zero
                self._score = 0
                self._update_display()
            else:
                self._log.debug(f'Unhandled stage: {cp.stage}')
        else:
            self._log.debug(f'Unhandled subkind: {cp.subkind}')

    def process_card_play(self, cp: gwent.messaging.card_play.Message):
        self._log.info({
            'action': f'received {cp.kind}',
            'subkind': cp.subkind,
            'faction': cp.card.faction,
            'name': cp.card.name,
            'strength': cp.card.strength,
        })

        if cp.subkind == gwent.messaging.card_play.ADD_TO_DECK:
            if cp.card.is_leader:
                self._leader = cp.card
                self._log.info(f"Stored leader", extra={"card": cp.card.to_object()})
            else:
                self._deck.append(cp.card)
                self._log.info(f"Added card to deck", extra={"card": cp.card.to_object()})

        elif cp.subkind == gwent.messaging.card_play.UPDATE_SCORE:
            score = cp._instance.get(gwent.messaging.card_play.SCORE, 0)
            self._score = score
            self._log.info(f"Score updated to {score}")
            self._update_display()

        else:
            self._log.debug(f'Unhandled subkind: {cp.subkind}')
