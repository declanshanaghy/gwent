import logging
import os
import tempfile

import pygame.mixer

import gtts
import gwent.cards


class TTS(object):
    _log = logging.getLogger(__name__)

    def tts_name_file(self, card: gwent.cards.Card) -> str:
        return os.path.join(tempfile.gettempdir(), f'{card.id}.mp3')

    def clear_cache(self, card: gwent.cards.Card):
        f = self.tts_name_file(card)
        if os.path.exists(f):
            self._log.debug({
                'action': 'clear_cache',
                'tts_name_file': f,
            })
            os.unlink(f)

    async def read_card(self, card: gwent.cards.Card):
        f = self.tts_name_file(card)

        if not os.path.exists(f):
            self._log.debug({
                'action': 'tts',
                'full_name': card.full_name,
                'name': card.name,
                'tts_name_file': f,
            })
            tts_name = gtts.gTTS(card.name, lang='en')
            tts_name.save(f)

        self._log.info({
            'action': 'speak',
            'full_name': card.full_name,
            'name': card.name,
            'tts_name_file': f,
        })

        speech = pygame.mixer.Sound(f)
        pygame.mixer.Sound.play(speech)
        # speech.get_length()


