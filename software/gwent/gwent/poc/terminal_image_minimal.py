#!/usr/bin/env python3
"""Minimal test: just render one image with textual-image."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual_image.widget import TGPImage

IMAGE_PATH = "/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/data/images/NorthernRealms/GeraltOfRivia.jpg"


class MinimalApp(App):
    CSS = """
    Screen { align: center middle; }
    #img { width: 60; height: 30; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield TGPImage(IMAGE_PATH, id="img")


if __name__ == "__main__":
    MinimalApp().run()
