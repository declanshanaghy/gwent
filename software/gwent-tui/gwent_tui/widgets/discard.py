"""Discard widget: P1/P2 discard piles. Scrollable."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.board import SPLIT_BOX


class _DiscardContent(Static):
    DEFAULT_CSS = """
    _DiscardContent { width: 1fr; }
    """

    def _max_name(self):
        """Compute max card name length based on pane width."""
        col_width = max(10, (self.size.width - 4) // 2)
        return max(8, col_width - 12)

    def render(self):
        state = self.app.state
        p1_disc = state.discard[P1]
        p2_disc = state.discard[P2]

        # Hide entirely when both discard piles are empty
        p1_ghosts = state.get_ghosts("discard", P1)
        p2_ghosts = state.get_ghosts("discard", P2)
        if not p1_disc and not p2_disc and not p1_ghosts and not p2_ghosts:
            self.styles.display = "none"
            return Text("")
        self.styles.display = "block"

        table = Table(
            box=SPLIT_BOX,
            expand=True,
            padding=(0, 1),
            show_header=False,
            show_edge=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        mn = self._max_name()
        p1_cards = []
        # Show ghost (removed) cards first with red strikethrough (medic resurrect)
        for c in state.get_ghosts("discard", P1):
            text = card_display(c, max_name=mn)
            p1_cards.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        for c in p1_disc:
            text = card_display(c, max_name=mn)
            if state.is_highlighted(f"discard:{P1}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p1_cards.append(text)
        p2_cards = []
        for c in state.get_ghosts("discard", P2):
            text = card_display(c, max_name=mn)
            p2_cards.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        for c in p2_disc:
            text = card_display(c, max_name=mn)
            if state.is_highlighted(f"discard:{P2}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p2_cards.append(text)

        if not p1_cards:
            p1_cards.append("")
        if not p2_cards:
            p2_cards.append("")

        # Pad shorter column so vertical separator runs full height
        target = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (target - len(p1_cards)))
        p2_cards.extend([""] * (target - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f5d1 Discard ({len(p1_disc)} | {len(p2_disc)})")


class DiscardWidget(Vertical):

    DEFAULT_CSS = """
    DiscardWidget {
        height: auto;
    }
    """

    def compose(self):
        yield _DiscardContent()
