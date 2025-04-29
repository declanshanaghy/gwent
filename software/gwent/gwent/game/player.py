import random
import gwent.game
import gwent.messaging.card_play
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.matrix


class Player(gwent.game.ThreadComponent):

    def __init__(self, player: str, pubsub, mux_channel=gwent.hal.matrix.MATRIX_CHANNEL_DEFAULT):
        super().__init__(pubsub)
        self._player = player
        self._mux_channel = mux_channel
        self._channel = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, self._player)

    def init(self):
        super().init()
        self._matrix = gwent.hal.matrix.instance(channel=self._mux_channel)
        self._matrix.init()
        self.subscribe(self._channel, gwent.messaging.card_play.KIND, 
                       self.process_card_play)

    def shutdown(self):
        self.unsubscribe(self._channel)
        self._matrix.shutdown()
        super().shutdown()
    
    def _update_display(self, score=None):
        """
        Update the score display
        """
        self._matrix.display_score(score)
        # self._matrix.display_score_animation(0, score)

    def process_card_play(self, cp: gwent.messaging.card_play.Message):
        self._log.info({
            'action': f'received {cp.kind}',
            'subkind': cp.subkind,
            'faction': cp.card.faction,
            'name': cp.card.name,
            'strength': cp.card.strength,
        })

        if cp.subkind == gwent.messaging.card_play.ADD_TO_DECK:
            self._update_display(random.randint(0, 100))
        else:
            self._log.error(f'Unhandled subkind: {cp.subkind}')
