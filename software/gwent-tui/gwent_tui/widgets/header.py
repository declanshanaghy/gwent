"""Header widget: factions, round, active player highlight, hamburger menu.

The whole widget is tappable (and also a keyboard target via `m`) — clicking
anywhere on it opens the in-game hamburger modal (Reset / Volume / Help).
A ☰ glyph in the top-right hints at the affordance.
"""

import logging

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji, FACTION_STYLE
from gwent_tui.game_state import P1, P2
from gwent_tui import tts as tts_mod

log = logging.getLogger("gwent_tui.header")

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
        game_id = f" [dim]\u2022 {state.game_id}[/dim]" if state.game_id else ""
        stage_label = f" {stage_icon} [dim]{state.stage}[/dim]{game_id}"

        mqtt_icon, mqtt_c = _CONN_ICON.get(state.mqtt_status, ("\u2753", "grey50"))
        srv_icon, srv_c = (("\u2705", "green") if state.server_online
                           else ("\u274c", "red"))
        server_tts = state.server_tts or "?"
        provider = tts_mod._get_provider()
        client_tts = tts_mod._provider_name or "auto"
        if provider and provider is not False:
            client_tts = tts_mod._provider_name or type(provider).__name__.replace("Provider", "").lower()
        elif provider is False:
            client_tts = "off"
        s_color = _TTS_COLOR.get(server_tts, "grey50")
        c_color = _TTS_COLOR.get(client_tts, "grey50")
        status_str = (
            f"{mqtt_icon} [{mqtt_c}]MQTT[/{mqtt_c}] "
            f"{srv_icon} [{srv_c}]SRV[/{srv_c}] "
            f"\U0001f50a [{s_color}]s:{server_tts}[/{s_color}] [{c_color}]c:{client_tts}[/{c_color}]"
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

        if not state.server_online or state.stage == "Offline":
            row2.add_row(
                Text.from_markup(" \u26a0 [bold red]Server Offline[/bold red]"),
                Text(""),
                Text(""),
            )
        else:
            # \u2630 hamburger sits to the left of the round label \u2014 taps anywhere
            # on the header open the in-game menu, but the icon now lives in
            # the central column so it visually anchors with "Round N".
            round_label = (
                f"[bold $accent on grey15] \u2630 [/]  "
                f"\u2694 Round {state.round_number} \u2694"
            )

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

            # Controller short-name helper — "anthropic/claude-sonnet-4-6"
            # → "Sonnet 4.6", "human" → "Human", etc.
            def _controller_short(cid: str) -> str:
                if not cid or cid == "human":
                    return "Human"
                tail = cid.split("/", 1)[-1]
                if "claude-" in tail:
                    return tail.replace("claude-", "").replace("-", " ").title()
                if "gemini" in tail:
                    return "Gemini " + tail.split("/")[-1].replace("gemini-", "")
                if tail.startswith("gpt-"):
                    return tail.replace("gpt-", "GPT-")
                return tail

            # ALWAYS prefix with "P1"/"P2" so users can tell sides apart even
            # when both names are model-driven. Build a slash-separated label:
            #   P1 · Sonnet 4.6 (Eredin)
            #   P2 · Human (Foltest)
            def _player_text(side_label: str, pname: str, lname: str,
                             faction: str, controller_id: str) -> str:
                controller = _controller_short(controller_id)
                # When controller is human and we have a per-game name (other
                # than the default placeholder), prefer that.
                if pname and pname not in ("Player 1", "Player 2"):
                    controller = pname
                # Append leader name in parens when we have it.
                if lname:
                    return f"{side_label} · {controller} ({lname})"
                if faction:
                    return f"{side_label} · {controller} ({faction})"
                return f"{side_label} · {controller}"

            p1_text = _player_text("P1", p1_pname, p1_lname, p1f,
                                   state.controllers.get(P1, "human"))
            p2_text = _player_text("P2", p2_pname, p2_lname, p2f,
                                   state.controllers.get(P2, "human"))

            # Gems
            p1_gems = self._gems(state.gems.get(P1, 2))
            p2_gems = self._gems(state.gems.get(P2, 2))

            p1_label = (f" {p1_gems} {p1e[0]}{p1e[1]} "
                        f"[{p1_style}]{p1_text}[/{p1_style}]")
            p2_label = (f"[{p2_style}]{p2_text}[/{p2_style}] "
                        f"{p2e[0]}{p2e[1]} {p2_gems} ")

            row2.add_row(
                Text.from_markup(p1_label),
                Text.from_markup(round_label),
                Text.from_markup(p2_label),
            )

        from rich.console import Group
        return Panel(Group(row1, row2), style="bold")

    # --- Touch / click ------------------------------------------------------
    # ALL header taps open the in-game hamburger menu (left-anchored).
    # Player assignment is reachable as a hamburger menu item — never via a
    # right-side tap zone. See memory: feedback_left_anchored_menus.
    def on_click(self, event: events.Click) -> None:
        log.info(
            "HeaderWidget CLICK widget=(%d,%d) size=(%d,%d) — opening hamburger",
            event.x, event.y, self.size.width, self.size.height,
        )
        try:
            from gwent_tui.in_game_menu_modal import InGameMenuModal
            self.app.push_screen(InGameMenuModal())
        except Exception as e:
            log.error("on_click handler failed: %s", e, exc_info=True)
