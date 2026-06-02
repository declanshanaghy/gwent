"""Full-screen card zoom — blow up a single card's art for inspection.

Used by the New Game screen: tapping a leader card opens this over the menu,
showing just that card large. Tap anywhere, Esc or q to close.
"""
from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static
from textual_image.widget import TGPImage

from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import FACTION_COLOR

log = logging.getLogger("gwent_tui.card_zoom")


class CardZoomModal(ModalScreen):
    """A single card, blown up full-screen and centered."""

    DEFAULT_CSS = """
    CardZoomModal {
        align: center middle;
        background: $background 88%;
    }
    #cz-box {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #cz-img {
        width: auto;
        height: 1fr;
    }
    #cz-name {
        width: 100%;
        height: 2;
        content-align: center middle;
        text-align: center;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, card: dict) -> None:
        super().__init__()
        self.card = card or {}
        log.info("CardZoomModal __init__ card=%s", self.card.get("name"))

    def compose(self) -> ComposeResult:
        with Vertical(id="cz-box"):
            path = resolve_card_image(self.card)
            yield TGPImage(path or "", id="cz-img")
            name = self.card.get("name", "")
            faction = self.card.get("faction", "")
            color = FACTION_COLOR.get(faction, "white")
            yield Static(f"[{color}]{name}[/]", id="cz-name")

    def on_click(self, event) -> None:
        # Tap anywhere to dismiss — it's a focused, single-card view.
        self.dismiss()
