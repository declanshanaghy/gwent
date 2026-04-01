import gwent.messaging.base


KIND = 'sfx'

ANNOUNCEMENT = 'announcement'
ANNOUNCEMENT_COMPLETE = 'announcement_complete'
EFFECT = 'effect'
FACTION = 'faction'

EFFECT_CARD_READ = 'card_read'
EFFECT_MFD_SELECT = 'mfd_select'
EFFECT_MFD_CHOOSE = 'mfd_choose'

# Row-specific battle SFX (picks random WAV from subdirectory)
EFFECT_CLOSE = 'close'
EFFECT_RANGED = 'ranged'
EFFECT_SIEGE = 'siege'
EFFECT_COMMANDER = 'commander'
EFFECT_CARD_PLAY = 'card'
EFFECT_WEATHER = 'weather'
EFFECT_SPECIAL = 'special'
EFFECT_LEADER = 'leader'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_announcement(announcement, faction=None):
        instance = {ANNOUNCEMENT: announcement}
        if faction:
            instance[FACTION] = faction
        return Message(instance, subkind=ANNOUNCEMENT)

    @staticmethod
    def with_announcement_complete(source="gwent", original_content_id=None):
        instance = {"source": source}
        if original_content_id:
            instance["original_content_id"] = original_content_id
        return Message(instance, subkind=ANNOUNCEMENT_COMPLETE)

    @staticmethod
    def with_effect(effect):
        instance = {EFFECT: effect}
        return Message(instance, subkind=EFFECT)

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
    def faction(self):
        return self._instance.get(FACTION)
