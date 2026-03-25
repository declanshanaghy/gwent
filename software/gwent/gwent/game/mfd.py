import threading
import time

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
        self._log.info("Initializing MFD component")
        self._chooser_thread = None
        self._chooser_lock = threading.RLock()
        self._chooser_stop_event = threading.Event()
        self._log.info("MFD component initialized")

    def init(self):
        self._log.info("Starting MFD initialization")
        super().init()
        try:
            self._log.info("Creating MFD hardware instance")
            self._mfd = gwent.hal.mfd.instance()
            self._log.info("MFD hardware instance created successfully")
        except Exception as e:
            self._log.error(f"Failed to create MFD hardware instance: {e}")
            raise
            
        self._log.info(f"Subscribing to channel {gwent.game.CH_MFD_PRESENT}")
        self.subscribe(gwent.game.CH_MFD_PRESENT,
                      gwent.messaging.mfd.KIND,
                      self.process_mfd)
        self._log.info("MFD initialization complete")

    def shutdown(self):
        self._log.info("Shutting down MFD component")
        self.cancel_chooser()
        self._log.info(f"Unsubscribing from channel {gwent.game.CH_MFD_PRESENT}")
        self.unsubscribe(gwent.game.CH_MFD_PRESENT)
        super().shutdown()
        self._log.info("MFD component shutdown complete")

    def cancel_chooser(self):
        self._log.info("Attempting to cancel chooser thread")
        with self._chooser_lock:
            if self._chooser_thread is not None:
                self._log.info(f"Chooser thread exists, is_alive={self._chooser_thread.is_alive()}")
                if self._chooser_thread.is_alive():
                    self._log.info("Setting stop event for chooser thread")
                    self._chooser_stop_event.set()
                    self._mfd
                    
                    # Try joining with increasing timeouts
                    for timeout in [0.5, 1.0, 2.0]:
                        self._log.info(f"Joining chooser thread with {timeout:.1f}s timeout")
                        start_time = time.time()
                        self._chooser_thread.join(timeout=timeout)
                        elapsed = time.time() - start_time
                        
                        if self._chooser_thread.is_alive():
                            self._log.warning("Chooser thread did not terminate successfully", 
                                           extra={"elapsed": elapsed})
                        else:
                            self._log.debug("Chooser thread terminated successfully", 
                                           extra={"elapsed": elapsed})
                            break
                    
                    if self._chooser_thread.is_alive():
                        self._log.error("Chooser thread did not terminate gracefully after multiple timeout attempts")
                else:
                    self._log.warning("Chooser thread exists but is not alive")
                
                self._chooser_thread = None
                self._log.info("Clearing stop event")
                self._chooser_stop_event.clear()
            else:
                self._log.info("No chooser thread to cancel")

    def process_mfd(self, mfd: gwent.messaging.mfd.Message):
        # Deduplicate by content_id (MQTT QoS 1 can redeliver)
        if hasattr(mfd, 'content_id') and mfd.content_id == getattr(self, '_last_mfd_id', None):
            self._log.debug(f"Skipping duplicate MFD message: {mfd.content_id}")
            return
        self._last_mfd_id = getattr(mfd, 'content_id', None)

        self._log.info({
            'action': 'received mfd',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'body': mfd.body,
        })
        
        def receive_select(delta: int, choice: gwent.messaging.choice.Message):
            self._log.info({
                'action': 'receive_select',
                'delta': delta,
                'choice_id': choice.id,
                'choice_text': choice.text
            })
            effect = gwent.messaging.sfx.EFFECT_MFD_SELECT
            for i in range(abs(delta)):
                self._log.debug(f"Publishing effect {effect} (iteration {i+1}/{abs(delta)})")
                self.publish_effect(effect)

        def receive_choice_callback(mfd_method):
            thread_id = threading.get_ident()
            self._log.info(f"Chooser thread started (id={thread_id})")
            try:
                self._log.info(f"Calling MFD method: {mfd_method.__name__}")
                
                # Periodically check for stop event while waiting for choice
                choice = None
                try:
                    # Set a timeout for the MFD method
                    choice = mfd_method(mfd, receive_select)
                except Exception as e:
                    self._log.error(f"Error in MFD method: {e}", exc_info=True)
                
                self._log.info({
                    'action': 'mfd_method_result',
                    'choice': choice.id if choice else None,
                    'stop_event_set': self._chooser_stop_event.is_set()
                })
                
                if choice and not self._chooser_stop_event.is_set():
                    self._log.info(f"Publishing choice: {choice.id}")
                    self.publish_effect(gwent.messaging.sfx.EFFECT_MFD_CHOOSE)
                    self.publish(gwent.game.CH_MFD_CHOOSE, choice)
                else:
                    if not choice:
                        self._log.warning("No choice returned from MFD method")
                    if self._chooser_stop_event.is_set():
                        self._log.info("Stop event was set, not publishing choice")
            except Exception as e:
                self._log.error(f"Error in chooser thread: {e}", exc_info=True)
            finally:
                # Make sure we properly clean up
                self._log.info(f"Chooser thread exiting (id={thread_id})")

        self._log.info("Canceling any existing chooser thread")
        self.cancel_chooser()

        with self._chooser_lock:
            self._log.info(f"Processing MFD message with subkind: {mfd.subkind}")
            
            if mfd.subkind == gwent.messaging.mfd.ERROR:
                self._log.info("Creating ERROR display thread")
                self._chooser_thread = threading.Thread(
                    target=receive_choice_callback,
                    args=(self._mfd.present_error,),
                    name="MFD-Error-Thread")
                self._chooser_thread.daemon = True
                self._log.info("Starting ERROR display thread")
                self._chooser_thread.start()
                
            elif mfd.subkind == gwent.messaging.mfd.PROMPT:
                self._log.info("Creating PROMPT display thread")
                self._chooser_thread = threading.Thread(
                    target=receive_choice_callback,
                    args=(self._mfd.present_prompt,),
                    name="MFD-Prompt-Thread")
                self._chooser_thread.daemon = True
                self._log.info("Starting PROMPT display thread")
                self._chooser_thread.start()
                
            elif mfd.subkind == gwent.messaging.mfd.CHOICES:
                self._log.info("Creating CHOICES display thread")
                self._chooser_thread = threading.Thread(
                    target=receive_choice_callback,
                    args=(self._mfd.present_choices,),
                    name="MFD-Choices-Thread")
                self._chooser_thread.daemon = True
                self._log.info("Starting CHOICES display thread")
                self._chooser_thread.start()
                
            else:
                self._log.debug(f'Unhandled subkind {mfd.subkind}')
