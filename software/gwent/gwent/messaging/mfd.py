from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.choice

KIND = 'mfd'

PROMPT = 'prompt'
OK = 'ok'
CANCEL = 'cancel'

ERROR = 'error'
CHOICES = 'choices'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_prompt(prompt: str, ok: bool = False, cancel: bool = False):
        return Message({
            PROMPT: prompt,
            OK: ok,
            CANCEL: cancel,
        }, subkind=PROMPT)

    @staticmethod
    def with_error(error:str):
        return Message({ERROR: error}, subkind=ERROR)

    @staticmethod
    def with_choices(choices:List[gwent.messaging.choice.Message]):
        return Message({CHOICES: [c.instance for c in choices]},
                       subkind=CHOICES)

    @property
    def kind(self):
        return KIND

    @property
    def prompt(self):
        return self.instance.get(PROMPT)

    @property
    def error(self):
        return self.instance.get(ERROR)

    @property
    def choices(self):
        return self.instance.get(CHOICES)

    def is_valid_choice(self, id):
        return id in self.choice_id_iter()

    def choice_id_iter(self) -> Iterable[str]:
        for c in self.choice_iter():
            yield c.id

    def choice_iter(self) -> Iterable[gwent.messaging.choice.Message]:
        for choice in self.choices:
            yield gwent.messaging.choice.Message(choice)
