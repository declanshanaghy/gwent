"""Discard widget: P1/P2 discard piles. Scrollable."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2


class _DiscardContent(Static):
    DEFAULT_CSS = """
    _DiscardContent { width: 1fr; min-height: 100%; }
    """

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

        p1_cards = []
        for c in p1_disc:
            text = card_display(c)
            if state.is_highlighted(f"discard:{P1}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p1_cards.append(text)
        p2_cards = []
        for c in p2_disc:
            text = card_display(c)
            if state.is_highlighted(f"discard:{P2}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p2_cards.append(text)

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f5d1\ufe0f Discard ({len(p1_disc)} | {len(p2_disc)})")


class DiscardWidget(Vertical):

    DEFAULT_CSS = """
    DiscardWidget {
        height: 1fr;
    }
    """

    def compose(self):
        yield _DiscardContent()
