"""Board widget: score title, 3 combat rows x 2 players."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display_short, ROW_EMOJI, WEATHER_EMOJI, ZAP,
)
from gwent_tui.game_state import P1, P2

ROW_COLOR = {
    "close": "orange1",
    "ranged": "orchid",
    "siege": "turquoise2",
}


class BoardWidget(Static):

    def _format_row(self, cards, row_name, row_emoji, weather_tag, has_horn,
                    row_score=0, weather_active=False):
        rc = ROW_COLOR.get(row_name, "white")
        horn_tag = " \U0001f4ef\U0001f50a" if has_horn else ""
        header = f"[bold {rc}]{row_emoji} {row_name.title()}:{weather_tag}{horn_tag} {ZAP}{row_score}[/bold {rc}]"

        if not cards:
            return header

        lines = [header]
        for c in cards:
            lines.append(f"  {card_display_short(c, weather_active=weather_active)}")
        return "\n".join(lines)

    def render(self):
        state = self.app.state
        p1s = state.scores[P1]
        p2s = state.scores[P2]
        title = Text.from_markup(
            f"\u2694\ufe0f [bold yellow]{p1s}[/bold yellow]"
            f" [dim]vs[/dim] "
            f"[bold dodger_blue2]{p2s}[/bold dodger_blue2]"
        )

        table = Table(
            title=title,
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
            show_lines=True,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for row_name in ("close", "ranged", "siege"):
            re = ROW_EMOJI.get(row_name, "")
            weather_active = row_name in state.weather_rows
            weather_tag = f" {WEATHER_EMOJI.get(row_name, '')}" if weather_active else ""

            p1_cards = state.board_rows[P1].get(row_name, [])
            p2_cards = state.board_rows[P2].get(row_name, [])

            p1_horn = row_name in state.commander_horn_rows.get(P1, set())
            p2_horn = row_name in state.commander_horn_rows.get(P2, set())

            p1_row_score = state.row_scores[P1].get(row_name, 0)
            p2_row_score = state.row_scores[P2].get(row_name, 0)

            p1_text = self._format_row(p1_cards, row_name, re, weather_tag, p1_horn,
                                       p1_row_score, weather_active=weather_active)
            p2_text = self._format_row(p2_cards, row_name, re, weather_tag, p2_horn,
                                       p2_row_score, weather_active=weather_active)

            table.add_row(p1_text, p2_text)

        return Panel(table)
