import os
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
CH_MUSIC = CH_SEP.join((MAIN_CHANNEL, 'music'))
CH_MUSIC_COMPLETE = CH_SEP.join((CH_MUSIC, 'complete'))
CH_MUSIC_CTRL = CH_SEP.join((CH_MUSIC, 'ctrl'))

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

    def publish(self, topic, message: gwent.messaging.base.Message, retain=False):
        """Publish a message to a topic and record to disk."""
        self._log.info({
            'action': 'publish',
            'topic': topic,
            'kind': message.kind,
            'content_id': message.content_id,
            'body': message.body,
            'retain': retain,
        })
        self._pubsub.publish(topic, message.body, qos=1, retain=retain)
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

    _music_next_track = None  # the next_music promised in the last play message
    _music_index = 0          # current position in the sorted track list
    _music_shuffled = False   # whether we've done the initial shuffle
    _music_enabled = True     # shared across all instances (toggled by SFX._on_music_ctrl)
    _music_timer = None       # shared auto-advance timer
    _client_handles_music = False  # True when a TUI client is connected (skip local playback)

    def _scan_music_tracks(self):
        """Live-scan music directory. Sorted for stable ordering."""
        import glob as _glob
        from gwent.game.data_paths import MUSIC_DIR
        return sorted([os.path.splitext(os.path.basename(f))[0]
                       for f in _glob.glob(os.path.join(MUSIC_DIR, '*.mp3'))])

    def publish_music(self, music: str = None):
        """Publish background music to gwent/music (retained).

        Maintains a sequential index through the live-scanned track list.
        On first call, shuffles the order. Wraps around at the end.
        Schedules auto-advance timer based on track duration.
        """
        import random as _random
        import threading
        from gwent.game.data_paths import MUSIC_DIR
        import gwent.messaging.music

        tracks = self._scan_music_tracks()
        if not tracks:
            return

        # Initial shuffle on first call
        if not self._music_shuffled:
            _random.shuffle(tracks)
            self.__class__._music_shuffled = True
            self.__class__._music_index = 0
            self._log.info(f"Music order: {tracks}")

        if music:
            # Explicit track — find its index in current scan
            try:
                idx = tracks.index(music)
            except ValueError:
                idx = self._music_index
            self.__class__._music_index = idx
        else:
            # Use current index
            idx = self._music_index % len(tracks)
            music = tracks[idx]

        # Next track wraps around
        next_idx = (idx + 1) % len(tracks)
        next_track = tracks[next_idx]

        # Remember what we promised and advance the pointer
        self.__class__._music_next_track = next_track
        self.__class__._music_index = next_idx  # advance for next call

        # Get track duration for auto-advance scheduling
        duration = None
        mp3_path = os.path.join(MUSIC_DIR, f'{music}.mp3')
        if os.path.exists(mp3_path):
            try:
                import pydub
                audio = pydub.AudioSegment.from_mp3(mp3_path)
                duration = len(audio) / 1000.0
            except Exception:
                pass

        dur_str = f", duration: {duration:.0f}s" if duration else ""
        self._log.info(f"Music: {music}, next: {next_track}{dur_str}")

        if not PubSubComponent._music_enabled:
            self._log.info("Music disabled, skipping publish")
            return

        e = gwent.messaging.music.Message.with_play(
            music=music, next_music=next_track, duration_seconds=duration)
        self.publish(CH_MUSIC, e, retain=True)

        # Schedule auto-advance 2s before track ends for crossfade overlap
        if duration:
            advance_after = max(1, duration - 2.0)
            def _auto_advance():
                self._log.info(f"Auto-advancing music (crossfade for {music})")
                complete = gwent.messaging.music.Message.with_complete(
                    music=music, source="gwent-timer")
                self.publish(CH_MUSIC_COMPLETE, complete)
            if PubSubComponent._music_timer:
                PubSubComponent._music_timer.cancel()
            PubSubComponent._music_timer = threading.Timer(advance_after, _auto_advance)
            PubSubComponent._music_timer.daemon = True
            PubSubComponent._music_timer.start()

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
