"""TUI stage: Wizard — the full-screen New Game screen (client-side proposal).

The matchup proposal lives entirely client-side: this stage builds two random
image decks locally (random faction → random image leader → 20 random image
units, via gwent.game.decks), picks a random AI model for P2, and renders the
matchup. Nothing touches the server until START, which publishes both decks
(gwent/game/start) for the server to deal.

Buttons:
  [ Re-select Sides ]  → regenerate both decks
  [ Re-select Model ]  → re-pick P2's AI model
  [ START ]            → publish_game_start(p1, p2)

A Witcher-style matchup line is spoken (announcer voice) on first show and
after each re-select.
"""
from __future__ import annotations

import json
import logging
import os
import random

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static
from textual_image.widget import TGPImage

import gwent.game.decks as gdecks
from gwent_tui import matchup_announcer, tts
from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import faction_emoji, FACTION_COLOR
from gwent_tui.game_state import P1, P2

log = logging.getLogger("gwent_tui.stages.wizard")

_MODELS_PATH = os.path.join(os.path.dirname(gdecks.CARDS_DIR), "llm-models.json")

# Big block-art "VS" — looks larger than a glyph without scaling the font.
_VS_ART = "\n".join([
    "█   █ ████",
    "█   █ █   ",
    "█   █ ████",
    " █ █     █",
    "  █   ████",
])


def _llm_models():
    try:
        data = json.load(open(_MODELS_PATH))
        return [m for m in data.get("models", []) if m.get("kind") == "llm"]
    except Exception as e:
        log.error("failed to load llm-models.json: %s", e)
        return []


def _proposal(app) -> dict:
    return getattr(app, "_wizard_proposal", None) or {}


def _controller_info(app, side: str) -> tuple[str, str]:
    """(controller_id, display_label) for a side, read from the retained
    `gwent/players/controller/PLAYER.*` topic via app state — the single
    source of truth for who drives each side."""
    state = getattr(app, "state", None)
    player = P1 if side == "p1" else P2
    controller = "human"
    label = ""
    if state is not None:
        controller = state.controllers.get(player, "human") or "human"
        # controller_labels is owned by the controller topic alone — unlike
        # player_names it can't be stomped back to "Player N" by snapshots.
        label = (getattr(state, "controller_labels", {}) or {}).get(player, "")
    if controller == "human":
        return "human", "Human (RFID / touch)"
    return controller, label or controller


class _SideInfo(Static):
    """Faction · player/controller · leader · approx power for one side.

    The controller line renders live from the retained controller topic, so
    picks made via the assign modal (tap a player half) show up immediately
    and survive START."""

    def __init__(self, side: str, **kwargs):
        super().__init__("", **kwargs)
        self.side = side  # "p1" or "p2"

    def render(self):
        s = _proposal(self.app).get(self.side) or {}
        faction = s.get("faction", "")
        color = FACTION_COLOR.get(faction, "white")
        e0, e1 = faction_emoji(faction)
        controller, ctrl_label = _controller_info(self.app, self.side)
        leader = s.get("leader") or "—"
        strength = s.get("strength")
        icon = "🃏" if controller == "human" else "🤖"
        # The controller name IS the player identity — no redundant
        # "Player 1"/"Player 2" header line.
        lines = [
            f"{icon} [bold]{ctrl_label}[/]",
            f"{e0}{e1}  [{color}]{faction or '—'}[/]",
            f"👑 {leader}",
        ]
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
        with Container(classes="wiz-img-wrap"):
            self._img = TGPImage("", classes="wiz-img")
            yield self._img
        yield _SideInfo(self.side, classes="wiz-info")

    def update_image(self) -> None:
        card = (_proposal(self.app).get(self.side) or {}).get("leader_card")
        path = resolve_card_image(card) if card else None
        if self._img is not None:
            self._img.image = path or ""


class WizardStage(Container):
    """Full-screen New Game wizard (client-side proposal)."""

    DEFAULT_CSS = """
    WizardStage { height: 1fr; layout: vertical; }
    #wiz-main { height: 1fr; layout: horizontal; }
    _Side { width: 1fr; height: 1fr; align: center top; }
    .wiz-img-wrap { width: 100%; height: 1fr; align: center middle; }
    .wiz-img { width: auto; height: 100%; }
    .wiz-info { width: 100%; height: auto; content-align: center middle; text-align: center; }
    #wiz-vs { width: 11; height: 1fr; content-align: center middle; text-style: bold; color: $accent; }
    #wiz-footer { dock: bottom; width: 100%; height: 3; align: center middle; }
    #wiz-buttons { width: 100%; height: 3; align: center middle; }
    #wiz-buttons Button { height: 3; min-width: 22; margin: 0 1; }
    #wiz-reroll-sides, #wiz-reroll-model {
        background: #9370db; color: black; text-style: bold;
    }
    #wiz-reroll-sides:hover, #wiz-reroll-model:hover { background: #a98ee0; color: black; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._p1: _Side | None = None
        self._p2: _Side | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="wiz-main"):
            self._p1 = _Side("p1", id="wiz-p1")
            yield self._p1
            yield Static(f"[bold yellow]{_VS_ART}[/]", id="wiz-vs")
            self._p2 = _Side("p2", id="wiz-p2")
            yield self._p2
        with Vertical(id="wiz-footer"):
            with Horizontal(id="wiz-buttons"):
                yield Button("🎲 Re-select Sides", id="wiz-reroll-sides")
                yield Button("🤖 Re-select Model", id="wiz-reroll-model")
                yield Button("▶ START", id="wiz-start", variant="success")

    def on_mount(self) -> None:
        log.info("WizardStage mounted")
        if not _proposal(self.app):
            self._generate(sides=True, model=True)
        else:
            self._refresh_sides()

    # --- proposal generation (client-side) ---

    def _generate(self, sides=True, model=True, announce=True) -> None:
        prop = dict(_proposal(self.app))
        if sides:
            matchup = gdecks.pick_random_matchup_sides(deck_size=20)
            if not matchup:
                log.error("wizard: no matchup available")
                return
            s1, s2 = matchup
            prop["p1"] = s1
            prop["p2"] = s2
        if model:
            self._roll_model()
        self.app._wizard_proposal = prop
        self._refresh_sides()
        if announce:
            self._announce(prop)

    def _roll_model(self) -> None:
        """Pick a random LLM for P2 and publish it via the assign-p2 menu.

        The server assigns it and republishes the retained controller topic
        (`gwent/players/controller/PLAYER.TWO`), which is what this screen —
        and everything else — renders controller info from. Controller state
        never lives in the local proposal."""
        models = _llm_models()
        subscriber = getattr(self.app, "_subscriber", None)
        if not models:
            log.error("wizard: no llm models available — P2 stays as-is")
            return
        if subscriber is None:
            log.error("wizard: no _subscriber — cannot publish P2 model roll")
            return
        m = random.choice(models)
        log.info("wizard rolled P2 model %s — publishing assign-p2 choose",
                 m.get("id"))
        subscriber.publish_choose("assign-p2", m.get("id"))

    def _announce(self, prop: dict) -> None:
        p1f = (prop.get("p1") or {}).get("faction")
        p2f = (prop.get("p2") or {}).get("faction")
        if not p1f or not p2f:
            return
        try:
            line = matchup_announcer.announce_matchup(p1f, p2f)
            log.info("matchup announcement: %s", line)
            tts.clear_pending()
            tts.speak(line, faction=None)
        except Exception as e:
            log.error("announce failed: %s", e, exc_info=True)

    def _refresh_sides(self) -> None:
        for side in (self._p1, self._p2):
            if side:
                side.update_image()
                try:
                    side.query_one(_SideInfo).refresh()
                except Exception:
                    pass

    # --- buttons ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "wiz-reroll-sides":
            self._generate(sides=True, model=False)
        elif bid == "wiz-reroll-model":
            self._generate(sides=False, model=True)
        elif bid == "wiz-start":
            self._start()
        event.stop()

    def _start(self) -> None:
        prop = _proposal(self.app)
        p1, p2 = prop.get("p1"), prop.get("p2")
        if not p1 or not p2 or not p1.get("deck") or not p2.get("deck"):
            log.error("wizard START with incomplete proposal: %s", prop)
            return
        subscriber = getattr(self.app, "_subscriber", None)
        if subscriber is None:
            log.error("no _subscriber — cannot start game")
            return
        # Controllers are NOT sent — they're already assigned (retained
        # gwent/players/controller/PLAYER.*) via the assign-pN menus, so
        # picks made on this screen stay in effect after START.
        c1, _ = _controller_info(self.app, "p1")
        c2, _ = _controller_info(self.app, "p2")
        log.info("WizardStage START: P1=%s (ctrl=%s) P2=%s (ctrl=%s)",
                 p1.get("faction"), c1, p2.get("faction"), c2)
        subscriber.publish_game_start(
            {"deck": p1["deck"]},
            {"deck": p2["deck"]},
        )
