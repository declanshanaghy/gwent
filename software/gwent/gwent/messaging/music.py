"""Music messaging — separate from SFX.

Published to gwent/music (retained). Completions on gwent/music/complete.
"""
import gwent.messaging.base

from datetime import datetime, timezone

KIND = 'music'

PLAY = 'play'
COMPLETE = 'complete'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_play(music: str, next_music: str = None, duration_seconds: float = None):
        instance = {
            "music": music,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if next_music:
            instance["next_music"] = next_music
        if duration_seconds:
            instance["duration_seconds"] = duration_seconds
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
