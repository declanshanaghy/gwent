"""TUI stage: RoundEnd — shows the round summary while server processes round end."""

from gwent_tui.stages.round_summary import RoundSummaryStage


class RoundEndStage(RoundSummaryStage):
    """Show round summary during the server's RoundEnd stage.

    The server stays in RoundEnd for ~10 seconds while it processes
    faction abilities and the between-rounds pause. During that time
    the TUI shows the round summary with scores and stats.
    """
    pass
