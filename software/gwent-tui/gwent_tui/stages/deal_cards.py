"""TUI stage: DealCards — shows dealing announcement."""

from textual.containers import Vertical

from gwent_tui.widgets.main_menu import MainMenuWidget


class DealCardsStage(Vertical):
    DEFAULT_CSS = """
    DealCardsStage { height: 1fr; }
    """

    def compose(self):
        yield MainMenuWidget(id="deal-cards-content")
