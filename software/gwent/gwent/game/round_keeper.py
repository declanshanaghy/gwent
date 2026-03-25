import gwent.game
import gwent.messaging.card_play
import gwent.messaging.ctrl
import gwent.messaging.factory
import gwent.hal.matrix

import paho.mqtt.client as mqtt

from gwent.game.constants import PLAYER


class RoundKeeper(gwent.game.PubSubComponent):
    """Gem display component. Shows each player's remaining gems on a shared
    LED matrix (mux channel 0). Listens for stage changes and gem updates."""

    def __init__(self, pubsub: mqtt.Client):
        super().__init__(pubsub)
        self._mux_channel = gwent.hal.matrix.MATRIX_CHANNEL_PLAYER_ROUND_KEEPER
        self._channel_ctrl = gwent.game.make_channel(gwent.game.CH_CTRL)
        self._channel_p1 = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(PLAYER.ONE))
        self._channel_p2 = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(PLAYER.TWO))
        self._p1_gems = 2
        self._p2_gems = 2

    def init(self):
        super().init()
        self._matrix = gwent.hal.matrix.instance(channel=self._mux_channel)
        self._matrix.init()
        self.subscribe(self._channel_ctrl, gwent.messaging.ctrl.KIND,
                       self.process_ctrl)
        self.subscribe(self._channel_p1, gwent.messaging.card_play.KIND,
                       self.process_card_play)
        self.subscribe(self._channel_p2, gwent.messaging.card_play.KIND,
                       self.process_card_play)
        self._update_display()

    def shutdown(self):
        self.unsubscribe(self._channel_ctrl)
        self.unsubscribe(self._channel_p1)
        self.unsubscribe(self._channel_p2)
        self._matrix.shutdown()
        super().shutdown()

    def _update_display(self):
        """Display both players' gems side by side."""
        self._log.info(f"Displaying gems: P1={self._p1_gems}, P2={self._p2_gems}")
        self._matrix.display_gem_pair(self._p1_gems, self._p2_gems)

    def process_ctrl(self, cp: gwent.messaging.ctrl.Message):
        self._log.info(f'received {cp.kind}', extra=cp.to_object())

        if cp.subkind == gwent.messaging.ctrl.STAGE:
            if cp.stage == gwent.messaging.ctrl.STAGE_MAIN_MENU:
                self._p1_gems = 2
                self._p2_gems = 2
                self._update_display()
            elif cp.stage == gwent.messaging.ctrl.STAGE_REGISTER_LEADERS:
                self._p1_gems = 2
                self._p2_gems = 2
                self._update_display()
            else:
                self._log.debug(f'Unhandled stage: {cp.stage}')
        else:
            self._log.debug(f'Unhandled subkind: {cp.subkind}')

    def process_card_play(self, cp: gwent.messaging.card_play.Message):
        if cp.subkind == gwent.messaging.card_play.UPDATE_GEMS:
            player = cp._instance.get(gwent.messaging.card_play.PLAYER)
            gems = cp._instance.get(gwent.messaging.card_play.GEMS, 0)
            if player == str(PLAYER.ONE):
                self._p1_gems = gems
            elif player == str(PLAYER.TWO):
                self._p2_gems = gems
            self._log.info(f"Gems updated: {player}={gems}")
            self._update_display()
