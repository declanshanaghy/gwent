"""Hands widget: P1/P2 hands + leaders. Scrollable."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display, leader_display
from gwent_tui.game_state import P1, P2


class _HandsContent(Static):
    DEFAULT_CSS = """
    _HandsContent { width: 1fr; min-height: 100%; }
    """

    def render(self):
        state = self.app.state
        p1_count = len(state.hands[P1])
        p2_count = len(state.hands[P2])

        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_rows = [leader_display(state.leaders[P1], used=state.leader_used.get(P1, False))]
        p2_rows = [leader_display(state.leaders[P2], used=state.leader_used.get(P2, False))]
        p1_rows.append("[dim]" + "\u2500" * 30 + "[/dim]")
        p2_rows.append("[dim]" + "\u2500" * 30 + "[/dim]")

        for c in state.hands[P1]:
            p1_rows.append(card_display(c))
        for c in state.hands[P2]:
            p2_rows.append(card_display(c))

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
