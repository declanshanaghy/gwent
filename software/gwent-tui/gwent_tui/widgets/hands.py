"""Hands widget: P1/P2 hands + leaders. Scrollable.

Tapping a hand opens the full-screen HandDetailModal for that side — left
half = P1, right half = P2 (matching the split-column layout).
"""

import logging

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Static

from gwent_tui.emoji import card_display
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.board import SPLIT_BOX

log = logging.getLogger("gwent_tui.hands")


class _HandsContent(Static):
    DEFAULT_CSS = """
    _HandsContent { width: 1fr; }
    """

    def _max_name(self):
        """Compute max card name length based on pane width."""
        col_width = max(10, (self.size.width - 4) // 2)
        return max(8, col_width - 8)

    def render(self):
        state = self.app.state
        p1_count = len(state.hands[P1])
        p2_count = len(state.hands[P2])
        mn = self._max_name()

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
            text = card_display(c, max_name=mn)
            p1_rows.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        for c in state.get_ghosts("hand", P2):
            text = card_display(c, max_name=mn)
            p2_rows.append(f"[on dark_red strike]{text}[/on dark_red strike]")

        for c in state.hands[P1]:
            text = card_display(c, max_name=mn)
            if state.is_highlighted(f"hand:{P1}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p1_rows.append(text)
        for c in state.hands[P2]:
            text = card_display(c, max_name=mn)
            if state.is_highlighted(f"hand:{P2}:{c.get('name', '')}"):
                text = f"[on dark_green]{text}[/on dark_green]"
            p2_rows.append(text)

        max_len = max(len(p1_rows), len(p2_rows))
        p1_rows.extend([""] * (max_len - len(p1_rows)))
        p2_rows.extend([""] * (max_len - len(p2_rows)))

        for p1, p2 in zip(p1_rows, p2_rows):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f0cf Hands ({p1_count} | {p2_count})")

    def on_click(self, event: events.Click) -> None:
        """Tap left half → P1 hand detail, right half → P2 hand detail."""
        width = self.size.width or 1
        player = P1 if event.x < width / 2 else P2
        log.info("Hands tapped x=%d width=%d -> %s", event.x, width, player)
        try:
            from gwent_tui.hand_detail_modal import HandDetailModal
            cards = list(self.app.state.hands.get(player, []))
            self.app.push_screen(HandDetailModal(player, cards))
        except Exception as e:
            log.error("failed to open hand detail: %s", e, exc_info=True)


class HandsWidget(VerticalScroll):

    DEFAULT_CSS = """
    HandsWidget {
        height: 1fr;
        scrollbar-size-vertical: 2;
        scrollbar-color: $accent;
        scrollbar-background: $surface-darken-1;
    }
    HandsWidget _HandsContent { height: auto; }
    """

    def compose(self):
        yield _HandsContent()
