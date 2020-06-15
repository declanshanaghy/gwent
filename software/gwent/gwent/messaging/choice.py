from typing import List, Iterable

import gwent.messaging.base

KIND = 'choice'
ID = 'id'
TEXT = 'text'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def from_properties(id: str, text:str):
        instance = {
            ID: id,
            TEXT: text
        }
        return Message(instance)

    @property
    def id(self):
        return self.instance[ID]

    @property
    def text(self):
        return self.instance[TEXT]

    @property
    def kind(self):
        return KIND

    def should_validate(self):
        return False

