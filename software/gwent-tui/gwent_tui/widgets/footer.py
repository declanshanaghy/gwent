"""Footer widget: event log, prompts, announcements."""

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from gwent_tui.emoji import faction_emoji


class FooterWidget(Static):

    def render(self):
        state = self.app.state
        parts = []

        if state.last_prompt:
            parts.append(f"\U0001f4df {state.last_prompt}")
        if state.last_announcement and state.last_announcement != state.last_prompt:
            parts.append(f"\U0001f4e2 {state.last_announcement}")
        if state.last_card_read:
            name = state.last_card_read.get("name", "???")
            faction = state.last_card_read.get("faction", "")
            fe = faction_emoji(faction)
            parts.append(f"\U0001f4f1 Scanned: {fe[0]}{fe[1]} {name}")
        if state.last_error:
            parts.append(f"\u274c {state.last_error}")

        if state.event_log:
            recent = list(state.event_log)[-3:]
            for e in recent:
                parts.append(f"[dim]{e}[/dim]")

        if not parts:
            parts.append("[dim]Waiting for events...[/dim]")

        content = "\n".join(parts)
        return Panel(Text.from_markup(content), title="Events", style="dim")
