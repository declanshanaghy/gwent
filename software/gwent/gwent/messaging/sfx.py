import gwent.messaging.base


KIND = 'sfx'

EFFECT = 'effect'
ANNOUNCEMENT = 'announcement'

EFFECT_CARD_READ = 'card_read'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_announcement(announcement):
        instance = {ANNOUNCEMENT: announcement}
        return Message(instance, subkind=ANNOUNCEMENT)

    @staticmethod
    def with_effect(effect):
        instance = {EFFECT: effect}
        return Message(instance, subkind=EFFECT)

    @property
    def kind(self):
        return KIND

    @property
    def announcement(self):
        return self.instance[ANNOUNCEMENT]

    @property
    def effect(self):
        return self.instance[EFFECT]
