from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.choice

KIND = 'mfd'

OK = 'ok'
OK_TEXT = 'ok_text'
CANCEL = 'cancel'
CLEAR_CHOICES = 'clear_choices'
CLEAR_PROMPT = 'clear_prompt'

PROMPT = 'prompt'
ERROR = 'error'
CHOICES = 'choices'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def with_prompt(prompt: str, ok: bool = None, cancel: bool = None,
                    clear_choices: bool = None, ok_text: str = None):
        m = { PROMPT: prompt }
        if ok is not None:
            m[OK] = ok
        if ok_text is not None:
            m[OK_TEXT] = ok_text
        if cancel is not None:
            m[CANCEL] = cancel
        if clear_choices is not None:
            m[CLEAR_CHOICES] = clear_choices

        return Message(m, subkind=PROMPT)

    @staticmethod
    def with_error(error: str):
        return Message({ERROR: error}, subkind=ERROR)

    @staticmethod
    def with_choices(choices: List[gwent.messaging.choice.Message],
                     clear_prompt: bool = False):
        return Message({
            CHOICES: [c._instance for c in choices],
            CLEAR_PROMPT: clear_prompt
        }, subkind=CHOICES)

    @property
    def kind(self):
        return KIND

    @property
    def prompt(self):
        return self._instance.get(PROMPT)

    @property
    def error(self):
        return self._instance.get(ERROR)

    @property
    def clear_choices(self):
        return self._instance.get(CLEAR_CHOICES) == True

    @property
    def clear_prompt(self):
        return self._instance.get(CLEAR_PROMPT) == True

    @property
    def has_ok(self):
        return OK in self._instance

    @property
    def ok(self):
        return self._instance[OK]

    @property
    def ok_text(self):
        return self._instance.get(OK_TEXT)

    @property
    def has_cancel(self):
        return CANCEL in self._instance

    @property
    def cancel(self):
        return self._instance[CANCEL]

    @property
    def choices(self):
        return self._instance.get(CHOICES)

    def is_valid_choice(self, id):
        return id in self.choice_id_iter()

    def choice_id_iter(self) -> Iterable[str]:
        for c in self.choice_iter():
            yield c.id

    def choice_iter(self) -> Iterable[gwent.messaging.choice.Message]:
        for choice in self.choices:
            yield gwent.messaging.choice.Message(choice)

    @property
    def announcement(self):
        return self.error or self.prompt
