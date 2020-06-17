import gwent.messaging.base


KIND = 'sfx'

ANNOUNCEMENT = 'announcement'
EFFECT = 'effect'
MUSIC = 'music'
RANDOM = 'random'

EFFECT_CARD_READ = 'card_read'

MUSIC1 = 'music1'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_announcement(announcement):
        instance = {ANNOUNCEMENT: announcement}
        return Message(instance, subkind=ANNOUNCEMENT)

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
        return self.instance[ANNOUNCEMENT]

    @property
    def effect(self):
        return self.instance[EFFECT]

    @property
    def music(self):
        return self.instance[MUSIC]

    @property
    def is_random(self):
        return self.instance.get(RANDOM) is True

    @property
    def random(self):
        return self.instance[RANDOM]
