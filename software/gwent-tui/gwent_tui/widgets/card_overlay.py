"""Card image overlay — modal dialog showing the last played card."""

import logging
import time

from rich.table import Table
from rich import box
from textual.containers import Horizontal
from textual.widgets import Static
from textual_image.widget import TGPImage

from gwent_tui.card_images import resolve_card_image
from gwent_tui.emoji import FACTION_STYLE
from gwent_tui.game_state import P1

log = logging.getLogger("gwent_tui.card_overlay")

DISPLAY_SECONDS = 8


class CardAttrsWidget(Static):
    """Displays card attributes as a vertical list."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._card = None

    def set_card(self, card):
        self._card = card
        self.refresh()

    def render(self):
        card = self._card
        if not card:
            return ""

        faction = card.get("faction", "")
        fc = FACTION_STYLE.get(faction, ("white", "grey30", "white"))
        color = fc[0]

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), expand=True)
        t.add_column("", style=f"bold {color}", width=10)
        t.add_column("")

        name = card.get("name", "???")
        t.add_row("Name", f"[bold bright_white]{name}[/]")
        t.add_row("Faction", f"[{color}]{faction}[/]")

        if card.get("strength") is not None:
            t.add_row("Strength", f"[bold yellow]{card['strength']}[/]")
        if card.get("ranges"):
            ranges = card["ranges"]
            range_icons = {"close": "\u2694 Close", "ranged": "\U0001f3f9 Ranged", "siege": "\U0001f3f0 Siege"}
            r_text = ", ".join(range_icons.get(r, r) for r in ranges)
            t.add_row("Range", r_text)
        if card.get("specialty"):
            t.add_row("Specialty", f"[bold]{card['specialty']}[/]")
        if card.get("abilities"):
            abilities = card["abilities"]
            if isinstance(abilities, list):
                t.add_row("Abilities", ", ".join(abilities))
        if card.get("owner"):
            t.add_row("Owner", f"[dim]{card['owner']}[/]")
        if card.get("card_text"):
            t.add_row("", "")
            t.add_row("", f"[italic dim]\u201c{card['card_text']}\u201d[/]")
        return t


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

        if state.last_played_card and elapsed < DISPLAY_SECONDS:
            card = state.last_played_card
            name = card.get("name", "???")
            faction = card.get("faction", "")

            if name != self._current_card_name:
                self._current_card_name = name

                # Track target row for flash highlight
                ranges = card.get("ranges", [])
                self._target_row = ranges[0] if ranges else "close"
                # current_player has already advanced to the next player,
                # so the one who just played is the OTHER player
                is_p1 = state.current_player != P1

                image_path = resolve_card_image(card)
                if image_path:
                    try:
                        img_widget = self.query_one("#overlay-image", TGPImage)
                        attrs_widget = self.query_one("#overlay-attrs", CardAttrsWidget)

                        img_widget.image = image_path
                        attrs_widget.set_card(card)

                        # P1: image left, attrs right. P2: attrs left, image right.
                        if is_p1:
                            img_widget.styles.order = 1
                            attrs_widget.styles.order = 2
                        else:
                            attrs_widget.styles.order = 1
                            img_widget.styles.order = 2

                        # Faction-colored border with card name
                        fc = FACTION_STYLE.get(faction, ("white", "grey30", "white"))
                        self.styles.border = ("round", fc[0])
                        self.styles.background = "black"
                        self.border_title = f" {name} "

                        # Center over the board
                        self._center_on_board()

                        # Track who played for the flash
                        self._card_player = str(P1) if is_p1 else str(state.current_player)

                        self.add_class("visible")
                        log.debug("Showing card image: %s (%s) p1=%s", name, image_path, is_p1)
                    except Exception as e:
                        log.debug("Failed to show card image: %s", e)
                else:
                    log.debug("No image for card: %s (%s)", name, faction)
                    self._hide()
        else:
            if self.has_class("visible"):
                self._hide()
                self._flash_row()

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
