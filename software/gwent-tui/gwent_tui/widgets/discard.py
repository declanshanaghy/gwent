"""Discard widget: P1/P2 discard piles."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2


class DiscardWidget(Static):

    def render(self):
        state = self.app.state
        p1_disc = state.discard[P1]
        p2_disc = state.discard[P2]

        if not p1_disc and not p2_disc:
            return Panel(
                Text("No discards", justify="center", style="dim"),
                title="\U0001f5d1\ufe0f Discard",
            )

        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_cards = [card_display(c) for c in p1_disc]
        p2_cards = [card_display(c) for c in p2_disc]

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f5d1\ufe0f Discard ({len(p1_disc)} | {len(p2_disc)})")
