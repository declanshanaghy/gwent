"""Board widget: 3 combat rows x 2 players, plus top-level scoreboard."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display_short, gems_display, ROW_EMOJI, WEATHER_EMOJI, WEATHER_NAME, FLAG, ZAP,
)
from gwent_tui.game_state import P1, P2

ROW_COLOR = {
    "close": "orange1",
    "ranged": "orchid",
    "siege": "turquoise2",
}


class ScoreboardWidget(Static):
    """Top-level scoreboard: P1 status | scores | P2 status."""

    def render(self):
        state = self.app.state
        p1s = state.scores[P1]
        p2s = state.scores[P2]

        # Weather
        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name}")
            weather = " | ".join(weather_items)
        else:
            weather = ""

        # Passed status
        p1_passed = state.passed.get(P1, False)
        p2_passed = state.passed.get(P2, False)
        p1_pass = f"{FLAG}" if p1_passed else ""
        p2_pass = f"{FLAG}" if p2_passed else ""

        # Leader status
        p1_ldr = "\U0001f451" + ("[dim]x[/dim]" if state.leader_used.get(P1) else "[green]\u26a1[/green]")
        p2_ldr = ("[dim]x[/dim]" if state.leader_used.get(P2) else "[green]\u26a1[/green]") + "\U0001f451"

        # Gems (highlight on change)
        p1_gems_str = gems_display(state.gems.get(P1, 0))
        p2_gems_str = gems_display(state.gems.get(P2, 0))
        if state.is_highlighted(f"gems:{P1}"):
            p1_gems_str = f"[on dark_red]{p1_gems_str}[/on dark_red]"
        if state.is_highlighted(f"gems:{P2}"):
            p2_gems_str = f"[on dark_red]{p2_gems_str}[/on dark_red]"

        # Score highlights
        p1s_style = "on dark_green" if state.is_highlighted(f"score:{P1}") else ""
        p2s_style = "on dark_green" if state.is_highlighted(f"score:{P2}") else ""
        p1s_open = f"[{p1s_style}]" if p1s_style else ""
        p1s_close = f"[/{p1s_style}]" if p1s_style else ""
        p2s_open = f"[{p2s_style}]" if p2s_style else ""
        p2s_close = f"[/{p2s_style}]" if p2s_style else ""

        # Build: P1 info | score | weather | score | P2 info
        left = f"[bold yellow]P1[/bold yellow] {p1_ldr} {p1_gems_str} {p1_pass}"
        center = (
            f"\U0001f5e1\ufe0f {p1s_open}[bold yellow]{p1s}[/bold yellow]{p1s_close}"
            f"  \u2694\ufe0f  "
            f"{p2s_open}[bold dodger_blue2]{p2s}[/bold dodger_blue2]{p2s_close} \U0001f6e1\ufe0f"
        )
        if weather:
            center += f"  {weather}"
        right = f"{p2_pass} {p2_gems_str} {p2_ldr} [bold dodger_blue2]P2[/bold dodger_blue2]"

        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(ratio=1, justify="left")
        table.add_column(ratio=2, justify="center")
        table.add_column(ratio=1, justify="right")
        table.add_row(
            Text.from_markup(left),
            Text.from_markup(center),
            Text.from_markup(right),
        )

        return Panel(table, title="\U0001f3c6 Scoreboard")


class _BoardRows(Static):
    """The 3 combat rows (close, ranged, siege) for both players."""
    DEFAULT_CSS = """
    _BoardRows { width: 1fr; min-height: 100%; }
    """

    def _format_row(self, cards, row_name, row_emoji, weather_tag, has_horn,
                    row_score=0, weather_active=False, player=None):
        rc = ROW_COLOR.get(row_name, "white")
        horn_tag = " \U0001f4ef\U0001f50a" if has_horn else ""
        header = f"[bold {rc}]{row_emoji} {row_name.title()}:{weather_tag}{horn_tag}  {ZAP} {row_score}[/bold {rc}]"

        if not cards:
            return header

        state = self.app.state
        lines = [header]
        for c in cards:
            name = c.get("name", "")
            hl_key = f"board:{player}:{row_name}:{name}" if player else ""
            text = card_display_short(c, weather_active=weather_active)
            if player and state.is_highlighted(hl_key):
                lines.append(f"  [on dark_green]{text}[/on dark_green]")
            else:
                lines.append(f"  {text}")
        return "\n".join(lines)

    def render(self):
        state = self.app.state

        table = Table(
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
                                       p1_row_score, weather_active=weather_active,
                                       player=P1)
            p2_text = self._format_row(p2_cards, row_name, re, weather_tag, p2_horn,
                                       p2_row_score, weather_active=weather_active,
                                       player=P2)

            table.add_row(p1_text, p2_text)

        return Panel(table, title="\u2694\ufe0f Board")


class BoardWidget(Vertical):

    DEFAULT_CSS = """
    BoardWidget {
        height: 1fr;
    }
    """

    def compose(self):
        yield _BoardRows()
