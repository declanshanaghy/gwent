"""TUI menu mirror message.

Parallel to `mfd.py` but distinct: each menu is identified by `menu_id` and
published RETAINED to `gwent/menu/present/{menu_id}` so any client can render
whichever menu is active without a request roundtrip. Selections come back on
`gwent/menu/choose` carrying `{menu_id, id}`.
"""
from typing import Iterable, List

import gwent.messaging.base

KIND = 'menu'

MENU_ID = 'menu_id'
PROMPT = 'prompt'
CHOICES = 'choices'

# Well-known menu IDs (also strings used by the TUI; keep in sync).
MENU_MAIN = 'main'
MENU_ASSIGN_P1 = 'assign-p1'
MENU_ASSIGN_P2 = 'assign-p2'
MENU_IN_GAME = 'in-game-menu'
MENU_STEP = 'step'


class Choice(dict):
    """A single menu choice. dict-shaped so it serializes naturally."""

    def __init__(self, id: str, text: str, description: str = None,
                 icon: str = None, disabled: bool = False):
        super().__init__()
        self['id'] = id
        self['text'] = text
        if description:
            self['description'] = description
        if icon:
            self['icon'] = icon
        if disabled:
            self['disabled'] = True


class Message(gwent.messaging.base.Message):
    """A menu broadcast or selection.

    Use `Message.with_choices(menu_id, choices, prompt=...)` to compose a menu
    for publishing. The same Message class is used to wrap an incoming
    `gwent/menu/choose` (which carries `menu_id` + `id`).
    """

    @staticmethod
    def with_choices(menu_id: str, choices: List[Choice],
                     prompt: str = None) -> 'Message':
        body = {
            MENU_ID: menu_id,
            CHOICES: [dict(c) for c in choices],
        }
        if prompt:
            body[PROMPT] = prompt
        return Message(body)

    @staticmethod
    def with_selection(menu_id: str, choice_id: str) -> 'Message':
        """Compose a `gwent/menu/choose` payload.

        Note: this skips schema validation since the schema is for the
        `present` shape (choices required). Choose messages carry a single
        `id` instead.
        """
        m = Message.__new__(Message)
        m._instance = {
            'kind': KIND,
            MENU_ID: menu_id,
            'id': choice_id,
        }
        m._schema = None
        # We use Message.__new__ above to bypass __init__'s schema validation.
        from gwent.utils.logging import get_logger
        m._log = get_logger('gwent.messaging.menu.Message')
        return m

    @property
    def kind(self) -> str:
        return KIND

    @property
    def menu_id(self) -> str:
        return self._instance.get(MENU_ID)

    @property
    def prompt(self) -> str:
        return self._instance.get(PROMPT)

    @property
    def choices(self) -> list:
        return self._instance.get(CHOICES, [])

    @property
    def selected_id(self) -> str:
        """The selected choice id from a `gwent/menu/choose` payload."""
        return self._instance.get('id')

    def is_valid_choice(self, id: str) -> bool:
        return id in list(self.choice_id_iter())

    def choice_id_iter(self) -> Iterable[str]:
        for c in self.choices:
            yield c.get('id')

    def should_validate(self) -> bool:
        # Choose-shape messages (with `id` but no `choices`) skip schema check.
        return CHOICES in self._instance

    @property
    def announcement(self):
        return self.prompt
