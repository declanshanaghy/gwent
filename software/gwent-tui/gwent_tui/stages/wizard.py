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


class _SideInfo(Static):
    """Faction · player/controller · leader · approx power for one side."""

    def __init__(self, side: str, **kwargs):
        super().__init__("", **kwargs)
        self.side = side  # "p1" or "p2"

    def render(self):
        s = _proposal(self.app).get(self.side) or {}
        faction = s.get("faction", "")
        color = FACTION_COLOR.get(faction, "white")
        e0, e1 = faction_emoji(faction)
        is_p1 = self.side == "p1"
        who = "you · RFID / touch" if is_p1 else "AI opponent"
        player = "Player 1" if is_p1 else "Player 2"
        leader = s.get("leader") or "—"
        strength = s.get("strength")
        lines = [
            f"[bold]{player}[/] [dim]({who})[/]",
            f"{e0}{e1}  [{color}]{faction or '—'}[/]",
        ]
        if not is_p1:
            lines.append(f"🤖 [bold]{s.get('controller_label', '—')}[/]")
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
            s1["controller"] = "human"
            s1["controller_label"] = "You (RFID / touch)"
            prop["p1"] = s1
            # keep existing p2 model across a sides re-roll
            prev_model = (prop.get("p2") or {}).get("controller")
            prev_label = (prop.get("p2") or {}).get("controller_label")
            s2["controller"] = prev_model or "human"
            s2["controller_label"] = prev_label or "Human"
            prop["p2"] = s2
        if model or not (prop.get("p2") or {}).get("controller") or \
                (prop["p2"]["controller"] == "human"):
            self._assign_random_model(prop)
        self.app._wizard_proposal = prop
        self._refresh_sides()
        if announce:
            self._announce(prop)

    def _assign_random_model(self, prop: dict) -> None:
        models = _llm_models()
        p2 = prop.setdefault("p2", {})
        if not models:
            p2["controller"] = "human"
            p2["controller_label"] = "Human"
            return
        m = random.choice(models)
        p2["controller"] = m.get("id")
        p2["controller_label"] = m.get("label", m.get("id"))

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
        log.info("WizardStage START: P1=%s/%s P2=%s/%s",
                 p1.get("faction"), p1.get("controller"),
                 p2.get("faction"), p2.get("controller"))
        subscriber.publish_game_start(
            {"controller": p1.get("controller", "human"), "deck": p1["deck"]},
            {"controller": p2.get("controller", "human"), "deck": p2["deck"]},
        )
