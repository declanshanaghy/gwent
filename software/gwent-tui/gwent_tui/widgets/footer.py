"""Footer widget: event log, prompts, connection status."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji
import gwent_tui.snapshot as snapshot_mod
from gwent_tui import tts as tts_mod

_CONN_ICON = {
    "off":        ("\u26aa", "grey50"),    # white circle
    "alive":      ("\u2705", "green"),      # check mark
    "polling":    ("\u2705", "green"),      # check mark (actively polling)
    "processing": ("\u23f3", "yellow"),     # hourglass
    "error":      ("\u274c", "red"),        # red X
}

# Per-provider display colors
_TTS_COLOR = {
    "say":        "bright_cyan",
    "piper":      "bright_magenta",
    "gtts":       "bright_yellow",
    "elevenlabs": "orange1",
    "openai":     "bright_blue",
    "off":        "red",
    "?":          "grey50",
    "auto":       "grey50",
}


class FooterWidget(Static):

    def render(self):
        state = self.app.state
        parts = []

        # Connection status line
        mqtt_icon, mqtt_c = _CONN_ICON.get(state.mqtt_status, ("\u2753", "grey50"))
        http_icon, http_c = _CONN_ICON.get(state.http_status, ("\u2753", "grey50"))
        pt = snapshot_mod.POLL_TIMEOUT
        poll_label = f"{pt}s" if pt > 0 else "off"
        # TTS provider labels
        server_tts = state.server_tts or "?"
        provider = tts_mod._get_provider()
        client_tts = tts_mod._provider_name or "auto"
        if provider and provider is not False:
            client_tts = tts_mod._provider_name or type(provider).__name__.replace("Provider", "").lower()
        elif provider is False:
            client_tts = "off"
        s_color = _TTS_COLOR.get(server_tts, "grey50")
        c_color = _TTS_COLOR.get(client_tts, "grey50")
        status_left = (
            f"{mqtt_icon} [{mqtt_c}]MQTT {state.mqtt_status}[/{mqtt_c}]  "
            f"{http_icon} [{http_c}]HTTP {state.http_status}[/{http_c}]  "
            f"\U0001f50a [green]server:[/green][{s_color}]{server_tts}[/{s_color}] "
            f"[green]client:[/green][{c_color}]{client_tts}[/{c_color}]"
        )
        status_right = f"\U0001f504 [dim]poll {poll_label}[/dim]"
        tbl = Table.grid(expand=True)
        tbl.add_column(ratio=1)
        tbl.add_column(justify="right")
        tbl.add_row(Text.from_markup(status_left), Text.from_markup(status_right))
        parts.append(tbl)

        if state.last_prompt:
            parts.append(f"\U0001f4df {state.last_prompt}")
        if state.last_card_read:
            name = state.last_card_read.get("name", "???")
            faction = state.last_card_read.get("faction", "")
            fe = faction_emoji(faction)
            parts.append(f"\U0001f4f1 Scanned: {fe[0]}{fe[1]} {name}")
        if state.last_error:
            parts.append(f"\u274c {state.last_error}")

        if state.event_log:
            recent = [e for e in state.event_log if "\U0001f4e2" not in e][-6:]
            for e in recent:
                parts.append(f"[dim]{e}[/dim]")

        if not parts:
            parts.append("[dim]Waiting for events...[/dim]")

        from rich.console import Group
        renderables = []
        for p in parts:
            if isinstance(p, str):
                renderables.append(Text.from_markup(p))
            else:
                renderables.append(p)
        return Panel(Group(*renderables), title="Events", style="dim")
