import asyncio
import os
import tempfile

import pygame.mixer
import gtts

import gwent.hal
import gwent.messaging.base


def instance():
    if gwent.hal.REAL:
        return _TTSReal()
    else:
        return _TTSFake()


class _TTSFake(gwent.hal.Component):
    async def announce(self, msg: gwent.messaging.base.Message):
        self._log.info({
            'action': 'announce',
            'speech': msg.speech,
        })


class _TTSReal(_TTSFake):
    def __init__(self):
        super().__init__()
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        pygame.init()

    def tts_filename(self, msg: gwent.messaging.base.Message) -> str:
        return os.path.join(tempfile.gettempdir(),
                            'tts', f'{msg.content_id}.mp3')

    def clear_cache(self, card: gwent.messaging.base.Message):
        f = self.tts_filename(card)
        if os.path.exists(f):
            self._log.debug({
                'action': 'clear_cache',
                'tts_name_file': f,
            })
            os.unlink(f)

    async def announce(self, msg: gwent.messaging.base.Message):
        await super().announce(msg)

        f = self.tts_filename(msg)

        if not os.path.exists(f):
            self._log.debug({
                'action': 'tts',
                'speech': msg.speech,
                'tts_name_file': f,
            })
            tts_name = gtts.gTTS(msg.speech, lang='en')
            tts_name.save(f)

        self._log.debug({
            'action': 'announce',
            'speech': msg.speech,
        })

        speech = pygame.mixer.Sound(f)
        pygame.mixer.Sound.play(speech)
        await asyncio.sleep(speech.get_length())
