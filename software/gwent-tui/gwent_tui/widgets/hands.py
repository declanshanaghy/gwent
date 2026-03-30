"""Hands widget: P1/P2 hands + leaders. Scrollable."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.board import SPLIT_BOX


class _HandsContent(Static):
    DEFAULT_CSS = """
    _HandsContent { width: 1fr; }
    """

    def render(self):
        state = self.app.state
        p1_count = len(state.hands[P1])
        p2_count = len(state.hands[P2])

        table = Table(
            box=SPLIT_BOX,
            expand=True,
            padding=(0, 1),
            show_header=False,
            show_edge=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_rows = []
        p2_rows = []

        # Show ghost (removed) cards first with red strikethrough
        for c in state.get_ghosts("hand", P1):
            text = card_display(c)
            p1_rows.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        for c in state.get_ghosts("hand", P2):
            text = card_display(c)
            p2_rows.append(f"[on dark_red strike]{text}[/on dark_red strike]")

        for c in state.hands[P1]:
            text = card_display(c)
            if state.is_highlighted(f"hand:{P1}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p1_rows.append(text)
        for c in state.hands[P2]:
            text = card_display(c)
            if state.is_highlighted(f"hand:{P2}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p2_rows.append(text)

        max_len = max(len(p1_rows), len(p2_rows))
        p1_rows.extend([""] * (max_len - len(p1_rows)))
        p2_rows.extend([""] * (max_len - len(p2_rows)))

        for p1, p2 in zip(p1_rows, p2_rows):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f0cf Hands ({p1_count} | {p2_count})")


class HandsWidget(Vertical):

    DEFAULT_CSS = """
    HandsWidget {
        height: 1fr;
    }
    """

    def compose(self):
        yield _HandsContent()
