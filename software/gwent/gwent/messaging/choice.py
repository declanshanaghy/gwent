from typing import List, Iterable

import gwent.messaging.base

KIND = 'choice'
ID = 'id'
TEXT = 'text'

OK_ID = 'y'
OK_TXT = 'ok'
CANCEL_ID = 'n'
CANCEL_TXT = 'cancel'

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
    def new_ok(text=None):
        instance = {
            ID: OK_ID,
            TEXT: text or OK_TXT
        }
        return Message(instance)

    @staticmethod
    def new_cancel():
        instance = {
            ID: CANCEL_ID,
            TEXT: CANCEL_TXT
        }
        return Message(instance)

    @property
    def id(self):
        return self._instance[ID]

    @property
    def text(self):
        return self._instance[TEXT]

    @property
    def kind(self):
        return KIND

    def should_validate(self):
        return False

