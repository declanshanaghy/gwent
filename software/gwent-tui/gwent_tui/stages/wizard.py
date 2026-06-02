"""TUI stage: Wizard — the full-screen new-game setup screen.

Replaces the old "choose a game" list. The server (MenuPublisher) rolls a
random 1-player matchup (P1 human + P2 AI model) and publishes it as the
retained `gwent/menu/present/wizard` message, which the TUI caches in
`state.menus['wizard']`. This stage renders that summary plus three buttons:

    [ Re-select Sides ]  [ Re-select Model ]  [ START ]

Re-roll buttons publish `wizard:reroll-sides` / `wizard:reroll-model`; START
publishes `wizard:start`, which kicks off the game server-side.

Profuse logging per feedback_profuse_logging. Touch targets are large buttons
for the Pi 7" display (see project_pi_display / feedback_touch_targets).
"""
from __future__ import annotations

import logging

from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static

from gwent_tui.emoji import faction_emoji, FACTION_COLOR

log = logging.getLogger("gwent_tui.stages.wizard")

WIZARD_MENU = "wizard"


def _faction_markup(faction: str) -> str:
    """Faction name with its emoji pair + faction color, as Rich markup."""
    if not faction:
        return "[dim]—[/dim]"
    e0, e1 = faction_emoji(faction)
    color = FACTION_COLOR.get(faction, "white")
    return f"[{color}]{e0}{e1}  {faction}[/]"


class _WizardSummary(Static):
    """Live summary of the pending matchup — re-renders each refresh tick."""

    def render(self):
        state = getattr(self.app, "state", None)
        menu = (state.menus.get(WIZARD_MENU) if state else None) or {}
        summary = menu.get("summary") or {}

        if summary.get("error"):
            body = Text.from_markup(
                f"\n[bold red]{summary['error']}[/bold red]\n\n"
                "[dim]Chip cards for 2+ factions, then return here.[/dim]\n")
            return Panel(Align.center(body), title="⚠  Cannot start",
                         border_style="red", padding=(1, 2))

        p1 = summary.get("p1") or {}
        p2 = summary.get("p2") or {}

        p1_faction = _faction_markup(p1.get("faction", ""))
        p2_faction = _faction_markup(p2.get("faction", ""))
        p1_owner = p1.get("owner", "")
        p2_ctrl = p2.get("controller_label", "—")
        p2_icon = p2.get("icon", "🤖")

        lines = [
            f"[bold]Player 1[/bold] [dim](you · RFID / touch)[/dim]   {p1_faction}"
            + (f"  [dim]{p1_owner}[/dim]" if p1_owner else ""),
            "[bold yellow]              ⚔  VS  ⚔[/bold yellow]",
            f"[bold]Player 2[/bold] [dim](AI opponent)[/dim]   {p2_faction}"
            f"   {p2_icon} [bold]{p2_ctrl}[/bold]",
        ]
        text = Text.from_markup("\n".join(lines))
        return Panel(text, title="🎲  New Game", border_style="bright_cyan",
                     padding=(1, 3))


class WizardStage(Container):
    """Full-screen new-game wizard."""

    DEFAULT_CSS = """
    WizardStage {
        height: 1fr;
        layout: vertical;
    }
    #wizard-summary {
        width: 100%;
        height: 1fr;
        content-align: center middle;
        padding: 0 2;
    }
    /* Footer is docked to the bottom so the buttons are ALWAYS visible,
       no matter how tall the summary panel gets. (Pi 7" = ~22 stage rows.) */
    #wizard-footer {
        dock: bottom;
        width: 100%;
        height: 5;
        align: center middle;
    }
    #wizard-buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }
    #wizard-buttons Button {
        height: 3;
        min-width: 22;
        margin: 0 1;
    }
    #wizard-hint {
        width: 100%;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield _WizardSummary(id="wizard-summary")
        with Vertical(id="wizard-footer"):
            with Horizontal(id="wizard-buttons"):
                yield Button("🎲 Re-select Sides", id="wiz-reroll-sides")
                yield Button("🤖 Re-select Model", id="wiz-reroll-model")
                yield Button("▶ START", id="wiz-start", variant="success")
            yield Static("Tap a button to set up your game",
                         id="wizard-hint")

    def on_mount(self) -> None:
        log.info("WizardStage mounted")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "wiz-reroll-sides": "reroll-sides",
            "wiz-reroll-model": "reroll-model",
            "wiz-start": "start",
        }
        choice = mapping.get(event.button.id or "")
        if choice is None:
            return
        log.info("WizardStage button -> wizard:%s", choice)
        subscriber = getattr(self.app, "_subscriber", None)
        if subscriber is None:
            log.error("no _subscriber on app — cannot publish wizard choice")
            return
        subscriber.publish_choose(WIZARD_MENU, choice)
        event.stop()
