"""TUI stage: Offline — shown when the gwent server is unreachable."""

from rich.panel import Panel
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Static


class _OfflineContent(Static):

    def render(self):
        lines = [
            "",
            "[bold red]Server Offline[/bold red]",
            "",
            "[dim]The gwent game server is not responding.[/dim]",
            "[dim]Waiting for connection...[/dim]",
            "",
            "Start the server with:",
            "  [bold cyan]bash scripts/dev-server.sh gwent start[/bold cyan]",
            "",
            "Or with a saved state:",
            "  [bold cyan]GWENT_STATE=<file> bash scripts/dev-server.sh gwent start[/bold cyan]",
            "",
        ]
        return Panel(
            Text.from_markup("\n".join(lines)),
            title="\u26a0  Gwent Server Offline",
            style="red",
        )


class OfflineStage(Vertical):
    DEFAULT_CSS = """
    OfflineStage { height: 1fr; align: center middle; }
    """

    def compose(self):
        yield _OfflineContent()
