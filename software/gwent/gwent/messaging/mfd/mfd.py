from typing import List, Iterable

import gwent.messaging.base
import gwent.messaging.mfd.choice

KIND = 'mfd'
CHOICES = 'choices'


class Message(gwent.messaging.base.Message):
    @staticmethod
    def from_properties(choices: List[gwent.messaging.mfd.choice.Message]):
        instance = {
            CHOICES: [c.instance for c in choices]
        }
        return Message(instance)

    @property
    def kind(self):
        return 'mfd'

    @property
    def choices(self):
        return self.instance[CHOICES]

    def is_valid_choice(self, id):
        return id in self.choice_id_iter()

    def choice_id_iter(self) -> Iterable[str]:
        for c in self.choice_iter():
            yield c.id

    def choice_iter(self) -> Iterable[gwent.messaging.mfd.choice.Message]:
        for choice in self.choices:
            yield gwent.messaging.mfd.choice.Message(choice)
