"""Footer widget: event log, prompts, connection status."""

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji
import gwent_tui.snapshot as snapshot_mod

_CONN_ICON = {
    "off":        ("\u26aa", "grey50"),    # white circle
    "polling":    ("\u2705", "green"),      # check mark
    "processing": ("\u23f3", "yellow"),     # hourglass
    "error":      ("\u274c", "red"),        # red X
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
        parts.append(
            f"{mqtt_icon} [{mqtt_c}]MQTT {state.mqtt_status}[/{mqtt_c}]  "
            f"{http_icon} [{http_c}]HTTP {state.http_status}[/{http_c}]  "
            f"\U0001f504 [dim]poll {poll_label}[/dim]"
        )

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
            recent = [e for e in state.event_log if "\U0001f4e2" not in e][-3:]
            for e in recent:
                parts.append(f"[dim]{e}[/dim]")

        if not parts:
            parts.append("[dim]Waiting for events...[/dim]")

        content = "\n".join(parts)
        return Panel(Text.from_markup(content), title="Events", style="dim")
