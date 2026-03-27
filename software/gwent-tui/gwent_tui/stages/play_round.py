"""TUI stage: PlayRound — full game board with all panes."""

from textual.containers import Horizontal, Vertical

from gwent_tui.widgets.board import BoardWidget
from gwent_tui.widgets.hands import HandsWidget
from gwent_tui.widgets.decks import DecksWidget
from gwent_tui.widgets.discard import DiscardWidget
from gwent_tui.widgets.weather import WeatherWidget


class PlayRoundStage(Horizontal):
    DEFAULT_CSS = """
    PlayRoundStage { height: 1fr; }
    PlayRoundStage #left { width: 1fr; }
    PlayRoundStage #right { width: 1fr; }
    PlayRoundStage #board-area { height: 2fr; }
    PlayRoundStage #discard-area { height: 1fr; min-height: 5; }
    PlayRoundStage #weather-area { height: 6; }
    PlayRoundStage #hands-area { height: 2fr; }
    PlayRoundStage #decks-area { height: 1fr; }
    """

    def compose(self):
        with Vertical(id="left"):
            yield BoardWidget(id="board-area")
            yield DiscardWidget(id="discard-area")
            yield WeatherWidget(id="weather-area")
        with Vertical(id="right"):
            yield HandsWidget(id="hands-area")
            yield DecksWidget(id="decks-area")
