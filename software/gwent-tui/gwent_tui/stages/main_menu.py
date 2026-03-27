"""TUI stage: MainMenu — shows menu choices and server status."""

from textual.containers import Vertical
from textual.widget import Widget

from gwent_tui.widgets.main_menu import MainMenuWidget


class MainMenuStage(Vertical):
    DEFAULT_CSS = """
    MainMenuStage { height: 1fr; }
    """

    def compose(self):
        yield MainMenuWidget(id="menu-content")
