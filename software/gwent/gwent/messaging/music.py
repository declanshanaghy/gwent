"""Music messaging — separate from SFX.

Published to gwent/music (retained). Completions on gwent/music/complete.
"""
import gwent.messaging.base

KIND = 'music'

PLAY = 'play'
COMPLETE = 'complete'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_play(music: str, next_music: str = None):
        instance = {"music": music}
        if next_music:
            instance["next_music"] = next_music
        return Message(instance, subkind=PLAY)

    @staticmethod
    def with_complete(music: str, source: str = "gwent"):
        instance = {"music": music, "source": source}
        return Message(instance, subkind=COMPLETE)

    @property
    def kind(self):
        return KIND

    @property
    def music(self):
        return self._instance.get("music", "")

    @property
    def next_music(self):
        return self._instance.get("next_music", "")

    @property
    def source(self):
        return self._instance.get("source", "")

    def should_validate(self):
        return True
