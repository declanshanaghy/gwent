import gwent.messaging.base


KIND = 'sfx'

ANNOUNCEMENT = 'announcement'
ANNOUNCEMENT_COMPLETE = 'announcement_complete'
EFFECT = 'effect'
MUSIC = 'music'
RANDOM = 'random'

EFFECT_CARD_READ = 'card_read'
EFFECT_MFD_SELECT = 'mfd_select'
EFFECT_MFD_CHOOSE = 'mfd_choose'

MUSIC1 = 'music1'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_announcement(announcement):
        instance = {ANNOUNCEMENT: announcement}
        return Message(instance, subkind=ANNOUNCEMENT)

    @staticmethod
    def with_announcement_complete(announcement):
        instance = {ANNOUNCEMENT: announcement}
        return Message(instance, subkind=ANNOUNCEMENT_COMPLETE)

    @staticmethod
    def with_effect(effect):
        instance = {EFFECT: effect}
        return Message(instance, subkind=EFFECT)

    @staticmethod
    def with_music(music:str=None, random:bool=False):
        instance = {}
        if music:
            instance[MUSIC] = music
        if random is not None:
            instance[RANDOM] = random
        return Message(instance, subkind=MUSIC)

    @property
    def kind(self):
        return KIND

    @property
    def announcement(self):
        return self._instance[ANNOUNCEMENT]

    @property
    def effect(self):
        return self._instance[EFFECT]

    @property
    def music(self):
        return self._instance[MUSIC]

    @property
    def is_random(self):
        return self._instance.get(RANDOM) is True

    @property
    def random(self):
        return self._instance[RANDOM]
