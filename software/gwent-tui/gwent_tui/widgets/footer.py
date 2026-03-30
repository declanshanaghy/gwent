"""Footer widget: event log."""

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class FooterWidget(Static):

    def render(self):
        state = self.app.state
        parts = []

        if state.event_log:
            recent = list(state.event_log)[-8:]
            for e in recent:
                parts.append(f"[dim]{e}[/dim]")

        if not parts:
            parts.append("[dim]Waiting for events...[/dim]")

        from rich.console import Group
        renderables = []
        for p in parts:
            if isinstance(p, str):
                renderables.append(Text.from_markup(p))
            else:
                renderables.append(p)
        return Panel(Group(*renderables), title="Events", style="dim")
