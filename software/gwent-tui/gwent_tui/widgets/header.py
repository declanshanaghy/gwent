"""Header widget: factions, round, active player highlight."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji, FACTION_STYLE
from gwent_tui.game_state import P1, P2

# Kept here for other widgets that import it
_STATUS_COLOR = {
    "polling": "green", "processing": "yellow",
    "error": "red", "off": "grey50", "offline": "red",
}


_STAGE_ICON = {
    "MainMenu":        "\U0001f3e0",  # house
    "RegisterLeaders": "\U0001f451",  # crown
    "RegisterDecks":   "\U0001f0cf",  # playing card
    "DealCards":       "\U0001f3b4",  # flower playing card
    "PlayRound":       "\u2694",  # crossed swords
    "RoundEnd":        "\U0001f3c1",  # chequered flag
    "GameOver":        "\U0001f3c6",  # trophy
    "DisplayWinner":   "\U0001f3c6",  # trophy
    "Offline":         "\u26a0",  # warning
    "—":               "\u23f3",      # hourglass
}


def _leader_nick(leader):
    """Short nickname from a leader card dict: 'Foltest: Son of Medell' -> 'Foltest'."""
    name = leader.get("name", "")
    return name.split(":")[0].split(" - ")[0].strip() or name


class HeaderWidget(Static):

    def _gems(self, gems, max_gems=2):
        alive = min(gems, max_gems)
        dead = max_gems - alive
        return "\U0001f48e" * alive + "\U0001f480" * dead

    def render(self):
        state = self.app.state

        stage_icon = _STAGE_ICON.get(state.stage, "\u2753")
        stage_label = Text.from_markup(
            f" {stage_icon} [dim]{state.stage}[/dim]"
        )

        # Offline mode — no player data to show
        if state.http_status == "error" or state.stage == "Offline":
            center = Text.from_markup(
                " \u26a0 [bold red]Server Offline[/bold red] — waiting for connection"
            )
            center.justify = "center"
        else:
            is_p1_turn = state.current_player == P1

            p1f = state.factions.get(P1, "")
            p2f = state.factions.get(P2, "")
            p1e = faction_emoji(p1f)
            p2e = faction_emoji(p2f)

            p1_tc, p1_bg, p1_fg = FACTION_STYLE.get(p1f, ("white", "grey30", "white"))
            p2_tc, p2_bg, p2_fg = FACTION_STYLE.get(p2f, ("white", "grey30", "white"))

            if is_p1_turn:
                p1_style = f"bold {p1_fg} on {p1_bg}"
                p2_style = p2_tc
            else:
                p1_style = p1_tc
                p2_style = f"bold {p2_fg} on {p2_bg}"

            p1_leader = state.leaders.get(P1)
            p2_leader = state.leaders.get(P2)
            p1_nick = _leader_nick(p1_leader) if p1_leader else "P1"
            p2_nick = _leader_nick(p2_leader) if p2_leader else "P2"

            p1_label = f"{p1e[0]} [{p1_style}] {p1_nick} ({p1f}) [/{p1_style}] {p1e[1]}" if p1f else f"[{p1_style}] {p1_nick} [/{p1_style}]"
            p2_label = f"{p2e[0]} [{p2_style}] {p2_nick} ({p2f}) [/{p2_style}] {p2e[1]}" if p2f else f"[{p2_style}] {p2_nick} [/{p2_style}]"

            center = Text.from_markup(
                f" {p1_label}  "
                f"\u2694 Round {state.round_number} \u2694"
                f"  {p2_label} "
            )
            center.justify = "center"

        table = Table(box=None, expand=True, show_header=False, padding=0)
        table.add_column(width=20, justify="left")
        table.add_column(ratio=1)
        table.add_row(stage_label, center)

        return Panel(table, style="bold")
