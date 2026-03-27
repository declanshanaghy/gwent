"""TUI stage: RoundEnd — reuses game board view (scores still visible)."""

from gwent_tui.stages.play_round import PlayRoundStage


class RoundEndStage(PlayRoundStage):
    """Same layout as PlayRound — board stays visible during round end."""
    pass
