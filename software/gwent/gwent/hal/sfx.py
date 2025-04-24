import functools
import os
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


def instance():
    return _SFX()


class _SFX(gwent.game.BaseComponent):
    _tempdir = None
    _sound_cache = {}

    def __init__(self):
        super().__init__()
        pygame.mixer.init(frequency=24000, size=-16, channels=2)

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
        fwav = self.music_filename(sfx)
        self._log.info({
            'action': 'play',
            'fwav': fwav,
        })
        pygame.mixer.music.load(fwav)
        pygame.mixer.music.play(-1)

    def play_effect(self, sfx: gwent.messaging.sfx.Message):
        start = time.time()
        fwav = self.effect_filename(sfx)
        self._log.info({
            'action': 'play_effect',
            'effect': sfx.effect,
            'fwav': fwav,
        })
        speech = self.load_sound(fwav)
        self.play_sound(speech, CHANNEL_EFFECT)

        self.log_time('play_effect', start)
        return speech.get_length()

    def announce(self, msg: gwent.messaging.base.Message):
        self._log.info({
            'action': 'announce',
            'speech': msg.announcement,
        })
        start = time.time()
        fmp3 = self.tts_filename(msg)
        fwav = self.tts_filename(msg, extn='wav')

        # Cache TTS if needed
        if not os.path.exists(fmp3):
            self._log.debug({
                'action': 'tts',
                'speech': msg.announcement,
                'tts_name_file': fmp3,
            })
            tts_name = gtts.gTTS(msg.announcement, lang='en')
            tts_name.save(fmp3)

        if not os.path.exists(fwav):
            # convert to wav for pygame
            sound = pydub.AudioSegment.from_mp3(fmp3)
            sound.export(fwav, format="wav")

        speech = self.load_sound(fwav)
        self.play_sound(speech, channel=CHANNEL_TTS)

        self.log_time('announce', start)
        return speech.get_length()
