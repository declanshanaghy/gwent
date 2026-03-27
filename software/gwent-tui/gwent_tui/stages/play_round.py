"""TUI stage: PlayRound — full game board with all panes."""

from textual.containers import Horizontal, Vertical

from gwent_tui.widgets.board import BoardWidget, ScoreboardWidget
from gwent_tui.widgets.hands import HandsWidget
from gwent_tui.widgets.decks import DecksWidget
from gwent_tui.widgets.discard import DiscardWidget


class PlayRoundStage(Vertical):
    DEFAULT_CSS = """
    PlayRoundStage { height: 1fr; }
    PlayRoundStage #scoreboard { height: 3; }
    PlayRoundStage #columns { height: 1fr; }
    PlayRoundStage #left { width: 1fr; }
    PlayRoundStage #right { width: 1fr; }
    PlayRoundStage #board-area { height: 1fr; }
    PlayRoundStage #discard-area { height: 1fr; min-height: 5; }
    PlayRoundStage #hands-area { height: 2fr; }
    PlayRoundStage #decks-area { height: 1fr; }
    """

    def compose(self):
        yield ScoreboardWidget(id="scoreboard")
        with Horizontal(id="columns"):
            with Vertical(id="left"):
                yield BoardWidget(id="board-area")
                yield DiscardWidget(id="discard-area")
            with Vertical(id="right"):
                yield HandsWidget(id="hands-area")
                yield DecksWidget(id="decks-area")
