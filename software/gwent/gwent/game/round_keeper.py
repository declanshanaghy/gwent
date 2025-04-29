import random
import gwent.game
import gwent.messaging.card_play
import gwent.messaging.ctrl
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.matrix


class RoundKeeper(gwent.game.ThreadComponent):

    def __init__(self, player: str, pubsub):
        super().__init__(pubsub)
        self._player = player
        self._mux_channel = gwent.hal.matrix.MATRIX_CHANNEL_PLAYER_ROUND_KEEPER
        self._channel = gwent.game.make_channel(gwent.game.CH_CTRL)

    def init(self):
        super().init()
        self._matrix = gwent.hal.matrix.instance(channel=self._mux_channel)
        self._matrix.init()
        self.subscribe(self._channel, gwent.messaging.ctrl.KIND, 
                       self.process_ctrl)

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

    def process_ctrl(self, cp: gwent.messaging.ctrl.Message):
        self._log.info(f'received {cp.kind}', extra=cp.to_object())
        
        if cp.subkind == gwent.messaging.ctrl.STAGE:
            if cp.stage == gwent.messaging.ctrl.STAGE_MAIN_MENU:
                self._update_display(0)
            elif cp.stage == gwent.messaging.ctrl.STAGE_REGISTER_LEADERS:
                self._update_display(1)
            else:
                self._log.error(f'Unhandled stage: {cp.stage}')
        else:
            self._log.error(f'Unhandled subkind: {cp.subkind}')
