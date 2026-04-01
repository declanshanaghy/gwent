"""Footer widget: event log — auto-scrolls to show newest events."""

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class FooterWidget(Static):

    def render(self):
        state = self.app.state

        # Calculate how many lines fit (widget height minus panel border)
        available = max(1, self.size.height - 2)

        if state.event_log:
            recent = list(state.event_log)[-available:]
            # Events already contain Rich markup (timestamp + color from _log_event)
            parts = [Text.from_markup(e) for e in recent]
        else:
            parts = [Text.from_markup("[dim]Waiting for events...[/dim]")]

        return Panel(Group(*parts), title="Events", style="dim")
