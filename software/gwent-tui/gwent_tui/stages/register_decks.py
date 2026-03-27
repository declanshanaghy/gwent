"""TUI stage: RegisterDecks — 2-pane P1|P2 deck registration."""

from textual.containers import Vertical

from gwent_tui.widgets.main_menu import MainMenuWidget


class RegisterDecksStage(Vertical):
    DEFAULT_CSS = """
    RegisterDecksStage { height: 1fr; }
    """

    def compose(self):
        yield MainMenuWidget(id="reg-decks-content")
