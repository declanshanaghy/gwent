import gwent.messaging.base


KIND = 'sfx'

ACTION = 'action'
ACTION_ANNOUNCE = 'announce'
MESSAGE = 'message'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def from_properties(action=None, message=None):
        instance = {}
        if action is not None:
            instance[ACTION] = action

        if message is not None:
            instance[MESSAGE] = message

        return Message(instance)

    @property
    def kind(self):
        return KIND

    @property
    def action(self):
        return self.instance[ACTION]

    @property
    def message(self):
        return self.instance[MESSAGE]

    @property
    def speech(self):
        return self.message
