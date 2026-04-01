import functools
import glob
import os
import queue
import random
import tempfile
import time
import threading

import pydub
import pygame.mixer

import gwent.game
import gwent.messaging.base
import gwent.messaging.sfx
from gwent.game.data_paths import SFX_DIR, MUSIC_DIR
from gwent.hal.tts import get_provider, DEFAULT_PROVIDER


CHANNEL_EFFECT = 0
CHANNEL_TTS = 1

ANNOUNCEMENT_DELAY = 0


def instance(tts_provider: str = DEFAULT_PROVIDER):
    return _SFX(tts_provider=tts_provider)


class _SFX(gwent.game.BaseComponent):
    _tempdir = None
    _sound_cache = {}

    def __init__(self, tts_provider: str = DEFAULT_PROVIDER):
        super().__init__()
        self._tts_provider = get_provider(tts_provider)
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        self._announce_queue = queue.Queue()
        self._announce_thread = threading.Thread(
            target=self._announcement_worker, daemon=True)
        self._announce_thread.start()

    def tempdir(self):
        if self._tempdir is None:
            self._tempdir = os.path.join(tempfile.gettempdir(), 'gwent-sfx')
            if not os.path.exists(self._tempdir):
                os.makedirs(self._tempdir)
        return self._tempdir

    def effect_filename(self, sfx: gwent.messaging.sfx.Message) -> str:
        """Resolve effect path.

        1. If effect name is a subdirectory → pick random WAV from it
        2. If effect name matches a file directly → use it
        3. Search all subdirs for a matching file (e.g. 'card_read' finds 'ui/card_read.wav')
        """
        subdir = os.path.join(SFX_DIR, sfx.effect)
        if os.path.isdir(subdir):
            files = glob.glob(os.path.join(subdir, '*.wav'))
            if files:
                choice = random.choice(files)
                self._log.debug(f"Random SFX from {sfx.effect}/: {os.path.basename(choice)}")
                return choice
            return None
        # Direct file at root
        path = os.path.join(SFX_DIR, f'{sfx.effect}.wav')
        if os.path.exists(path):
            return path
        # Search subdirs for the file
        matches = glob.glob(os.path.join(SFX_DIR, '*', f'{sfx.effect}.wav'))
        if matches:
            return matches[0]
        return None

    def music_filename(self, sfx: gwent.messaging.sfx.Message) -> str:
        """Resolve music path. If random, pick from all available tracks."""
        if sfx.is_random or not sfx._instance.get('music'):
            files = glob.glob(os.path.join(MUSIC_DIR, '*.mp3'))
            if files:
                choice = random.choice(files)
                self._log.debug(f"Random music: {os.path.basename(choice)}")
                return choice
            return None
        return os.path.join(MUSIC_DIR, f'{sfx.music}.mp3')

    def tts_filename(self, msg: gwent.messaging.base.Message,
                    extn='mp3') -> str:
        d = self.tempdir()
        return os.path.join(d, f'{msg.content_id}.{extn}')

    def clear_cache(self, msg: gwent.messaging.base.Message):
        files = [
            self.tts_filename(msg, extn='mp3'),
            self.tts_filename(msg, extn='wav'),
        ]
        for f in files:
            if os.path.exists(f):
                self._log.debug({
                    'action': 'clear_cache',
                    'tts_name_file': f,
                })
                os.unlink(f)

    def load_sound(self, fwav: str):
        if fwav in self._sound_cache:
            return self._sound_cache[fwav]

        sound = pygame.mixer.Sound(fwav)
        self._log.debug({
            'action': 'cache sound',
            'fwav': fwav,
        })
        self._sound_cache[fwav] = sound
        return sound

    def play_sound(self, sound, channel: int=None):
        self._log.info({
            'action': 'play_sound',
            'channel': channel,
            'sound': sound,
        })
        if channel is None:
            sound.play()
        else:
            ch = pygame.mixer.Channel(channel)
            ch.play(sound)

    def play_music(self, sfx: gwent.messaging.sfx.Message):
        try:
            fpath = self.music_filename(sfx)
            self._log.info({
                'action': 'play_music',
                'fpath': fpath,
                'exists': os.path.exists(fpath) if fpath else False,
                'size': os.path.getsize(fpath) if fpath and os.path.exists(fpath) else 0,
                'mixer_initialized': pygame.mixer.get_init() is not None
            })

            if not fpath or not os.path.exists(fpath):
                self._log.error(f"Music file not found: {fpath}")
                return

            # Crossfade: fade out current, fade in new
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(2000)
                time.sleep(2.1)

            pygame.mixer.music.load(fpath)
            pygame.mixer.music.play(-1, fade_ms=2000)

            if pygame.mixer.music.get_busy():
                self._log.info(f"Music playing: {os.path.basename(fpath)}")
            else:
                self._log.error("Music failed to start playing")
        except Exception as e:
            self._log.error(f"Error playing music: {e}", exc_info=True)

    def play_effect(self, sfx: gwent.messaging.sfx.Message):
        try:
            start = time.time()
            fwav = self.effect_filename(sfx)
            self._log.info({
                'action': 'play_effect',
                'effect': sfx.effect,
                'fwav': fwav,
                'exists': os.path.exists(fwav) if fwav else False,
                'size': os.path.getsize(fwav) if fwav and os.path.exists(fwav) else 0,
                'mixer_initialized': pygame.mixer.get_init() is not None
            })

            if not fwav or not os.path.exists(fwav):
                self._log.error(f"Effect file not found: {fwav}")
                return 0

            speech = self.load_sound(fwav)
            self.play_sound(speech, CHANNEL_EFFECT)
            
            duration = speech.get_length()
            self._log.info({
                'action': 'effect_played',
                'effect': sfx.effect,
                'duration': duration
            })

            self.log_time('play_effect', start)
            return duration
        except Exception as e:
            self._log.error(f"Error playing effect: {e}", exc_info=True)
            return 0

    def announce(self, msg: gwent.messaging.base.Message, on_complete=None):
        """Queue an announcement for sequential playback."""
        self._log.info({
            'action': 'announce_queued',
            'speech': msg.announcement,
            'queue_size': self._announce_queue.qsize(),
        })
        self._announce_queue.put((msg, on_complete))

    def _announcement_worker(self):
        """Process announcements sequentially with a delay between them."""
        while True:
            msg, on_complete = self._announce_queue.get()
            try:
                self._play_announcement(msg)
                # Wait for the audio to finish plus a delay before the next one
                ch = pygame.mixer.Channel(CHANNEL_TTS)
                while ch.get_busy():
                    time.sleep(0.1)
                time.sleep(ANNOUNCEMENT_DELAY)
            except Exception as e:
                self._log.error(f"Error in announcement worker: {e}", exc_info=True)
            finally:
                # Always fire on_complete so the game advances even if TTS fails
                if on_complete:
                    on_complete(msg)
                self._announce_queue.task_done()

    def _play_announcement(self, msg: gwent.messaging.base.Message):
        try:
            self._log.info({
                'action': 'announce',
                'speech': msg.announcement,
            })
            # Skip synthesis and playback entirely for none provider
            from gwent_shared.tts.none_provider import NoneProvider
            if isinstance(self._tts_provider, NoneProvider):
                return 0
            start = time.time()
            native_wav = self._tts_provider.native_wav
            fwav = self.tts_filename(msg, extn='wav')

            if native_wav:
                # Provider outputs WAV directly — no conversion needed
                if not os.path.exists(fwav):
                    faction = getattr(msg, 'faction', None)
                    self._log.debug({
                        'action': 'tts_generate_wav',
                        'speech': msg.announcement,
                        'file': fwav,
                        'faction': faction,
                        'provider': type(self._tts_provider).__name__,
                    })
                    self._tts_provider.synthesize(msg.announcement, faction, fwav)
            else:
                # Provider outputs MP3 — generate then convert to WAV
                fmp3 = self.tts_filename(msg, extn='mp3')
                if not os.path.exists(fmp3):
                    faction = getattr(msg, 'faction', None)
                    self._log.debug({
                        'action': 'tts_generate_mp3',
                        'speech': msg.announcement,
                        'file': fmp3,
                        'faction': faction,
                        'provider': type(self._tts_provider).__name__,
                    })
                    self._tts_provider.synthesize(msg.announcement, faction, fmp3)

                if not os.path.exists(fwav):
                    self._log.debug({
                        'action': 'convert_to_wav',
                        'source': fmp3,
                        'target': fwav,
                    })
                    sound = pydub.AudioSegment.from_mp3(fmp3)
                    sound.export(fwav, format="wav")

            speech = self.load_sound(fwav)
            self.play_sound(speech, channel=CHANNEL_TTS)

            duration = speech.get_length()
            self._log.info({
                'action': 'announcement_played',
                'speech': msg.announcement,
                'duration': duration
            })

            self.log_time('announce', start)
            return duration
        except Exception as e:
            self._log.error(f"Error playing announcement: {e}", exc_info=True)
            return 0
