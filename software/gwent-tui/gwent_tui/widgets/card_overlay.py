"""Card image overlay — modal dialog showing the last played card."""

import logging
import time

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal
from textual.widgets import Static
from textual_image.widget import TGPImage

from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import FACTION_STYLE
from gwent_tui.game_state import P1, P2

log = logging.getLogger("gwent_tui.card_overlay")

DISPLAY_SECONDS = 8

_POSSESSIVE = {"he": "his", "she": "her", "it": "its"}


class CardAttrsWidget(Static):
    """Displays card attributes as a vertical list with quote at bottom."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._card = None
        self._player_name = ""
        self._leader_pronoun = "he"
        self._subkind = "play_card"

    def set_card(self, card, player_name="", leader_pronoun="he", subkind="play_card", is_p1=True):
        self._card = card
        self._player_name = player_name
        self._leader_pronoun = leader_pronoun
        self._subkind = subkind
        self._is_p1 = is_p1
        self.refresh()

    def render(self):
        card = self._card
        if not card:
            return ""

        faction = card.get("faction", "")
        fc = FACTION_STYLE.get(faction, ("white", "grey30", "white"))
        color = fc[0]
        card_name = card.get("name", "???")

        # Build narration line — player plays/draws, pronoun from leader
        poss = _POSSESSIVE.get(self._leader_pronoun, "their")
        player = self._player_name or "Unknown"
        if self._subkind == "deal_leader":
            narration_text = f"[bold]{player}[/] commands [bold]{card_name}[/]"
        elif self._subkind == "spy_draw":
            narration_text = f"[bold]{player}[/] draws [bold]{card_name}[/] from the deck"
        elif self._subkind == "medic_resurrect":
            narration_text = f"[bold]{player}[/] resurrects [bold]{card_name}[/] from the graveyard"
        elif self._subkind == "deal_to_hand":
            narration_text = f"[bold]{player}[/] draws [bold]{card_name}[/] from the deck"
        elif self._subkind == "remove_card":
            narration_text = f"[bold red]{card_name}[/] is destroyed!"
        elif self._subkind == "decoy_swap":
            narration_text = f"[bold]{player}[/] recalls [bold]{card_name}[/] with a decoy"
        elif self._subkind == "transform":
            narration_text = f"[bold]{card_name}[/] transforms!"
        else:
            narration_text = f"[bold]{player}[/] plays [bold]{card_name}[/] from {poss} hand"

        # P1 text aligns left, P2 text aligns right
        justify = "left" if self._is_p1 else "right"
        narration = Text.from_markup(narration_text, justify=justify)

        # Card attributes table
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), expand=True)
        t.add_column("", style=f"bold {color}", width=10)
        t.add_column("")

        t.add_row("Faction", f"[{color}]{faction}[/]")

        if card.get("strength") is not None:
            t.add_row("Strength", f"[bold yellow]{card['strength']}[/]")
        if card.get("ranges"):
            ranges = card["ranges"]
            range_icons = {"close": "\u2694 Close", "ranged": "\U0001f3f9 Ranged", "siege": "\U0001f3f0 Siege"}
            r_text = " [dim]\u2502[/] ".join(range_icons.get(r, r) for r in ranges)
            t.add_row("Range", r_text)
        if card.get("specialty"):
            t.add_row("Specialty", f"[bold]{card['specialty']}[/]")
        if card.get("abilities"):
            abilities = card["abilities"]
            if isinstance(abilities, list):
                a_text = " [dim]\u2502[/] ".join(f"[bold]{a}[/]" for a in abilities)
                t.add_row("Abilities", a_text)
        if card.get("owner"):
            t.add_row("Owner", f"[dim]{card['owner']}[/]")

        # Blank line, narration, blank line, faction-colored separator, blank line, attrs
        sep = Text("\u2500" * 34, style=color)
        parts = [Text(""), narration, Text(""), sep, Text(""), t]

        # Quote at the bottom — pad with blank lines to push it down
        if card.get("card_text"):
            # Count rendered lines above:
            #   blank(1) + narration(2 wrap) + blank(1) + sep(1) + blank(1)
            #   + table top gap(1) + data rows + table bottom gap(1)
            row_count = 1  # faction always present
            for field in ("strength", "specialty", "owner"):
                if card.get(field) is not None:
                    row_count += 1
            if card.get("ranges"):
                row_count += 1
            if card.get("abilities"):
                row_count += 1
            content_lines = 1 + 2 + 1 + 1 + 1 + 1 + row_count + 1
            # Overlay inner height ~24 (28h - 2 border - 2 padding)
            # Reserve: quote (2 lines) + attribution (1) + bottom gap (1)
            padding = max(0, 24 - content_lines - 4)
            parts.append(Text("\n" * padding))
            parts.append(Text.from_markup(
                f"  [italic bright_white]\u201c{card['card_text']}\u201d[/]",
                justify=justify))
            parts.append(Text.from_markup(
                f"  [dim]\u2014 {card_name}[/]",
                justify=justify))
            parts.append(Text(""))

        return Group(*parts)


class CardImageOverlay(Horizontal):
    """Modal overlay showing card image + attributes when a card is played.

    Centered over the board area. Border color matches faction.
    P1 cards: image left, attrs right. P2 cards: attrs left, image right.
    """

    DEFAULT_CSS = """
    CardImageOverlay {
        display: none;
        layer: overlay;
        width: 80;
        height: 28;
    }
    CardImageOverlay.visible {
        display: block;
    }
    CardImageOverlay #overlay-image {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }
    CardImageOverlay #overlay-attrs {
        width: 1fr;
        height: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_card_name = None
        self._target_row = ""
        self._card_player = ""

    def compose(self):
        yield TGPImage("", id="overlay-image")
        yield CardAttrsWidget(id="overlay-attrs")

    def check_and_update(self):
        """Called periodically by the app to show/hide the overlay."""
        state = self.app.state
        now = time.time()
        elapsed = now - state.last_played_time

        display_secs = getattr(state, 'card_display_seconds', DISPLAY_SECONDS)
        if state.last_played_card and elapsed < display_secs:
            card = state.last_played_card
            name = card.get("name", "???")
            faction = card.get("faction", "")

            # Skip cards without images — advance queue until we find one
            image_path = resolve_card_image(card)
            if not image_path:
                log.debug("No image for card: %s (%s)", name, faction)
                self._hide()
                if hasattr(state, 'advance_card_queue'):
                    state.advance_card_queue()
                return

            if name != self._current_card_name:
                self._current_card_name = name

                # Track target row for flash highlight
                ranges = card.get("ranges", [])
                self._target_row = ranges[0] if ranges else "close"
                # Use last_played_by (set from MQTT topic) for accurate player tracking
                # Falls back to inverting current_player for backwards compat
                played_by = getattr(state, 'last_played_by', None)
                if played_by is not None:
                    is_p1 = played_by == P1
                else:
                    is_p1 = state.current_player != P1
                try:
                    img_widget = self.query_one("#overlay-image", TGPImage)
                    attrs_widget = self.query_one("#overlay-attrs", CardAttrsWidget)

                    img_widget.image = image_path

                    # Determine player name and pronoun for narration
                    player_key = P1 if is_p1 else P2
                    leader = state.reg_leader1 if is_p1 else state.reg_leader2
                    player_pronoun = getattr(state, 'player_pronouns', {}).get(
                        player_key, leader.get("pronoun", "he") if leader else "he")
                    player_name = getattr(state, 'player_names', {}).get(
                        player_key, "Player 1" if is_p1 else "Player 2")
                    subkind = getattr(state, 'last_played_subkind', '') or "play_card"

                    attrs_widget.set_card(
                        card,
                        player_name=player_name,
                        leader_pronoun=player_pronoun,
                        subkind=subkind,
                        is_p1=is_p1,
                    )

                    # P1: image left, attrs right. P2: attrs left, image right.
                    if is_p1:
                        self.move_child(img_widget, before=attrs_widget)
                    else:
                        self.move_child(attrs_widget, before=img_widget)

                    # Faction-colored border: P1/P2 + card name top, player/leader bottom
                    fc = FACTION_STYLE.get(faction, ("white", "grey30", "white"))
                    self.styles.border = ("round", fc[0])
                    self.styles.background = "black"
                    self.styles.border_subtitle_align = "center"

                    p_tag = "P1" if is_p1 else "P2"
                    tag_len = len(p_tag) + 1
                    center_pos = max(0, (78 - len(name)) // 2 - tag_len)
                    fill = "\u2500" * center_pos
                    self.styles.border_title_align = "left"
                    self.border_title = f" {p_tag} {fill} {name} "

                    leader_name = leader.get("name", "") if leader else ""
                    if leader_name:
                        self.border_subtitle = f" {player_name} / {leader_name} "
                    else:
                        self.border_subtitle = f" {player_name} "

                    # Center over the board
                    self._center_on_board()

                    # Track who played for the flash
                    self._card_player = str(P1) if is_p1 else str(state.current_player)

                    self.add_class("visible")
                    log.debug("Showing card image: %s (%s) p1=%s", name, image_path, is_p1)
                except Exception as e:
                    import sys, traceback
                    print(f"ERROR: Failed to show card image for {name}: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    log.error("Failed to show card image: %s", e, exc_info=True)
        else:
            if self.has_class("visible"):
                self._hide()
                self._flash_row()
                # Advance to next queued card if any
                if hasattr(state, 'advance_card_queue'):
                    state.advance_card_queue()

    def _center_on_board(self):
        """Position the overlay centered on the stage container."""
        try:
            stage = self.app.query_one("#stage-container")
            sr = stage.region
            w = 80
            h = 28
            self.styles.offset = (
                sr.x + (sr.width - w) // 2,
                sr.y + (sr.height - h) // 2,
            )
        except Exception:
            pass

    def _hide(self):
        self.remove_class("visible")
        self._current_card_name = None

    def _flash_row(self):
        """Highlight the target board row briefly after the card disappears."""
        state = self.app.state
        if self._target_row and self._card_player:
            state._highlight(f"flash:{self._card_player}:{self._target_row}", ttl=1.5)
