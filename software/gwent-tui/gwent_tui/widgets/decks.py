"""Decks widget: P1/P2 remaining deck cards. Scrollable."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2


class _DecksContent(Static):
    """Inner content for decks — rendered by Textual."""
    DEFAULT_CSS = """
    _DecksContent { width: 1fr; min-height: 100%; }
    """

    def render(self):
        state = self.app.state
        p1_count = len(state.decks[P1])
        p2_count = len(state.decks[P2])

        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_cards = [card_display(c) for c in state.decks[P1]]
        p2_cards = [card_display(c) for c in state.decks[P2]]

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f4e6 Deck ({p1_count} | {p2_count})")


class DecksWidget(Vertical):

    DEFAULT_CSS = """
    DecksWidget {
        height: 1fr;
    }
    """

    def compose(self):
        yield _DecksContent()

    def refresh_content(self):
        for w in self.query("_DecksContent"):
            w.refresh()
