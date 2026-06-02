"""TUI stage: Wizard — the full-screen new-game setup screen.

Replaces the old "choose a game" list. The server (MenuPublisher) rolls a
random 1-player matchup (P1 human + P2 AI) and publishes it as the retained
`gwent/menu/present/wizard` message (cached in `state.menus['wizard']`). For
each side the summary carries faction, owner, leader, the leader card (for its
image) and the deck's summed strength.

This stage renders a two-sided matchup card — leader image, faction, player,
leader name and approx strength per side — with three buttons:

    [ Re-select Sides ]  [ Re-select Model ]  [ START ]

Re-roll buttons publish `wizard:reroll-sides` / `wizard:reroll-model`; START
publishes `wizard:start`.
"""
from __future__ import annotations

import logging

from rich.align import Align
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static
from textual_image.widget import TGPImage

from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import faction_emoji, FACTION_COLOR

log = logging.getLogger("gwent_tui.stages.wizard")

WIZARD_MENU = "wizard"


def _summary(app) -> dict:
    state = getattr(app, "state", None)
    menu = (state.menus.get(WIZARD_MENU) if state else None) or {}
    return menu.get("summary") or {}


class _SideInfo(Static):
    """Text block for one side: player · faction · leader · strength."""

    def __init__(self, side: str, **kwargs):
        super().__init__("", **kwargs)
        self.side = side  # "p1" or "p2"

    def render(self):
        s = _summary(self.app).get(self.side) or {}
        faction = s.get("faction", "")
        color = FACTION_COLOR.get(faction, "white")
        e0, e1 = faction_emoji(faction)
        is_p1 = self.side == "p1"
        who = "you · RFID / touch" if is_p1 else "AI opponent"
        player = "Player 1" if is_p1 else "Player 2"
        ctrl = s.get("controller_label", "") if not is_p1 else ""
        leader = s.get("leader") or "—"
        strength = s.get("strength")
        lines = [
            f"[bold]{player}[/] [dim]({who})[/]",
            f"{e0}{e1}  [{color}]{faction or '—'}[/]",
        ]
        if ctrl:
            lines.append(f"🤖 [bold]{ctrl}[/]")
        lines.append(f"👑 {leader}")
        if strength is not None:
            lines.append(f"⚔ [bold yellow]≈ {strength}[/] power")
        return Text.from_markup("\n".join(lines), justify="center")


class _Side(Vertical):
    """One side of the matchup: leader image above, info below."""

    def __init__(self, side: str, **kwargs):
        super().__init__(**kwargs)
        self.side = side
        self._img: TGPImage | None = None

    def compose(self) -> ComposeResult:
        self._img = TGPImage("", classes="wiz-img")
        yield self._img
        yield _SideInfo(self.side, classes="wiz-info")

    def update_image(self) -> None:
        s = _summary(self.app).get(self.side) or {}
        card = s.get("leader_card")
        path = resolve_card_image(card) if card else None
        if self._img is not None:
            self._img.image = path or ""


class WizardStage(Container):
    """Full-screen new-game wizard."""

    DEFAULT_CSS = """
    WizardStage {
        height: 1fr;
        layout: vertical;
    }
    #wiz-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #wiz-main {
        height: 1fr;
        layout: horizontal;
    }
    _Side {
        width: 1fr;
        height: 1fr;
        align: center top;
    }
    .wiz-img {
        width: auto;
        height: 1fr;
    }
    .wiz-info {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
    }
    #wiz-vs {
        width: 11;
        height: 1fr;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    /* Buttons docked bottom so they're always visible. */
    #wiz-footer {
        dock: bottom;
        width: 100%;
        height: 4;
        align: center middle;
    }
    #wiz-buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }
    #wiz-buttons Button {
        height: 3;
        min-width: 22;
        margin: 0 1;
    }
    #wiz-hint {
        width: 100%;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    #wiz-error {
        height: 1fr;
        content-align: center middle;
        color: $error;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._p1: _Side | None = None
        self._p2: _Side | None = None
        self._last_cid = None

    def compose(self) -> ComposeResult:
        yield Static("🎲  New Game", id="wiz-title")
        with Horizontal(id="wiz-main"):
            self._p1 = _Side("p1", id="wiz-p1")
            yield self._p1
            yield Static("⚔\nVS\n⚔", id="wiz-vs")
            self._p2 = _Side("p2", id="wiz-p2")
            yield self._p2
        with Vertical(id="wiz-footer"):
            with Horizontal(id="wiz-buttons"):
                yield Button("🎲 Re-select Sides", id="wiz-reroll-sides")
                yield Button("🤖 Re-select Model", id="wiz-reroll-model")
                yield Button("▶ START", id="wiz-start", variant="success")
            yield Static("Tap a button to set up your game", id="wiz-hint")

    def on_mount(self) -> None:
        log.info("WizardStage mounted")
        self._sync()
        # Leader images aren't auto-refreshed like Static text, so poll the
        # cached wizard payload and swap them when the matchup changes.
        self.set_interval(0.5, self._sync)

    def _sync(self) -> None:
        cid = (self.app.state.menus.get(WIZARD_MENU) or {}).get("content_id")
        if cid == self._last_cid:
            return
        self._last_cid = cid
        try:
            if self._p1:
                self._p1.update_image()
            if self._p2:
                self._p2.update_image()
        except Exception as e:
            log.error("wizard image sync failed: %s", e, exc_info=True)

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
