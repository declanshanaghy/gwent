"""Client-initiated game start.

The New Game wizard lives client-side: the TUI proposes both sides (faction,
leader, deck of cards, controller) and only on START sends them here for the
server to deal. Each side is independent JSON — no shared file load.

Published to `gwent/game/start`. Body:
  {"kind": "game_start",
   "p1": {"controller": "human", "deck": [<card dict>, ...]},
   "p2": {"controller": "anthropic/claude-sonnet-4-6", "deck": [...]}}
The first leader-specialty card in each deck becomes that side's leader.
"""
import gwent.messaging.base

KIND = 'game_start'
P1 = 'p1'
P2 = 'p2'


class Message(gwent.messaging.base.Message):

    @staticmethod
    def with_sides(p1: dict, p2: dict) -> 'Message':
        """p1/p2: {"controller": str, "deck": [card dict, ...]}."""
        return Message({P1: p1, P2: p2})

    @property
    def kind(self) -> str:
        return KIND

    @property
    def announcement(self):
        return None

    @property
    def p1(self) -> dict:
        return self._instance.get(P1, {})

    @property
    def p2(self) -> dict:
        return self._instance.get(P2, {})
