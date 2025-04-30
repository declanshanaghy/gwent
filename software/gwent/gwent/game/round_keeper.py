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
        self.plr1_score = 0
        self.plr2_score = 0

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
        
        If score is provided, it updates both player scores to that value.
        Otherwise, it displays the current player scores.
        """
        if score is not None:
            # If a single score is provided, update both player scores
            self.plr1_score = score
            self.plr2_score = score
            self._log.info(f"Setting both player scores to {score}")
        else:
            self._log.info(f"Displaying current scores: Player 1: {self.plr1_score}, Player 2: {self.plr2_score}")
            
        # Display both player scores with a border and vertical bar
        self._matrix.display_round_scores(self.plr1_score, self.plr2_score)

    def process_ctrl(self, cp: gwent.messaging.ctrl.Message):
        self._log.info(f'received {cp.kind}', extra=cp.to_object())
        
        if cp.subkind == gwent.messaging.ctrl.STAGE:
            if cp.stage == gwent.messaging.ctrl.STAGE_MAIN_MENU:
                self._update_display(0)
            elif cp.stage == gwent.messaging.ctrl.STAGE_REGISTER_LEADERS:
                # Set player scores to 1 and 2 for the register leaders stage
                self._log.info("Register Leaders stage: Setting Player 1 score to 1 and Player 2 score to 2")
                self.plr1_score = 1
                self.plr2_score = 2
                self._update_display()
            else:
                self._log.debug(f'Unhandled stage: {cp.stage}')
        else:
            self._log.debug(f'Unhandled subkind: {cp.subkind}')
