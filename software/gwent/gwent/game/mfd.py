import threading

import gwent.cards
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.sfx
import gwent.messaging.choice

import gwent.game
import gwent.hal.mfd


class MFD(gwent.game.PubSubComponent):
    def __init__(self, pubsub):
        super().__init__(pubsub)
        self._chooser_thread = None
        self._chooser_lock = threading.RLock()
        self._chooser_stop_event = threading.Event()

    def init(self):
        self._mfd = gwent.hal.mfd.instance()
        self.subscribe(gwent.game.CH_MFD_PRESENT,
                      gwent.messaging.mfd.KIND,
                      self.process_mfd)

    def shutdown(self):
        self.cancel_chooser()
        self.unsubscribe(gwent.game.CH_MFD_PRESENT)
        super().shutdown()

    def cancel_chooser(self):
        with self._chooser_lock:
            if self._chooser_thread is not None and self._chooser_thread.is_alive():
                self._log.debug("Previous chooser being canceled")
                self._chooser_stop_event.set()
                self._chooser_thread.join(timeout=1.0)
                if self._chooser_thread.is_alive():
                    self._log.warning("Chooser thread did not terminate gracefully")
                self._chooser_thread = None
                self._chooser_stop_event.clear()

    def process_mfd(self, mfd: gwent.messaging.mfd.Message):
        self._log.info({
            'action': 'received mfd',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'body': mfd.body,
        })
        self.cancel_chooser()

        def receive_select(delta: int, _: gwent.messaging.choice.Message):
            effect = gwent.messaging.sfx.EFFECT_MFD_SELECT
            for i in range(abs(delta)):
                self.publish_effect(effect)

        def receive_choice_thread(mfd_method):
            try:
                choice = mfd_method(mfd, receive_select)
                if choice and not self._chooser_stop_event.is_set():
                    self.publish_effect(gwent.messaging.sfx.EFFECT_MFD_CHOOSE)
                    self.publish(gwent.game.CH_MFD_CHOOSE, choice)
            except Exception as e:
                self._log.error(f"Error in chooser thread: {e}")

        with self._chooser_lock:
            if mfd.subkind == gwent.messaging.mfd.ERROR:
                self._chooser_thread = threading.Thread(
                    target=receive_choice_thread,
                    args=(self._mfd.present_error,))
                self._chooser_thread.daemon = True
                self._chooser_thread.start()
            elif mfd.subkind == gwent.messaging.mfd.PROMPT:
                self._chooser_thread = threading.Thread(
                    target=receive_choice_thread,
                    args=(self._mfd.present_prompt,))
                self._chooser_thread.daemon = True
                self._chooser_thread.start()
            elif mfd.subkind == gwent.messaging.mfd.CHOICES:
                self._chooser_thread = threading.Thread(
                    target=receive_choice_thread,
                    args=(self._mfd.present_choices,))
                self._chooser_thread.daemon = True
                self._chooser_thread.start()
            else:
                self._log.error(f'Unhandled subkind {mfd.subkind}')
