#!/usr/bin/env python3
"""POC: Display a Gwent card image in a Textual TUI layout.

Uses textual-image TGPImage for broad terminal compatibility.
Layout mimics the gwent-tui PlayRound stage: left board pane + right info pane.

Usage:
    python -m gwent.poc.terminal_image [image_path]

Requires: pip install textual-image
"""

import os
import sys

from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from textual_image.widget import TGPImage

# Default card image (absolute path to avoid CWD issues)
DEFAULT_IMAGE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "data", "images", "NorthernRealms", "GeraltOfRivia.jpg",
))


class CardImageWidget(Vertical):
    """Card image with a label underneath."""

    DEFAULT_CSS = """
    CardImageWidget { width: 100%; height: 100%; }
    CardImageWidget #card-image { width: 100%; height: 1fr; }
    CardImageWidget #card-label { height: 3; content-align: center middle; }
    """

    def __init__(self, image_path: str, card_name: str = "Geralt of Rivia"):
        super().__init__()
        self._image_path = image_path
        self._card_name = card_name

    def compose(self) -> ComposeResult:
        yield TGPImage(self._image_path, id="card-image")
        yield Static(
            Panel(
                Text(self._card_name, style="bold bright_white", justify="center"),
                style="bright_cyan",
            ),
            id="card-label",
        )


class FakeBoardWidget(Static):
    """Placeholder board mimicking gwent-tui layout."""

    def render(self):
        lines = [
            "[bold bright_cyan]═══ GAME BOARD ═══[/]",
            "",
            "[orange1]⚔  Close:   [dim]Geralt (10) · Ciri (9)[/][/]",
            "[orchid]🏹 Ranged:  [dim]Triss (7) · Avallac'h (0)[/][/]",
            "[turquoise2]🏰 Siege:   [dim]Villentretenmerth (7)[/][/]",
            "",
            "[dim]─── opponent ───[/]",
            "",
            "[orange1]⚔  Close:   [dim]Eredin (10) · Draug (10)[/][/]",
            "[orchid]🏹 Ranged:  [dim]Triss (7)[/][/]",
            "[turquoise2]🏰 Siege:   [dim]Earth Elemental (6)[/][/]",
        ]
        return Panel("\n".join(lines), title="Board", border_style="bright_blue")


class FakeScoreboardWidget(Static):
    """Placeholder scoreboard."""

    def render(self):
        return Panel(
            "[bold green]Player 1: 33[/]  |  [bold red]Player 2: 33[/]  |  Round 2 of 3",
            title="Scoreboard",
            border_style="bright_yellow",
        )


class FakeHandWidget(Static):
    """Placeholder hand display."""

    def render(self):
        cards = [
            "🃏 Zoltan Chivay (5)",
            "🃏 Commander's Horn",
            "🃏 Biting Frost",
            "🃏 Emiel Regis (5)",
        ]
        return Panel("\n".join(cards), title="Hand (4 cards)", border_style="bright_green")


class TerminalImageApp(App):
    """POC app: gwent-tui-like layout with a card image panel."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    CSS = """
    Screen { layout: vertical; }
    #header { height: 3; content-align: center middle; }
    #main { height: 1fr; }
    #left { width: 2fr; height: 1fr; }
    #right { width: 1fr; height: 1fr; }
    #board { height: 1fr; }
    #scoreboard { height: 3; }
    #hand { height: auto; }
    #footer { height: 1; content-align: center middle; }
    """

    def __init__(self, image_path: str):
        super().__init__()
        self._image_path = image_path

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold bright_cyan]⚔ GWENT COMPANION ⚔[/] — [dim]Terminal Image POC[/]",
            id="header",
        )
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield FakeScoreboardWidget(id="scoreboard")
                yield FakeBoardWidget(id="board")
                yield FakeHandWidget(id="hand")
            with Vertical(id="right"):
                yield Static(
                    Panel("[bold]Last Played Card[/]", border_style="bright_magenta"),
                )
                yield CardImageWidget(
                    self._image_path,
                    card_name="Geralt of Rivia",
                )
        yield Static(
            "[dim]Press Ctrl+C to quit | Renderer: TGP (kitty)[/]",
            id="footer",
        )


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE
    image_path = os.path.abspath(image_path)
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    app = TerminalImageApp(image_path)
    app.run()


if __name__ == "__main__":
    main()
