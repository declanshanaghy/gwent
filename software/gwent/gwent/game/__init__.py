import time
import threading
from typing import Any, Callable
from collections import OrderedDict

import paho.mqtt.client as mqtt
from gwent.utils.logging import get_logger

import gwent.messaging.base
import gwent.messaging.factory
import gwent.messaging.mfd
import gwent.messaging.sfx

CH_SEP = '/'
MAIN_CHANNEL = 'gwent'

CH_CTRL = CH_SEP.join((MAIN_CHANNEL, 'ctrl'))

CH_CARDS = CH_SEP.join((MAIN_CHANNEL, 'cards'))
CH_CARDS_RAW = CH_SEP.join((CH_CARDS, 'raw'))
CH_CARDS_RAW_READ = CH_SEP.join((CH_CARDS_RAW, 'read'))
CH_CARDS_RAW_WRITE = CH_SEP.join((CH_CARDS_RAW, 'write'))

CH_CARDS_PLAY = CH_SEP.join((CH_CARDS, 'play'))

CH_MFD = CH_SEP.join((MAIN_CHANNEL, 'mfd'))
CH_MFD_PRESENT = CH_SEP.join((CH_MFD, 'present'))
CH_MFD_CHOOSE = CH_SEP.join((CH_MFD, 'choose'))

CH_SFX = CH_SEP.join((MAIN_CHANNEL, 'sfx'))
CH_SFX_COMPLETE = CH_SEP.join((CH_SFX, 'complete'))

DEFAULT_YIELD_TIME = 0.5
DEFAULT_ERROR_TIME = 3.0
LOG_FREQ_SECS = 5


def make_channel(base, *topics):
    return CH_SEP.join((base, *topics))


class BaseComponent(object):
    _last_log = time.time() - LOG_FREQ_SECS - 1
    _log = None
    simple_mode = False  # Set True by --simple flag; use static TTS messages

    def __init__(self):
        self._log = get_logger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        # Log level is now controlled by logging.json configuration

    def should_log(self) -> bool:
        r = time.time() > self._last_log + LOG_FREQ_SECS
        if r:
            self._last_log = time.time()
        return r

    def log_time(self, action, start):
        end = time.time()
        self._log.debug({
            'action': action,
            'start': f'{start:.5f}',
            'end': f'{end:.5f}',
            'duration': f'{end - start:.5f}',
        })


class ThreadComponent(BaseComponent):
    """Base class for threaded components"""
    
    def __init__(self):
        super().__init__()
        self._thread = None
        self._stop_event = threading.Event()
        self._initialized = threading.Event()
    
    def init(self):
        """Initialize the component"""
        self._log.debug("Initializing component")
        self._initialized.set()
    
    def start(self):
        """Start the component in a new thread"""
        if self._thread is not None and self._thread.is_alive():
            self._log.warning("Component already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
    
    def _run(self):
        """Main thread function"""
        self._log.info("Component started")
        try:
            self.run()
        except Exception as e:
            self._log.error(f"Error in component thread: {e}", exc_info=True)
        finally:
            self._log.info("Component stopped")
    
    def run(self):
        """Override this method in subclasses"""
        self._stop_event.wait()
    
    def shutdown(self):
        """Shutdown the component"""
        self._log.info("Shutting down component")
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                self._log.warning("Component thread did not terminate gracefully")
    
class PubSubComponent(ThreadComponent):
    def __init__(self, pubsub: mqtt.Client):
        super().__init__()
        self._pubsub = pubsub
        self._callbacks = {}
        
    def shutdown(self):
        """Shutdown the component"""
        # Unsubscribe from all topics
        for topic in list(self._callbacks.keys()):
            self.unsubscribe(topic)                

        super().shutdown()
        
    def _message_handler(self, topic: str, payload: str, expect_kind: str, callback: Callable):
        """Handle incoming messages"""
        try:
            message = gwent.messaging.factory.unmarshall(payload, expect_kind=expect_kind)
            callback(message)
        except Exception as e:
            self._log.exception(f"Error processing message: {e}", exc_info=True)

    def subscribe(self, topic_filter: str, expect_kind: str,
                  callback: Callable[[gwent.messaging.base.Message], Any]):
        """Subscribe to a topic with a callback"""
        
        # Create a wrapper function to handle the message
        def wrapper(topic, payload):
            self._message_handler(topic, payload, expect_kind, callback)
        
        # Store the wrapper function for later unsubscription
        if topic_filter not in self._callbacks:
            self._callbacks[topic_filter] = []
        
        self._callbacks[topic_filter].append((wrapper, callback))
        
        self._log.info({
            'action': 'subscribe',
            'topic_filter': topic_filter,
            'expect_kind': expect_kind,
        })
        
        # Subscribe to the topic
        self._pubsub.subscribe(topic_filter, wrapper)

    def unsubscribe(self, topic: str):
        """Unsubscribe from a topic"""
        self._log.info({
            'action': 'unsubscribe',
            'topic': topic,
        })
        
        if topic in self._callbacks:
            for wrapper, _ in self._callbacks[topic]:
                self._pubsub.unsubscribe(topic, wrapper)
            del self._callbacks[topic]

    def publish(self, topic, message: gwent.messaging.base.Message):
        """Publish a message to a topic"""
        self._log.info({
            'action': 'publish',
            'topic': topic,
            'kind': message.kind,
            'content_id': message.content_id,
            'body': message.body,
        })
        self._pubsub.publish(topic, message.body, qos=1)
        # Signal long-poll waiters that state has changed
        cond = getattr(self._pubsub, 'state_condition', None)
        if cond:
            with cond:
                cond.notify_all()

    def publish_effect(self, effect: str):
        """Publish a sound effect"""
        self._log.info(f"Publishing sound effect: {effect}")
        e = gwent.messaging.sfx.Message.with_effect(effect)
        self.publish(CH_SFX, e)

    def publish_music(self, music: str = None):
        """Publish background music"""
        self._log.info(f"Publishing background music: {music}")
        e = gwent.messaging.sfx.Message.with_music(music=music)
        self.publish(CH_SFX, e)

    def publish_error(self, error: str):
        """Publish an error message"""
        e = gwent.messaging.mfd.Message.with_error(error=error)
        self.publish(CH_MFD_PRESENT, e)

        e = gwent.messaging.sfx.Message.with_announcement(e.error)
        self.publish(CH_SFX, e)

    def publish_prompt(self, prompt: str, ok=True,
                       cancel=True, clear_choices=True, ok_text=None,
                       faction=None):
        """Publish a prompt message"""
        p = gwent.messaging.mfd.Message.with_prompt(
            prompt=prompt, ok=ok, cancel=cancel, clear_choices=clear_choices,
            ok_text=ok_text)
        self.publish(CH_MFD_PRESENT, p)

        p = gwent.messaging.sfx.Message.with_announcement(
            p.prompt, faction=faction)
        self.publish(CH_SFX, p)
