import functools
import os
import queue
import tempfile
import time
import threading

import pydub
import pygame.mixer
import gtts

import gwent.game
import gwent.messaging.base
import gwent.messaging.sfx


CHANNEL_EFFECT = 0
CHANNEL_TTS = 1

ANNOUNCEMENT_DELAY = 0


def instance():
    return _SFX()


class _SFX(gwent.game.BaseComponent):
    _tempdir = None
    _sound_cache = {}

    def __init__(self):
        super().__init__()
        pygame.mixer.init(frequency=24000, size=-16, channels=2)
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
        base = os.path.dirname(__file__)
        dir = os.path.abspath(base)
        return os.path.join(dir, 'effects', f'{sfx.effect}.wav')

    def music_filename(self, sfx: gwent.messaging.sfx.Message) -> str:
        base = os.path.dirname(__file__)
        dir = os.path.abspath(base)
        return os.path.join(dir, 'music', f'{sfx.music}.mp3')

    def tts_filename(self, msg: gwent.messaging.base.Message,
                    extn='mp3') -> str:
        d = self.tempdir()
        return os.path.join(d, f'{msg.content_id}.{extn}')

    def clear_cache(self, msg: gwent.messaging.base.Message):
        files = [
            self.tts_filename(msg),
            self.tts_filename(msg, extn='wav')
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
            fwav = self.music_filename(sfx)
            self._log.info({
                'action': 'play_music',
                'fwav': fwav,
                'exists': os.path.exists(fwav),
                'size': os.path.getsize(fwav) if os.path.exists(fwav) else 0,
                'mixer_initialized': pygame.mixer.get_init() is not None
            })
            
            if not os.path.exists(fwav):
                self._log.error(f"Music file not found: {fwav}")
                return
                
            pygame.mixer.music.load(fwav)
            pygame.mixer.music.play(-1)
            
            # Verify music is playing
            if pygame.mixer.music.get_busy():
                self._log.info("Music started playing successfully")
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
                'exists': os.path.exists(fwav),
                'size': os.path.getsize(fwav) if os.path.exists(fwav) else 0,
                'mixer_initialized': pygame.mixer.get_init() is not None
            })
            
            if not os.path.exists(fwav):
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
                # Notify that the announcement has finished
                if on_complete:
                    on_complete(msg)
            except Exception as e:
                self._log.error(f"Error in announcement worker: {e}", exc_info=True)
            finally:
                self._announce_queue.task_done()

    def _play_announcement(self, msg: gwent.messaging.base.Message):
        try:
            self._log.info({
                'action': 'announce',
                'speech': msg.announcement,
            })
            start = time.time()
            fmp3 = self.tts_filename(msg)
            fwav = self.tts_filename(msg, extn='wav')

            self._log.debug({
                'action': 'announce_paths',
                'fmp3': fmp3,
                'fwav': fwav,
                'fmp3_exists': os.path.exists(fmp3),
                'fwav_exists': os.path.exists(fwav),
                'mixer_initialized': pygame.mixer.get_init() is not None
            })

            # Cache TTS if needed
            if not os.path.exists(fmp3):
                self._log.debug({
                    'action': 'tts_generate',
                    'speech': msg.announcement,
                    'tts_name_file': fmp3,
                })
                tts_name = gtts.gTTS(msg.announcement, lang='en')
                tts_name.save(fmp3)
                self._log.debug({
                    'action': 'tts_saved',
                    'file': fmp3,
                    'size': os.path.getsize(fmp3) if os.path.exists(fmp3) else 0
                })

            if not os.path.exists(fwav):
                # convert to wav for pygame
                self._log.debug({
                    'action': 'convert_to_wav',
                    'source': fmp3,
                    'target': fwav
                })
                sound = pydub.AudioSegment.from_mp3(fmp3)
                sound.export(fwav, format="wav")
                self._log.debug({
                    'action': 'wav_saved',
                    'file': fwav,
                    'size': os.path.getsize(fwav) if os.path.exists(fwav) else 0
                })

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
