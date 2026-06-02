"""Card-list overlay — inspect (and optionally play) a list of cards.

Reused via the `action` arg:
  - HAND (action="play"): [Cancel] + [Play <NAME>]. Gated to the player whose
    turn it is (the server plays a scanned card as the *current* player, so
    playing out of turn would misattribute it). Playing an AI-controlled side
    on its turn is a human override — the server advances the turn and the AI's
    in-flight move self-aborts via its fresh-state check.
  - DECK (action="draw"): [Cancel] + [Draw <NAME> from Deck], same turn gating
    — for when a card must be pulled from the deck (spy, leader draw, etc.).
  - BOARD section (action=None): view-only, [Cancel] only.
Both "play" and "draw" reach the server as a scan on gwent/cards/raw/read.

Layout (sized for the Pi 7" display, project_pi_display):
  - LEFT : scrollable list, two rows per card (touch-friendly, scrollbar).
  - RIGHT: the card image as an aspect-preserved background with the stats /
    abilities overlaid in a semi-transparent panel on top.
  - BOTTOM: docked buttons (always visible).

Dismiss via Cancel, Esc/q, or tapping the backdrop. Profuse logging per
feedback_profuse_logging; rows are height 2 per feedback_touch_targets.
"""
from __future__ import annotations

import logging

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich import box as rich_box
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static
from textual_image.widget import TGPImage

from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import card_display, FACTION_STYLE
from gwent_tui.game_state import P1, P2

log = logging.getLogger("gwent_tui.card_list")

_RANGE_ICONS = {"close": "⚔ Close", "ranged": "🏹 Ranged", "siege": "🏰 Siege"}
_RANGE_ICON_ONLY = {"close": "⚔", "ranged": "🏹", "siege": "🏰"}


def _truncate(name: str, n: int = 22) -> str:
    return name if len(name) <= n else name[: n - 1] + "…"


def _row_label(card: dict) -> str:
    """Two-line label: name line + dim attributes line (touch-friendly)."""
    line1 = card_display(card, max_name=30)
    bits = []
    for r in card.get("ranges") or []:
        bits.append(_RANGE_ICON_ONLY.get(r, r))
    if card.get("specialty"):
        bits.append(card["specialty"])
    for a in card.get("abilities") or []:
        bits.append(a)
    line2 = f"  [dim]{' · '.join(bits)}[/dim]" if bits else ""
    return f"{line1}\n{line2}"


class _CardRow(ListItem):
    """A single tappable card row (two rows tall). Carries its card dict."""

    DEFAULT_CSS = """
    _CardRow { height: 2; padding: 0 1; }
    """

    def __init__(self, card: dict) -> None:
        super().__init__(Label(_row_label(card)))
        self.card = card


class _CardDetail(Static):
    """Stats + abilities, rendered to sit on top of the card image."""

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self._card: dict | None = None

    def set_card(self, card: dict | None) -> None:
        self._card = card
        self.refresh()

    def render(self):
        card = self._card
        if not card:
            return Text.from_markup("[dim]Select a card to see details.[/dim]")

        faction = card.get("faction", "")
        color = FACTION_STYLE.get(faction, ("white", "grey30", "white"))[0]
        name = card.get("name", "???")

        t = Table(box=rich_box.SIMPLE, show_header=False, padding=(0, 1),
                  expand=True)
        t.add_column("", style=f"bold {color}", width=10)
        t.add_column("")
        t.add_row("Faction", f"[{color}]{faction}[/]")
        if card.get("strength") is not None:
            t.add_row("Strength", f"[bold yellow]{card['strength']}[/]")
        if card.get("ranges"):
            r_text = " [dim]│[/] ".join(
                _RANGE_ICONS.get(r, r) for r in card["ranges"])
            t.add_row("Range", r_text)
        if card.get("specialty"):
            t.add_row("Specialty", f"[bold]{card['specialty']}[/]")
        if card.get("abilities"):
            abilities = card["abilities"]
            if isinstance(abilities, list) and abilities:
                a_text = " [dim]│[/] ".join(f"[bold]{a}[/]" for a in abilities)
                t.add_row("Abilities", a_text)
        if card.get("owner"):
            t.add_row("Owner", f"[dim]{card['owner']}[/]")

        title = Text.from_markup(f"[bold {color}]{name}[/]")
        parts = [title, t]
        if card.get("card_text"):
            parts.append(Text.from_markup(
                f"[italic bright_white]“{card['card_text']}”[/]"))
        return Group(*parts)


class CardListModal(ModalScreen):
    """Full-screen list+detail overlay for a set of cards."""

    DEFAULT_CSS = """
    CardListModal {
        align: center middle;
    }
    #cl-box {
        width: 96%;
        height: 92%;
        max-width: 110;
        max-height: 32;
        background: $panel;
        border: thick $accent;
        padding: 0 1;
    }
    #cl-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }
    #cl-main {
        height: 1fr;
        layout: horizontal;
    }
    #cl-list {
        width: 44;
        height: 1fr;
        border: round $primary;
        background: $surface;
        scrollbar-size-vertical: 2;
        scrollbar-color: $accent;
        scrollbar-background: $surface-darken-1;
    }
    /* Right pane: image is the background layer, stats overlay on top. */
    #cl-detail {
        width: 1fr;
        height: 1fr;
        layers: cardimg cardstats;
        align: center middle;
    }
    #cl-image {
        layer: cardimg;
        width: auto;
        height: 100%;
    }
    #cl-attrs {
        layer: cardstats;
        dock: bottom;
        width: 100%;
        height: auto;
        max-height: 100%;
        background: $panel 78%;
        padding: 0 2;
    }
    /* Buttons docked bottom so they're always visible (Pi 7" = short). */
    #cl-buttons {
        dock: bottom;
        width: 100%;
        height: 3;
        align: center middle;
    }
    #cl-buttons Button {
        height: 3;
        min-width: 16;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, title: str, cards: list, *, player_key: str | None = None,
                 action: str | None = None) -> None:
        super().__init__()
        self._title = title
        self._cards = list(cards or [])
        self.player_key = player_key
        # action: None = view-only (Cancel only); "play" = hand; "draw" = deck.
        self.action = action
        self._list: ListView | None = None
        self._detail: _CardDetail | None = None
        self._image: TGPImage | None = None
        self._play_btn: Button | None = None
        self._selected: dict | None = None
        log.info("CardListModal __init__ title=%r cards=%d action=%s player=%s",
                 title, len(self._cards), action, player_key)

    def _action_label(self, name: str) -> str:
        if self.action == "draw":
            return f"📦 Draw {name} from Deck"
        return f"▶ Play {name}"

    def compose(self) -> ComposeResult:
        with Container(id="cl-box"):
            yield Static(self._title, id="cl-title")
            with Horizontal(id="cl-main"):
                self._list = ListView(
                    *[_CardRow(c) for c in self._cards], id="cl-list")
                yield self._list
                with Container(id="cl-detail"):
                    self._image = TGPImage("", id="cl-image")
                    yield self._image
                    self._detail = _CardDetail(id="cl-attrs")
                    yield self._detail
            with Horizontal(id="cl-buttons"):
                yield Button("✕ Cancel", id="cl-cancel", variant="error")
                if self.action:
                    self._play_btn = Button("", id="cl-action",
                                            variant="success")
                    self._play_btn.display = False
                    yield self._play_btn

    def on_mount(self) -> None:
        if self._list and self._list.children:
            self._list.focus()
            self._list.index = 0
            first = self._list.children[0]
            if isinstance(first, _CardRow):
                self._select_card(first.card)
        elif self._detail:
            self._detail.set_card(None)

    # --- selection ---

    def _is_turn(self) -> bool:
        state = getattr(self.app, "state", None)
        return bool(state and getattr(state, "current_player", None)
                    == self.player_key)

    def _player_name(self) -> str:
        state = getattr(self.app, "state", None)
        names = getattr(state, "player_names", {}) if state else {}
        default = "Player 1" if self.player_key == P1 else "Player 2"
        return names.get(self.player_key, default)

    def _select_card(self, card: dict | None) -> None:
        self._selected = card
        if self._detail:
            self._detail.set_card(card)
        if self._image is not None:
            path = resolve_card_image(card) if card else None
            self._image.image = path or ""
        if self._play_btn is not None:
            if not card:
                self._play_btn.display = False
            elif self._is_turn():
                self._play_btn.display = True
                self._play_btn.disabled = False
                self._play_btn.label = self._action_label(
                    _truncate(card.get("name", "")))
            else:
                self._play_btn.display = True
                self._play_btn.disabled = True
                self._play_btn.label = f"⌛ Not {self._player_name()}'s turn"

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, _CardRow):
            self._select_card(event.item.card)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _CardRow):
            self._select_card(event.item.card)

    def action_cursor_up(self) -> None:
        if self._list:
            self._list.action_cursor_up()

    def action_cursor_down(self) -> None:
        if self._list:
            self._list.action_cursor_down()

    def action_dismiss(self) -> None:
        log.info("CardListModal dismissed")
        self.dismiss()

    # --- buttons ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cl-cancel":
            self.dismiss()
        elif event.button.id == "cl-action":
            self._do_action()
        event.stop()

    def _do_action(self) -> None:
        """Play (hand) or draw (deck) the selected card — both reach the server
        as a scan on gwent/cards/raw/read, processed per the active stage."""
        card = self._selected
        if not card or not self.action or not self._is_turn():
            log.info("CardListModal: action ignored (card=%s action=%s turn=%s)",
                     bool(card), self.action, self._is_turn())
            return
        log.info("CardListModal: %s %s (rfid=%s) for %s",
                 self.action.upper(), card.get("name"), card.get("rfid"),
                 self.player_key)
        subscriber = getattr(self.app, "_subscriber", None)
        if subscriber is None:
            log.error("no _subscriber on app — cannot scan card")
            return
        subscriber.publish_card_scan(card)
        self.dismiss()

    # --- backdrop tap dismiss ---

    def on_click(self, event: events.Click) -> None:
        try:
            widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
        except Exception:
            widget = None
        node = widget
        while node is not None:
            if getattr(node, "id", None) == "cl-box":
                return
            node = getattr(node, "parent", None)
        log.info("CardListModal: backdrop tap — dismissing")
        self.dismiss()


def HandDetailModal(player_key: str, cards: list) -> CardListModal:
    """Convenience: a playable hand overlay for one player."""
    label = "Player 1" if player_key == P1 else "Player 2"
    return CardListModal(f"🃏  {label} — Hand", cards,
                         player_key=player_key, action="play")


def DeckDetailModal(player_key: str, cards: list) -> CardListModal:
    """Convenience: a deck overlay with a 'Draw from Deck' action."""
    label = "Player 1" if player_key == P1 else "Player 2"
    return CardListModal(f"📦  {label} — Deck", cards,
                         player_key=player_key, action="draw")
