"""TUI stage: RegisterLeaders — 2-pane P1|P2 leader registration."""

from textual.containers import Vertical

from gwent_tui.widgets.main_menu import MainMenuWidget


class RegisterLeadersStage(Vertical):
    DEFAULT_CSS = """
    RegisterLeadersStage { height: 1fr; }
    """

    def compose(self):
        yield MainMenuWidget(id="reg-leaders-content")
