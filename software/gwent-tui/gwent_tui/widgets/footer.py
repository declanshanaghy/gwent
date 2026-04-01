"""Footer widget: event log — fixed height, always shows latest 6 events."""

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

EVENT_LINES = 6


class FooterWidget(Static):

    def render(self):
        state = self.app.state

        if state.event_log:
            recent = list(state.event_log)[-EVENT_LINES:]
            parts = []
            for e in recent:
                t = Text.from_markup(e)
                t.no_wrap = True
                t.overflow = "ellipsis"
                parts.append(t)
            # Pad to exactly EVENT_LINES so the panel height stays fixed
            while len(parts) < EVENT_LINES:
                parts.insert(0, Text(""))
        else:
            parts = [Text("")] * (EVENT_LINES - 1)
            parts.append(Text.from_markup("[dim]Waiting for events...[/dim]"))

        return Panel(Group(*parts), title="Events", style="dim")
