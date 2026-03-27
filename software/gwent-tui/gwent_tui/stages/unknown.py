"""TUI stage: Unknown — error screen for unimplemented stages."""

from textual.containers import Vertical

from gwent_tui.widgets.unknown_stage import UnknownStageWidget


class UnknownStage(Vertical):
    DEFAULT_CSS = """
    UnknownStage { height: 1fr; }
    """

    def compose(self):
        yield UnknownStageWidget(id="unknown-content")
