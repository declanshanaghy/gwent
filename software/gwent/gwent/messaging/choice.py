from typing import List, Iterable

import gwent.messaging.base

KIND = 'choice'
ID = 'id'
TEXT = 'text'

OK = 'ok'
CANCEL = 'cancel'

class Message(gwent.messaging.base.Message):
    @staticmethod
    def from_properties(id: str, text:str):
        instance = {
            ID: id,
            TEXT: text
        }
        return Message(instance)

    @staticmethod
    def from_dict(obj: dict):
        instance = {
            ID: obj[ID],
            TEXT: obj[TEXT]
        }
        return Message(instance)

    @staticmethod
    def new_ok():
        instance = {
            ID: OK,
            TEXT: OK
        }
        return Message(instance)

    @staticmethod
    def new_cancel():
        instance = {
            ID: CANCEL,
            TEXT: CANCEL
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

