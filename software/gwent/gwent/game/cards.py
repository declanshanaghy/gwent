import time
import threading

import gwent.cards
import gwent.game
import gwent.messaging.factory
import gwent.messaging.ctrl
import gwent.messaging.sfx

import gwent.hal.rfid

T_PAUSE_CARD_READ_SHORT = 1
T_PAUSE_CARD_READ_LONG = 3

READING_STAGES = {
    gwent.messaging.ctrl.STAGE_REGISTER_LEADERS: T_PAUSE_CARD_READ_SHORT,
    gwent.messaging.ctrl.STAGE_REGISTER_DECKS: T_PAUSE_CARD_READ_SHORT,
    gwent.messaging.ctrl.STAGE_PLAY_ROUND: T_PAUSE_CARD_READ_SHORT,
}


class Reader(gwent.game.PubSubComponent):
    _pause_until = None
    _pause_length = None

    def init(self):
        super().init()
        self._read_enabled = False
        self._rfid = None
        self._last_rfid = None

        self.subscribe(gwent.game.CH_CTRL,
                      gwent.messaging.ctrl.KIND,
                      self.process_ctrl)

    def start(self):
        # Initialize RFID hardware AFTER all other components (especially OLED)
        # are set up, because the OLED SPI init can reset the MFRC522 via
        # the shared GPIO25 RST line.
        self._log.info("Initializing RFID hardware")
        self._rfid = gwent.hal.rfid.instance()
        self._log.info("RFID hardware initialized")
        super().start()

    def shutdown(self):
        self._read_enabled = False
        self.unsubscribe(gwent.game.CH_CTRL)
        super().shutdown()

    def process_ctrl(self, ctrl: gwent.messaging.ctrl.Message):
        self._log.info('received ctrl', extra={
            'kind': ctrl.kind,
            'subkind': ctrl.subkind,
            'body': ctrl.to_object(),
        })

        if ctrl.subkind == gwent.messaging.ctrl.STAGE:
            if ctrl.stage in READING_STAGES:
                self.pause_length = READING_STAGES[ctrl.stage]
                self.read_enabled = ctrl.active
                self._log.info({
                    'action': 'read_enabled',
                    'read_enabled': self._read_enabled,
                })
        else:
            self._log.debug(f'Unhandled subkind {ctrl.subkind}')

    def pause_reading(self):
        self._pause_until = time.time() + self.pause_length

    def pause_complete(self):
        if self._pause_until is None:
            return True
        else:
            complete = time.time() > self._pause_until
            if complete:
                self._pause_until = None
                self._log.info('pause complete, reading unblocked')
            return complete

    @property
    def should_read(self) -> bool:
        return self.read_enabled and self.pause_complete()

    @property
    def pause_length(self) -> float:
        return self._pause_length

    @pause_length.setter
    def pause_length(self, v: float):
        self._pause_length = v

    @property
    def read_enabled(self) -> bool:
        return self._read_enabled

    @read_enabled.setter
    def read_enabled(self, v: bool):
        self._log.info({
            'action': 'set read enabled',
            'read_enabled': v,
        })
        self._read_enabled = v

    def run(self):
        while not self._stop_event.is_set():
            if self.should_read:
                # Read card in the current thread
                card = self._rfid.read_card()

                if card is not None:
                    # Skip if same card is still on the reader
                    if card.rfid == self._last_rfid:
                        time.sleep(0.5)
                        continue
                    self._last_rfid = card.rfid

                    # Skip incomplete reads (blank means body read failed)
                    if card.is_blank:
                        self._log.warning({
                            'action': 'incomplete_card_read',
                            'rfid': card.rfid,
                        })
                        self.pause_reading()
                        continue

                    self.publish_effect(
                        gwent.messaging.sfx.EFFECT_CARD_READ)
                    self.publish(gwent.game.CH_CARDS_RAW_READ, card)
                    self.pause_reading()
                else:
                    # Card removed, clear last seen
                    if self._last_rfid is not None:
                        self._log.info({'action': 'card_removed'})
                    self._last_rfid = None

            time.sleep(gwent.game.DEFAULT_YIELD_TIME)
