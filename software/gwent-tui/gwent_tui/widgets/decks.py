"""Decks widget: P1/P2 remaining deck cards. Scrollable.

Tapping a deck opens the card-list overlay for that side (left half = P1,
right half = P2) with a "Draw <NAME> from Deck" action — for when a card must
be pulled from the deck (spy, leader draw, etc.).
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

log = logging.getLogger("gwent_tui.decks")


class _DecksContent(Static):
    """Inner content for decks — rendered by Textual."""
    DEFAULT_CSS = """
    _DecksContent { width: 1fr; }
    """

    def _max_name(self):
        """Compute max card name length based on pane width."""
        col_width = max(10, (self.size.width - 4) // 2)
        return max(8, col_width - 8)

    def render(self):
        state = self.app.state
        p1_count = len(state.decks[P1])
        p2_count = len(state.decks[P2])
        p1_hl = state.is_highlighted(f"deck:{P1}")
        p2_hl = state.is_highlighted(f"deck:{P2}")

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
        # Show ghost (removed) cards first with red strikethrough (drawn to hand)
        for c in state.get_ghosts("deck", P1):
            text = card_display(c, max_name=mn)
            p1_cards.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        p1_cards.extend(card_display(c, max_name=mn) for c in state.decks[P1])
        p2_cards = []
        for c in state.get_ghosts("deck", P2):
            text = card_display(c, max_name=mn)
            p2_cards.append(f"[on dark_red strike]{text}[/on dark_red strike]")
        p2_cards.extend(card_display(c, max_name=mn) for c in state.decks[P2])

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        def fmt(count, hl):
            txt = str(count)
            return f"[on dark_green]{txt}[/on dark_green]" if hl else txt

        p1_tag = fmt(p1_count, p1_hl)
        p2_tag = fmt(p2_count, p2_hl)
        return Panel(table, title=f"\U0001f4e6 Deck ({p1_tag} | {p2_tag})")

    def on_click(self, event: events.Click) -> None:
        """Tap left half → P1 deck, right half → P2 deck (Draw from Deck)."""
        width = self.size.width or 1
        player = P1 if event.x < width / 2 else P2
        cards = list(self.app.state.decks.get(player, []))
        log.info("Deck tapped x=%d width=%d -> %s (%d cards)",
                 event.x, width, player, len(cards))
        try:
            from gwent_tui.hand_detail_modal import DeckDetailModal
            self.app.push_screen(DeckDetailModal(player, cards))
        except Exception as e:
            log.error("failed to open deck detail: %s", e, exc_info=True)


class DecksWidget(VerticalScroll):

    DEFAULT_CSS = """
    DecksWidget {
        height: 1fr;
        scrollbar-size-vertical: 2;
        scrollbar-color: $accent;
        scrollbar-background: $surface-darken-1;
    }
    DecksWidget _DecksContent { height: auto; }
    """

    def compose(self):
        yield _DecksContent()

    def refresh_content(self):
        for w in self.query("_DecksContent"):
            w.refresh()
