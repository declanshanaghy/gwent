"""Weather widget: active weather effects + passed/leader status."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import WEATHER_EMOJI, WEATHER_NAME, FLAG
from gwent_tui.game_state import P1, P2


class WeatherWidget(Static):

    def render(self):
        state = self.app.state

        # Weather (center)
        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name}")
            weather = "\U0001f326 " + ", ".join(weather_items)
        else:
            weather = "\U0001f326 Clear skies"

        # Passed status
        p1_passed = state.passed.get(P1, False)
        p2_passed = state.passed.get(P2, False)
        p1_pass = f"{FLAG} [bold yellow]Passed[/bold yellow]" if p1_passed else "\u270b"
        p2_pass = f"[bold dodger_blue2]Passed[/bold dodger_blue2] {FLAG}" if p2_passed else "\u270b"

        # Leader status
        p1_ldr = "\U0001f451" + ("[dim]spent[/dim]" if state.leader_used.get(P1) else "[green]\u26a1[/green]")
        p2_ldr = ("[dim]spent[/dim]" if state.leader_used.get(P2) else "[green]\u26a1[/green]") + "\U0001f451"

        # Build table: P1 left | weather center | P2 right
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(ratio=1, justify="left")
        table.add_column(ratio=2, justify="center")
        table.add_column(ratio=1, justify="right")

        table.add_row(
            Text.from_markup(f"[bold yellow]P1[/bold yellow] {p1_pass} {p1_ldr}"),
            Text.from_markup(weather),
            Text.from_markup(f"{p2_ldr} {p2_pass} [bold dodger_blue2]P2[/bold dodger_blue2]"),
        )

        return Panel(table, style="dim")
