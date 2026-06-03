"""TUI stage: PlayRound — full game board with all panes."""

from textual.containers import Horizontal, Vertical

from gwent_tui.widgets.board import BoardWidget, ScoreboardWidget, PlayerBarWidget
from gwent_tui.widgets.hands import HandsWidget
from gwent_tui.widgets.decks import DecksWidget
from gwent_tui.widgets.discard import DiscardWidget


class PlayRoundStage(Horizontal):
    DEFAULT_CSS = """
    PlayRoundStage { height: 1fr; }
    PlayRoundStage #left { width: 1fr; height: 1fr; overflow: hidden; }
    PlayRoundStage #right { width: 1fr; height: 1fr; overflow: hidden; }
    PlayRoundStage #player-bar { height: auto; }
    PlayRoundStage #board-area { height: 1fr; }
    PlayRoundStage #discard-area { height: auto; min-height: 3; }
    PlayRoundStage #scoreboard { height: auto; max-height: 6; }
    PlayRoundStage #hands-area { height: auto; }
    PlayRoundStage #decks-area { height: 1fr; max-height: 13; }
    """

    def compose(self):
        with Vertical(id="left"):
            yield PlayerBarWidget(id="player-bar")
            yield BoardWidget(id="board-area")
            yield DiscardWidget(id="discard-area")
        with Vertical(id="right"):
            yield ScoreboardWidget(id="scoreboard")
            yield HandsWidget(id="hands-area")
            yield DecksWidget(id="decks-area")
