"""Timers widget: move timing stats for both players."""

import time

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import FACTION_STYLE
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.header import _leader_nick


class TimersWidget(Static):

    def render(self):
        state = self.app.state

        elapsed = time.monotonic() - state._turn_start
        is_p1_turn = state.current_player == P1

        lines = []
        for p, label in ((P1, "P1"), (P2, "P2")):
            leader = state.leaders.get(p)
            nick = _leader_nick(leader) if leader else label
            faction = state.factions.get(p, "")
            fc = FACTION_STYLE.get(faction, ("white", "grey30", "white"))[0]

            avg = state.avg_move_time(p)
            n = state.move_count(p)
            avg_str = f"{avg:.0f}s" if n else "-"

            if (p == P1 and is_p1_turn) or (p == P2 and not is_p1_turn):
                turn_str = f"[bold]{elapsed:.0f}s[/bold]"
                marker = "\u25b6 "
            else:
                turn_str = "[dim]-[/dim]"
                marker = "  "

            lines.append(
                f"{marker}[{fc}]{nick}[/{fc}]"
            )
            lines.append(
                f"  now: {turn_str}  avg: {avg_str}  ({n})"
            )

        content = "\n".join(lines)
        return Panel(Text.from_markup(content), title="\u23f1 Timers", style="dim")
