"""Unknown stage widget: error screen for unimplemented stages."""

from rich.align import Align
from rich.text import Text
from textual.widgets import Static

from gwent_tui.widgets.header import _STATUS_COLOR


class UnknownStageWidget(Static):

    def render(self):
        state = self.app.state
        mc = _STATUS_COLOR.get(state.mqtt_status, "grey50")
        hc = _STATUS_COLOR.get(state.http_status, "grey50")

        text = Text.from_markup(
            f"\n\n[bold red]\u26a0 Unknown Stage[/bold red]\n\n"
            f"Server is at stage: [bold yellow]{state.stage}[/bold yellow]\n\n"
            f"[red]No TUI screen implemented for this stage.[/red]\n\n"
            f"[dim]The game is running but this stage cannot be displayed.[/dim]\n\n"
            f"[{mc}]MQTT[/{mc}] [{hc}]HTTP[/{hc}]\n\n"
            f"[dim]? for help  Ctrl+S to save state[/dim]"
        )
        text.justify = "center"
        return Align.center(text, vertical="middle")
