"""Footer widget: event log — auto-scrolls to show newest events."""

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

# Event color mapping by leading emoji/keyword
_EVENT_COLORS = {
    "\U0001f3ad": "bright_cyan",     # 🎭 Stage change, decoy
    "\u274c":     "bright_red",      # ❌ Error
    "\U0001f518": "bright_yellow",   # 🔘 Choices
    "\U0001f4e2": "bright_magenta",  # 📢 Announcement
    "\U0001f451": "bright_yellow",   # 👑 Leader
    "\U0001f0cf": "dodger_blue2",    # 🃏 Deal to hand
    "\u2694":     "orange1",         # ⚔ Card played (close feel)
    "\U0001f4e3": "orchid",          # 📣 Muster
    "\U0001f575": "turquoise2",      # 🕵 Spy draw
    "\U0001f48a": "green3",          # 💊 Medic
    "\U0001f525": "bright_red",      # 🔥 Destroyed/scorch
    "\u2601":     "grey70",          # ☁ Weather on
    "\u2600":     "bright_yellow",   # ☀ Weather cleared
    "\U0001f4ef": "gold1",           # 📯 Commander horn
    "\U0001f3c1": "bright_white",    # 🏁 Round clear
    "\u2714":     "green1",          # ✔ Choice made
    "\U0001f4f1": "bright_cyan",     # 📱 Card scan
}


def _colorize(event: str) -> Text:
    """Apply color based on the event's leading emoji."""
    for emoji, color in _EVENT_COLORS.items():
        if event.startswith(emoji):
            return Text.from_markup(f"[{color}]{event}[/{color}]")
    return Text.from_markup(f"[dim]{event}[/dim]")


class FooterWidget(Static):

    def render(self):
        state = self.app.state

        # Calculate how many lines fit (widget height minus panel border)
        available = max(1, self.size.height - 2)

        if state.event_log:
            recent = list(state.event_log)[-available:]
            parts = [_colorize(e) for e in recent]
        else:
            parts = [Text.from_markup("[dim]Waiting for events...[/dim]")]

        return Panel(Group(*parts), title="Events", style="dim")
