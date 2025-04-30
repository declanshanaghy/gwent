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
        self._current_stage = None  # Track the current stage
        self._last_subkind = None   # Track the last subkind processed
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
        """
        Cancel the chooser thread if it exists.
        This method should only be called when we're sure we want to cancel the thread,
        such as when shutting down or when explicitly requested.
        """
        self._log.info("Attempting to cancel chooser thread")
        with self._chooser_lock:
            if self._chooser_thread is not None:
                self._log.debug(f"Chooser thread exists, is_alive={self._chooser_thread.is_alive()}")
                if self._chooser_thread.is_alive():
                    self._log.debug("Setting stop event for chooser thread")
                    self._chooser_stop_event.set()
                    
                    # Try joining with a single timeout
                    self._log.debug(f"Joining chooser thread", extra={"timeout": self.THREAD_TIMEOUT_LONG})
                    start_time = time.time()
                    self._chooser_thread.join(timeout=self.THREAD_TIMEOUT_LONG)
                    elapsed = time.time() - start_time
                    self._log.debug(f"Join completed", extra={
                        "elapsed": elapsed, 
                        "success": not self._chooser_thread.is_alive()
                    })
                    
                    if self._chooser_thread.is_alive():
                        self._log.warning("Chooser thread did not terminate gracefully after timeout")
                    else:
                        self._log.info("Chooser thread terminated successfully")
                else:
                    self._log.warning("Chooser thread exists but is not alive")
                
                self._chooser_thread = None
                self._log.debug("Clearing stop event")
                self._chooser_stop_event.clear()
            else:
                self._log.debug("No chooser thread to cancel")

    def process_mfd(self, mfd: gwent.messaging.mfd.Message):
        """
        Process an MFD message.
        Only cancel the existing chooser thread if we're changing stages or if explicitly needed.
        """
        self._log.info({
            'action': 'received mfd',
            'kind': mfd.kind,
            'subkind': mfd.subkind,
            'body': mfd.body,
        })
        
        # Extract stage information from the message body if available
        stage = None
        if 'stage' in mfd.body:
            stage = mfd.body['stage']
            
        # Cancel the chooser thread if we're changing stages or if the subkind is changing
        # This ensures that a choices message can replace a prompt message
        should_cancel = False
        
        # Check for stage change
        if stage is not None and stage != self._current_stage:
            self._log.info(f"Stage change detected: {self._current_stage} -> {stage}")
            self._current_stage = stage
            should_cancel = True
        
        # Check if we have an existing thread and the subkind is changing
        if (self._chooser_thread is not None and self._chooser_thread.is_alive() and
            hasattr(self, '_last_subkind') and self._last_subkind != mfd.subkind):
            self._log.info(f"Subkind change detected: {self._last_subkind} -> {mfd.subkind}")
            should_cancel = True
        
        # Store the current subkind for future comparison
        self._last_subkind = mfd.subkind
        
        # Cancel the thread if needed
        if should_cancel:
            self._log.info("Canceling existing chooser thread due to stage or subkind change",
                          extra={"stage": stage, "current_stage": self._current_stage,
                                 "subkind": mfd.subkind, "last_subkind": self._last_subkind})
            self.cancel_chooser()
        else:
            self._log.info("No stage or subkind change detected, keeping existing chooser thread if any",
                          extra={"stage": stage, "current_stage": self._current_stage,
                                 "subkind": mfd.subkind, "last_subkind": self._last_subkind})

        # Create a single function for handling selection events
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

        # Create a single thread function for all MFD methods
        def start_chooser_thread(mfd_method):
            """
            Start a chooser thread for the given MFD method.
            This is a unified function for all MFD methods.
            """
            with self._chooser_lock:
                # If there's already a thread running, we need to decide what to do
                if self._chooser_thread is not None and self._chooser_thread.is_alive():
                    # For prompt messages, we should update the display even if there's a thread running
                    if mfd.subkind == gwent.messaging.mfd.PROMPT:
                        # Call the method directly without creating a new thread
                        # This ensures the display is updated immediately
                        self._log.info(f"Updating display with new prompt: {mfd.prompt}")
                        try:
                            mfd_method(mfd, receive_select)
                        except Exception as e:
                            self._log.error(f"Error updating display: {e}", exc_info=True)
                        return
                    else:
                        # For other message types, don't start a new thread
                        self._log.info("Chooser thread already running, not starting a new one")
                        return
                
                # Clear the stop event before starting a new thread
                self._chooser_stop_event.clear()
                
                # Define the thread function
                def thread_func():
                    thread_id = threading.get_ident()
                    self._log.info(f"Chooser thread started (id={thread_id})")
                    try:
                        self._log.info(f"Calling MFD method: {mfd_method.__name__}")
                        
                        # Call the MFD method
                        choice = None
                        try:
                            choice = mfd_method(mfd, receive_select)
                        except Exception as e:
                            self._log.error(f"Error in MFD method: {e}", exc_info=True)
                        
                        self._log.info({
                            'action': 'mfd_method_result',
                            'choice': choice.id if choice else None,
                            'stop_event_set': self._chooser_stop_event.is_set()
                        })
                        
                        # Publish the choice if available and not stopped
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
                        self._log.info(f"Chooser thread exiting (id={thread_id})")
                
                # Create and start the thread
                thread_name = f"MFD-{mfd.subkind.capitalize()}-Thread"
                self._log.info(f"Creating {thread_name}")
                self._chooser_thread = threading.Thread(
                    target=thread_func,
                    name=thread_name)
                self._chooser_thread.daemon = True
                self._log.info(f"Starting {thread_name}")
                self._chooser_thread.start()

        # Process the MFD message based on its subkind
        if mfd.subkind == gwent.messaging.mfd.ERROR:
            start_chooser_thread(self._mfd.present_error)
        elif mfd.subkind == gwent.messaging.mfd.PROMPT:
            start_chooser_thread(self._mfd.present_prompt)
        elif mfd.subkind == gwent.messaging.mfd.CHOICES:
            start_chooser_thread(self._mfd.present_choices)
        else:
            self._log.debug(f'Unhandled subkind {mfd.subkind}')
