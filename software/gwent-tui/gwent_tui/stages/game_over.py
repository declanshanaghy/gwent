"""TUI stage: GameOver — reuses game board view (final scores visible)."""

from gwent_tui.stages.play_round import PlayRoundStage


class GameOverStage(PlayRoundStage):
    """Same layout as PlayRound — board stays visible at game over."""
    pass
