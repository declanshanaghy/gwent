"""Weather widget: active weather effects + passed status."""

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import WEATHER_EMOJI, WEATHER_NAME, FLAG
from gwent_tui.game_state import P1, P2


class WeatherWidget(Static):

    def render(self):
        state = self.app.state
        parts = []

        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name} ({row})")
            parts.append("\U0001f326\ufe0f Weather: " + ", ".join(weather_items))
        else:
            parts.append("\U0001f326\ufe0f No active weather")

        p1_passed = state.passed.get(P1, False)
        p2_passed = state.passed.get(P2, False)
        if p1_passed and p2_passed:
            parts.append(f"{FLAG} Both players passed")
        elif p1_passed:
            parts.append(f"{FLAG} P1 passed")
        elif p2_passed:
            parts.append(f"{FLAG} P2 passed")
        else:
            parts.append("\u270b Neither player has passed")

        # Leader power status
        p1_ldr = "P1 \U0001f451" + ("[dim]spent[/dim]" if state.leader_used.get(P1) else "[green]\u26a1[/green]")
        p2_ldr = "P2 \U0001f451" + ("[dim]spent[/dim]" if state.leader_used.get(P2) else "[green]\u26a1[/green]")
        parts.append(f"{p1_ldr}  {p2_ldr}")

        return Panel(Text.from_markup("\n".join(parts)), style="dim")
