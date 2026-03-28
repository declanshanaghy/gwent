"""Header widget: factions, gems, round, turn, MQTT/HTTP status."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji
from gwent_tui.game_state import P1, P2
import time
import gwent_tui.snapshot as snapshot_mod

_STATUS_COLOR = {
    "polling": "green", "processing": "yellow",
    "error": "red", "off": "grey50", "offline": "red",
}

_STAGE_ICON = {
    "MainMenu":        "\U0001f3e0",  # house
    "RegisterLeaders": "\U0001f451",  # crown
    "RegisterDecks":   "\U0001f0cf",  # playing card
    "DealCards":       "\U0001f3b4",  # flower playing card
    "PlayRound":       "\u2694\ufe0f",  # crossed swords
    "RoundEnd":        "\U0001f3c1",  # chequered flag
    "GameOver":        "\U0001f3c6",  # trophy
    "DisplayWinner":   "\U0001f3c6",  # trophy
    "Offline":         "\u26a0\ufe0f",  # warning
    "—":               "\u23f3",      # hourglass
}


class HeaderWidget(Static):

    def _gems(self, gems, max_gems=2):
        alive = min(gems, max_gems)
        dead = max_gems - alive
        return "\U0001f48e" * alive + "\U0001f480" * dead

    def render(self):
        state = self.app.state

        mc = _STATUS_COLOR.get(state.mqtt_status, "grey50")
        hc = _STATUS_COLOR.get(state.http_status, "grey50")
        pt = snapshot_mod.POLL_TIMEOUT
        poll_label = f"[dim]{pt}s[/dim]" if pt > 0 else "[dim]off[/dim]"
        status = Text.from_markup(
            f"[{mc}]MQTT[/{mc}] [{hc}]HTTP[/{hc}] {poll_label} "
        )
        status.justify = "right"

        stage_icon = _STAGE_ICON.get(state.stage, "\u2753")
        stage_label = Text.from_markup(
            f" {stage_icon} [dim]{state.stage}[/dim]"
        )

        # Offline mode — no player data to show
        if state.http_status == "error" or state.stage == "Offline":
            center = Text.from_markup(
                " \u26a0\ufe0f [bold red]Server Offline[/bold red] — waiting for connection"
            )
            center.justify = "center"
        else:
            is_p1_turn = state.current_player == P1

            p1f = state.factions.get(P1, "")
            p2f = state.factions.get(P2, "")
            p1e = faction_emoji(p1f)
            p2e = faction_emoji(p2f)

            p1_label = f"{p1e[0]} [bold yellow]P1 ({p1f})[/bold yellow] {p1e[1]}" if p1f else "[bold yellow]P1[/bold yellow]"
            p2_label = f"{p2e[0]} [bold dodger_blue2]P2 ({p2f})[/bold dodger_blue2] {p2e[1]}" if p2f else "[bold dodger_blue2]P2[/bold dodger_blue2]"

            if is_p1_turn:
                turn_label = f"\U0001f3af [bold yellow]P1 to Play[/bold yellow]"
            else:
                turn_label = f"\U0001f3af [bold dodger_blue2]P2 to Play[/bold dodger_blue2]"

            # Move timing: current think time + averages
            elapsed = time.monotonic() - state._turn_start
            cur_time = f"[dim]{elapsed:.0f}s[/dim]"

            p1_avg = state.avg_move_time(P1)
            p2_avg = state.avg_move_time(P2)
            p1_n = state.move_count(P1)
            p2_n = state.move_count(P2)
            p1_time = f"[dim yellow]{p1_avg:.0f}s[/dim yellow]" if p1_n else "[dim]-[/dim]"
            p2_time = f"[dim dodger_blue2]{p2_avg:.0f}s[/dim dodger_blue2]" if p2_n else "[dim]-[/dim]"

            center = Text.from_markup(
                f" {p1_label} avg:{p1_time}    "
                f"\u2694\ufe0f Round {state.round_number} "
                f"{turn_label} {cur_time}"
                f"    avg:{p2_time} {p2_label} "
            )
            center.justify = "center"

        table = Table(box=None, expand=True, show_header=False, padding=0)
        table.add_column(width=20, justify="left")
        table.add_column(ratio=1)
        table.add_column(width=16, justify="right")
        table.add_row(stage_label, center, status)

        return Panel(table, style="bold")
