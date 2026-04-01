#!/usr/bin/env python3
"""POC: Test the card overlay dialog without playing a full game.

Picks a random card (or accepts a path) and displays it using the same
CardImageOverlay / CardAttrsWidget that the live gwent-tui uses.
The event subkind is inferred from the card's abilities/specialty,
matching the same logic the game server uses.

Usage:
    python -m gwent.poc.card_dialog_test [--card PATH] [--player 1|2]

Requires: pip install textual-image gwent-tui
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

# Re-use the real overlay from gwent-tui
from gwent_tui.widgets.card_overlay import CardImageOverlay
from gwent_tui.card_images import resolve_card_image
from gwent_tui.game_state import P1, P2

CYCLE_SECONDS = 5

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
CARDS_DIR = DATA_DIR / "cards"


def infer_subkind(card: dict) -> str:
    """Determine the overlay subkind from card attributes.

    Mirrors the game server logic in play_round.py:
    - spy ability   -> spy_draw   (player draws from deck after playing spy)
    - medic ability -> medic_resurrect (card resurrected from discard)
    - muster ability -> muster    (mustered from deck/hand)
    - everything else -> play_card
    """
    abilities = card.get("abilities", [])
    if not isinstance(abilities, list):
        abilities = []
    if "spy" in abilities:
        return "spy_draw"
    if "medic" in abilities:
        return "medic_resurrect"
    if "muster" in abilities:
        return "muster"
    return "play_card"


class MockState:
    """Minimal game state to satisfy CardImageOverlay.check_and_update()."""

    def __init__(self, card: dict, player_num: int, leader: dict):
        self.last_played_card = card
        self.last_played_time = time.time()
        self.last_played_subkind = infer_subkind(card)

        # current_player is inverted in overlay — the overlay checks
        # `state.current_player != P1` to determine who just played.
        # If player_num==1, we want is_p1=True, so current_player must be P2.
        self.current_player = P2 if player_num == 1 else P1

        self.reg_leader1 = leader if player_num == 1 else None
        self.reg_leader2 = leader if player_num == 2 else None

        # Mock player names for the border subtitle
        self.player_names = {
            P1: "Declan" if player_num == 1 else "Dandelion",
            P2: "Dandelion" if player_num == 1 else "Declan",
        }

        # Stubs for anything else the overlay or app might access
        self.stage = "play_round"


class CardDialogApp(App):
    """Standalone app to preview the card overlay."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("enter", "next_card", "Next card"),
    ]

    CSS = """
    Screen { layout: vertical; background: $surface; }
    #stage-container { width: 100%; height: 1fr; }
    #help { height: 1; content-align: center middle; }
    """

    def __init__(self, card: dict, player_num: int, leader: dict):
        super().__init__()
        self._player_num = player_num
        self.state = MockState(card, player_num, leader)

    def compose(self) -> ComposeResult:
        with Vertical(id="stage-container"):
            yield Static("")
        yield CardImageOverlay(id="card-overlay")
        yield Static(
            f"[dim]Enter: next card | q: quit | Auto-cycles every {CYCLE_SECONDS}s[/]",
            id="help",
        )

    def on_mount(self) -> None:
        # Defer first render until after layout so #stage-container has real dimensions
        self.set_timer(0.3, self._show_overlay)
        # Cycle to a new random card after each display period
        self.set_interval(CYCLE_SECONDS, self._next_card)

    def _show_overlay(self) -> None:
        self.state.last_played_time = time.time()
        overlay = self.query_one(CardImageOverlay)
        # Force re-render even if same card name (e.g. player side changed)
        overlay._current_card_name = None
        overlay.check_and_update()

    def _next_card(self) -> None:
        """Cycle to a new random card (skip cards without images)."""
        for _ in range(20):
            card, _ = _random_card()
            if resolve_card_image(card):
                break
        else:
            import sys
            print("WARNING: Could not find a card with an image", file=sys.stderr)
        faction = card.get("faction", "Northern Realms")
        leader = _find_leader_for_faction(faction)
        # Random player side
        self._player_num = random.choice([1, 2])
        self.state = MockState(card, self._player_num, leader)
        self._show_overlay()

    def action_next_card(self) -> None:
        """Enter key cycles to next card."""
        self._next_card()


def _load_card(path: str) -> dict:
    """Load a card JSON file."""
    with open(path) as f:
        return json.load(f)


def _random_card() -> tuple[dict, str]:
    """Pick a random card JSON and return (card_dict, path)."""
    files = list(CARDS_DIR.glob("**/*.json"))
    if not files:
        print(f"No card files found in {CARDS_DIR}", file=sys.stderr)
        sys.exit(1)
    path = random.choice(files)
    return _load_card(str(path)), str(path)


def _find_leader_for_faction(faction: str) -> dict:
    """Find a random leader card for the given faction."""
    faction_dirs = {
        "Northern Realms": "NorthernRealms",
        "Monsters": "Monsters",
        "Nilfgaardian": "Nilfgaardian",
        "Scoia'tael": "Scoiatael",
        "Skellige": "Skellige",
        "Neutral": "NorthernRealms",  # fallback
    }
    dir_name = faction_dirs.get(faction, faction)
    faction_dir = CARDS_DIR / dir_name
    if not faction_dir.exists():
        # Fallback: search all dirs
        faction_dir = CARDS_DIR

    leaders = []
    for f in faction_dir.glob("*.json"):
        try:
            card = json.loads(f.read_text())
            if card.get("specialty") == "leader":
                leaders.append(card)
        except (json.JSONDecodeError, KeyError):
            continue

    if leaders:
        return random.choice(leaders)
    # Ultimate fallback
    return {"name": "Unknown Leader", "pronoun": "he", "faction": faction}


def main():
    parser = argparse.ArgumentParser(description="Test the card overlay dialog")
    parser.add_argument("--card", "-c", help="Path to a card JSON file (default: random)")
    parser.add_argument("--player", "-p", type=int, choices=[1, 2], default=1,
                        help="Player number (1=image left, 2=image right)")
    args = parser.parse_args()

    if args.card:
        card_path = os.path.abspath(args.card)
        if not os.path.exists(card_path):
            print(f"Card file not found: {card_path}", file=sys.stderr)
            sys.exit(1)
        card = _load_card(card_path)
    else:
        card, card_path = _random_card()

    faction = card.get("faction", "Northern Realms")
    leader = _find_leader_for_faction(faction)
    subkind = infer_subkind(card)

    print(f"Card:    {card.get('name', '???')} ({faction})")
    print(f"Leader:  {leader.get('name', '???')} (pronoun: {leader.get('pronoun', '?')})")
    print(f"Player:  {args.player} ({'image left' if args.player == 1 else 'image right'})")
    print(f"Subkind: {subkind} (inferred from card abilities)")
    print(f"Path:    {card_path}")
    print()

    app = CardDialogApp(card, args.player, leader)
    app.run()


if __name__ == "__main__":
    main()
