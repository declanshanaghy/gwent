"""Header widget: factions, round, active player highlight."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji, FACTION_STYLE
from gwent_tui.game_state import P1, P2
import gwent_tui.snapshot as snapshot_mod
from gwent_tui import tts as tts_mod

# Kept here for other widgets that import it
_STATUS_COLOR = {
    "polling": "green", "processing": "yellow",
    "error": "red", "off": "grey50", "offline": "red",
}

_CONN_ICON = {
    "off":        ("\u26aa", "grey50"),
    "alive":      ("\u2705", "green"),
    "polling":    ("\u2705", "green"),
    "processing": ("\u23f3", "yellow"),
    "error":      ("\u274c", "red"),
}

_TTS_COLOR = {
    "say": "bright_cyan", "piper": "bright_magenta",
    "gtts": "bright_yellow", "elevenlabs": "orange1",
    "openai": "bright_blue", "none": "grey50",
    "off": "red", "?": "grey50", "auto": "grey50",
}

_STAGE_ICON = {
    "MainMenu":        "\U0001f3e0",
    "RegisterLeaders": "\U0001f451",
    "RegisterDecks":   "\U0001f0cf",
    "DealCards":       "\U0001f3b4",
    "PlayRound":       "\u2694",
    "RoundEnd":        "\U0001f3c1",
    "GameOver":        "\U0001f3c6",
    "DisplayWinner":   "\U0001f3c6",
    "Offline":         "\u26a0",
    "\u2014":          "\u23f3",
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

        # --- Row 1: status bar ---
        stage_icon = _STAGE_ICON.get(state.stage, "\u2753")
        stage_label = f" {stage_icon} [dim]{state.stage}[/dim]"

        mqtt_icon, mqtt_c = _CONN_ICON.get(state.mqtt_status, ("\u2753", "grey50"))
        http_icon, http_c = _CONN_ICON.get(state.http_status, ("\u2753", "grey50"))
        server_tts = state.server_tts or "?"
        provider = tts_mod._get_provider()
        client_tts = tts_mod._provider_name or "auto"
        if provider and provider is not False:
            client_tts = tts_mod._provider_name or type(provider).__name__.replace("Provider", "").lower()
        elif provider is False:
            client_tts = "off"
        s_color = _TTS_COLOR.get(server_tts, "grey50")
        c_color = _TTS_COLOR.get(client_tts, "grey50")
        pt = snapshot_mod.POLL_TIMEOUT
        status_str = (
            f"{mqtt_icon} [{mqtt_c}]MQTT[/{mqtt_c}] "
            f"{http_icon} [{http_c}]HTTP[/{http_c}] "
            f"\U0001f50a [{s_color}]s:{server_tts}[/{s_color}] [{c_color}]c:{client_tts}[/{c_color}] "
            f"\U0001f504 {pt}s"
        )

        row1 = Table(box=None, expand=True, show_header=False, padding=0)
        row1.add_column(justify="left", ratio=1)
        row1.add_column(justify="right", ratio=1)
        row1.add_row(
            Text.from_markup(stage_label),
            Text.from_markup(status_str),
        )

        # --- Row 2: P1 label | Round | P2 label ---
        row2 = Table(box=None, expand=True, show_header=False, padding=0)
        row2.add_column(justify="left", ratio=2)
        row2.add_column(justify="center", ratio=1)
        row2.add_column(justify="right", ratio=2)

        if state.http_status == "error" or state.stage == "Offline":
            row2.add_row(
                Text.from_markup(" \u26a0 [bold red]Server Offline[/bold red]"),
                Text(""),
                Text(""),
            )
        else:
            round_label = f"\u2694 Round {state.round_number} \u2694"

            is_p1_turn = state.current_player == P1
            p1f = state.factions.get(P1, "")
            p2f = state.factions.get(P2, "")
            p1e = faction_emoji(p1f)
            p2e = faction_emoji(p2f)
            p1_tc, _, p1_fg = FACTION_STYLE.get(p1f, ("white", "grey30", "white"))
            p2_tc, _, p2_fg = FACTION_STYLE.get(p2f, ("white", "grey30", "white"))

            # Use the faction text color as highlight bg so it matches card colors
            if is_p1_turn:
                p1_style = f"bold {p1_fg} on {p1_tc}"
                p2_style = p2_tc
            else:
                p1_style = p1_tc
                p2_style = f"bold {p2_fg} on {p2_tc}"

            # Player name (model name or "Player 1")
            p1_pname = state.player_names.get(P1, "")
            p2_pname = state.player_names.get(P2, "")

            # Leader name (full title)
            p1_leader = state.leaders.get(P1)
            p2_leader = state.leaders.get(P2)
            p1_lname = p1_leader.get("name", "") if p1_leader else ""
            p2_lname = p2_leader.get("name", "") if p2_leader else ""

            # Build display: "emoji Name (Leader) emoji" or just "emoji Faction emoji"
            if p1_pname and p1_pname not in ("Player 1",):
                p1_text = f"{p1_pname}"
                if p1_lname:
                    p1_text += f" ({p1_lname})"
            elif p1_lname:
                p1_text = p1_lname
            else:
                p1_text = p1f or "P1"

            if p2_pname and p2_pname not in ("Player 2",):
                p2_text = f"{p2_pname}"
                if p2_lname:
                    p2_text += f" ({p2_lname})"
            elif p2_lname:
                p2_text = p2_lname
            else:
                p2_text = p2f or "P2"

            # Gems
            p1_gems = self._gems(state.gems.get(P1, 2))
            p2_gems = self._gems(state.gems.get(P2, 2))

            p1_label = f" {p1e[0]}{p1e[1]} [{p1_style}]{p1_text}[/{p1_style}] {p1_gems}"
            p2_label = f"{p2_gems} [{p2_style}]{p2_text}[/{p2_style}] {p2e[0]}{p2e[1]} "

            row2.add_row(
                Text.from_markup(p1_label),
                Text.from_markup(round_label),
                Text.from_markup(p2_label),
            )

        from rich.console import Group
        return Panel(Group(row1, row2), style="bold")
