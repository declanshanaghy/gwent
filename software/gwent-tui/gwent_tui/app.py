"""Gwent TUI — Textual-based live game dashboard."""

import argparse
import json
import logging
import logging.handlers
import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from gwent_tui.game_state import GameState
from gwent_tui.mqtt_client import MqttSubscriber
from gwent_tui.widgets.header import HeaderWidget
from gwent_tui.widgets.footer import FooterWidget
from gwent_tui.widgets.timers import TimersWidget
from gwent_tui.stages import STAGE_WIDGETS, UnknownStage, OfflineStage
from gwent_tui.widgets.camera_view import CameraView
from gwent_tui.widgets.card_overlay import CardImageOverlay

log = logging.getLogger("gwent_tui.app")


def _configure_logging():
    _repo_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    log_file = os.path.join(_repo_root, "tmp", "logs", "gwent-tui.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=50 * 1024 * 1024, backupCount=3,
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


class RecDot(Static):
    """Red eye — floats above MenuCorner whenever the camera is recording."""

    _W = 3
    _H = 1

    def render(self):
        self._reposition()
        return "[bold red]👁[/bold red]"

    def on_mount(self) -> None:
        self._reposition()

    def on_resize(self, event) -> None:
        self._reposition()

    def _reposition(self) -> None:
        try:
            sw = self.app.size.width
            stage = getattr(self.app, "_current_stage_name", None)
            if stage == "PlayRound":
                # Centre within the left 1fr column (same column as the hamburger).
                col_w = sw // 2
                x = max(0, (col_w - self._W) // 2)
            else:
                x = max(0, (sw - self._W) // 2)
            offset = (x, 1)
            if getattr(self, "_last_offset", None) != offset:
                self._last_offset = offset
                self.styles.offset = offset
        except Exception as e:
            log.debug("rec-dot reposition failed: %s", e)


class MenuCorner(Static):
    """Floating affordance that opens the in-game menu.

    Renders the SAME chunky three-bar hamburger as the PlayRound player-bar
    menu cell, so the trigger looks identical on every screen. Hidden in
    PlayRound (the player bar hosts it there).
    """

    _W = 7
    _H = 5

    def render(self):
        self._recenter()
        return "▬▬▬\n▬▬▬\n▬▬▬"

    def on_mount(self) -> None:
        self._recenter()

    def on_resize(self, event) -> None:
        self._recenter()

    def _recenter(self) -> None:
        """Centered horizontally, two rows from the top."""
        try:
            sw = self.app.size.width
            offset = ((sw - self._W) // 2, 2)
            if getattr(self, "_last_offset", None) != offset:
                self._last_offset = offset
                self.styles.offset = offset
        except Exception as e:
            log.debug("menu-corner recenter failed: %s", e)

    def on_click(self, event) -> None:
        try:
            self.app.action_in_game_menu()
        except Exception as e:
            log.error("menu-corner open failed: %s", e, exc_info=True)


class GwentTUI(App):
    """Gwent Companion TUI."""

    TITLE = "Gwent TUI"

    CSS = """
    Screen { layout: vertical; layers: bg default overlay corner; }
    * { scrollbar-size: 0 0; }
    /* Card lists ALWAYS get a right vertical scrollbar. Must live here (App
       CSS) — widget DEFAULT_CSS loses to the global rule above. */
    HandsWidget, DecksWidget, DiscardWidget, DealCardsStage, #cl-list, #hd-list,
    MenuChoicesWidget ListView, #imm-list {
        scrollbar-size-horizontal: 0;
        scrollbar-size-vertical: 2;
        scrollbar-color: $accent;
        scrollbar-background: $surface-darken-1;
    }
    /* Header is hidden by default to maximize board space; toggled via the
       in-game menu (Screen.show-header). A small stage-icon button floats in
       the top-left corner so the menu stays reachable while it's hidden. */
    #menu-corner {
        layer: corner;
        width: 7;
        height: 5;
        background: $panel;
        color: $accent;
        border: heavy $accent;
        content-align: center middle;
        text-style: bold;
    }
    /* NOTE: menu-corner show/hide is driven imperatively from
       _check_updates() (single owner) — not via Screen.<class> rules. */
    /* Blurred splash image, full-screen behind everything. Shown only on the
       New Game screen (Screen.newgame). On that screen the panels go
       translucent so the image reads through as a background. */
    #bg-image { layer: bg; width: 100%; height: 100%; display: none; }
    Screen.newgame #bg-image { display: block; }
    Screen.newgame #header { background: transparent 0%; }
    Screen.newgame #stage-container { background: transparent 0%; }
    Screen.newgame #bottom-bar { background: transparent 0%; }
    Screen.newgame #footer { background: transparent 0%; }
    Screen.newgame #timers { background: transparent 0%; }
    #header { height: 4; display: none; }
    Screen.show-header #header { display: block; }
    #stage-container { height: 1fr; overflow: hidden; }
    /* Events + Timers are hidden by default to give the board/hands more
       room; toggled on via the in-game menu (Screen.show-panels). */
    #bottom-bar { height: 8; display: none; }
    Screen.show-panels #bottom-bar { display: block; }
    #footer { width: 3fr; height: 100%; }
    #timers { width: 1fr; height: 100%; }
    #card-overlay { layer: overlay; }
    #rec-dot {
        layer: corner;
        width: 3;
        height: 1;
        background: transparent;
        content-align: center middle;
        display: none;
    }
    """

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help"),
        Binding("right", "next_track", "Next Track"),
        Binding("v", "volume_mixer", "Volume Mixer"),
        Binding("m", "in_game_menu", "Menu"),
        Binding("ctrl+m", "toggle_music", "Music On/Off"),
    ]

    def __init__(self, mqtt_host: str = "localhost",
                 mqtt_port: int = 1883, no_splash: bool = False):
        super().__init__()
        self.state = GameState()
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._no_splash = no_splash
        self._subscriber = None
        self._current_stage_name = None
        self._prev_server_online = True
        # Last mfd_pick seq we popped a modal for (avoid re-pop on dismiss).
        self._mfd_pick_seen = 0

    def compose(self) -> ComposeResult:
        log.debug("compose() start")
        # Half-cell renderer (not TGP/kitty) so the image is composed of real
        # colored cells — the New Game panels on higher layers composite over
        # it. A kitty-graphics image can't sit behind text cells.
        from textual_image.widget import HalfcellImage
        import os as _os
        _bg = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                            "assets", "splash_blur.png")
        yield HalfcellImage(_bg if _os.path.exists(_bg) else "", id="bg-image")
        yield HeaderWidget(id="header")
        # Stage container — will be populated dynamically
        yield UnknownStage(id="stage-container")
        with Horizontal(id="bottom-bar"):
            yield FooterWidget(id="footer")
            yield TimersWidget(id="timers")
        yield CardImageOverlay(id="card-overlay")
        yield RecDot(id="rec-dot")
        yield MenuCorner(id="menu-corner")
        yield CameraView(id="camera-view")
        log.debug("compose() done")

    # --- profuse input logging (per feedback_profuse_logging) ----------------
    # These fire for any event that bubbles up to the App (i.e. wasn't handled
    # by a child widget). Useful for verifying touch → wl_pointer → kitty →
    # Textual delivery on the kiosk panel.

    def on_mouse_down(self, event):
        log.debug(
            "MouseDown x=%d y=%d button=%d screen=(%d,%d)",
            event.x, event.y, event.button, event.screen_x, event.screen_y,
        )

    def on_mouse_up(self, event):
        log.debug(
            "MouseUp   x=%d y=%d button=%d", event.x, event.y, event.button,
        )

    def on_click(self, event):
        log.info(
            "APP CLICK x=%d y=%d screen=(%d,%d) button=%d ctrl=%s meta=%s",
            event.x, event.y, event.screen_x, event.screen_y,
            event.button, event.ctrl, event.meta,
        )

    def on_key(self, event):
        log.info(
            "Key key=%r character=%r name=%s",
            event.key, event.character, event.name,
        )

    def on_resize(self, event):
        log.info("Resize new_size=%dx%d", event.size.width, event.size.height)
    # -------------------------------------------------------------------------

    def on_mount(self):
        log.info("gwent-tui starting (mqtt=%s:%d)", self._mqtt_host, self._mqtt_port)
        log.info(
            "env: TERM=%s KITTY_WINDOW_ID=%s WAYLAND_DISPLAY=%s XDG_SESSION_TYPE=%s",
            os.environ.get("TERM"),
            os.environ.get("KITTY_WINDOW_ID"),
            os.environ.get("WAYLAND_DISPLAY"),
            os.environ.get("XDG_SESSION_TYPE"),
        )
        log.info(
            "on_mount: console size=%dx%d driver=%s",
            self.size.width, self.size.height,
            type(self._driver).__name__ if self._driver else "?",
        )

        # Apply persisted mixer volumes (Master / Music / SFX / TTS).
        try:
            from gwent_tui.volume_mixer import apply_persisted_state
            apply_persisted_state()
        except Exception as e:
            log.error("Mixer state restore failed: %s", e, exc_info=True)

        # Splash screen
        if not self._no_splash:
            from gwent_tui.splash import SplashScreen
            self.push_screen(SplashScreen(duration=6.0))

        # MQTT — also carries the full game-state snapshot (retained
        # gwent/server/state), so no separate HTTP poller is needed.
        self._subscriber = MqttSubscriber(
            self.state, host=self._mqtt_host, port=self._mqtt_port)
        self._subscriber.connect()

        # Register client TTS provider with the server
        self._register_client_tts()

        # Periodic refresh as fallback (1s)
        self.set_interval(1.0, self._check_updates)

    async def _check_updates(self):
        """Periodic refresh + presence-driven offline handling."""
        # Re-register client TTS when the server (re)comes online so a server
        # restart re-learns that this client handles audio.
        if self.state.server_online and not self._prev_server_online:
            self._register_client_tts()
        self._prev_server_online = self.state.server_online

        # Switch to/from offline stage based on MQTT presence.
        if not self.state.server_online:
            if self._current_stage_name != "Offline":
                self.state.stage = "Offline"
                await self._refresh_all()
        elif self._current_stage_name == "Offline":
            # Recovered — refresh will pick up the real stage
            await self._refresh_all()
        # Refresh all Static widgets so MQTT-driven updates (dealt cards,
        # announcements, etc.) appear. When a new snapshot has arrived, do a
        # LAYOUT refresh so auto-height panels (e.g. Hands) recompute their
        # size — a plain repaint updates text but leaves rows clipped.
        try:
            await self._switch_stage(self.state.stage)
            layout = self.state.dirty
            self.state.dirty = False
            for widget in self.query("Static"):
                widget.refresh(layout=layout)
            # Menu mirror — if the current stage exposes refresh_menu(),
            # rebuild its choice list from the cache.
            for stage in self.query("MainMenuStage"):
                try:
                    stage.refresh_menu()
                except Exception as e:
                    log.error("refresh_menu failed: %s", e, exc_info=True)
        except Exception as e:
            log.error("Error refreshing widgets: %s", e, exc_info=True)
        # Update card image overlay (separate try to avoid swallowing errors)
        try:
            self.query_one("#card-overlay", CardImageOverlay).check_and_update()
        except Exception as e:
            log.error("Card overlay error: %s", e, exc_info=True)
        # Camera live view — show/hide + REC indicator from gwent/camera/state
        try:
            self.query_one("#camera-view", CameraView).check_and_update()
        except Exception as e:
            log.error("Camera view error: %s", e, exc_info=True)
        # Interactive MFD pick popup (agile row / leader weather pick, …) —
        # pop when a numeric-id choice set is pending, keep its title fresh,
        # and auto-close if the pick resolves elsewhere (rotary, LLM loop).
        try:
            from gwent_tui.mfd_choice_modal import MFDChoiceModal
            pick = self.state.mfd_pick
            top = self.screen_stack[-1] if len(self.screen_stack) > 1 else None
            showing = isinstance(top, MFDChoiceModal)
            if pick is not None:
                if showing and top.pick.get("seq") == pick.get("seq"):
                    top.refresh_title()
                elif not showing and len(self.screen_stack) == 1 and \
                        pick.get("seq") != self._mfd_pick_seen:
                    self._mfd_pick_seen = pick.get("seq")
                    log.info("popping MFDChoiceModal for pick #%s",
                             pick.get("seq"))
                    self.push_screen(MFDChoiceModal(pick))
            elif showing:
                log.info("mfd pick resolved elsewhere — closing popup")
                top.dismiss()
        except Exception as e:
            log.error("mfd pick popup handling failed: %s", e, exc_info=True)

        # Menu-corner visibility — computed in ONE place every tick and set
        # inline (the Screen.<class> #menu-corner CSS rules did not reliably
        # re-evaluate, leaving the corner visible in PlayRound). Hidden when:
        # anything is on top of the board (modal / card overlay), the header
        # is shown (it has its own ☰), a deal is in progress, or we're in
        # PlayRound — there the ☰ lives in the player bar's centre cell.
        try:
            base = self.screen_stack[0]
            card_overlay_up = self.query_one(
                "#card-overlay", CardImageOverlay).has_class("visible")
            modal_up = len(self.screen_stack) > 1
            base.set_class(card_overlay_up or modal_up, "overlay-active")
            hide = (
                card_overlay_up or modal_up
                or base.has_class("show-header")
                or self._current_stage_name in (
                    "PlayRound",
                    "RegisterLeaders", "RegisterDecks", "DealCards")
            )
            self.query_one("#menu-corner").display = not hide
            cam_on = getattr(self.state, "camera_on", False)
            self.query_one("#rec-dot").display = bool(cam_on) and not hide
        except Exception as e:
            log.debug("menu-corner visibility toggle failed: %s", e)

    async def _switch_stage(self, stage_name):
        """Swap the stage container widget if the stage changed."""
        if stage_name == self._current_stage_name:
            return

        self._current_stage_name = stage_name

        # Show the blurred splash background only on the New Game screen.
        try:
            self.screen.set_class(stage_name == "MainMenu", "newgame")
            # Hide the menu button while a game is being dealt / loaded — keep
            # it hidden through registration + dealing until PlayRound begins.
            dealing = stage_name in (
                "RegisterLeaders", "RegisterDecks", "DealCards")
            self.screen.set_class(dealing, "dealing")
        except Exception as e:
            log.debug("set stage classes failed: %s", e)

        if stage_name == "Offline":
            stage_cls = OfflineStage
        else:
            stage_cls = STAGE_WIDGETS.get(stage_name)

            if stage_cls is None and stage_name != "—":
                log.error("No TUI screen for stage: %s", stage_name)
                stage_cls = UnknownStage

            if stage_cls is None:
                stage_cls = UnknownStage

        # Replace the stage container
        try:
            old = self.query_one("#stage-container")
            await old.remove()
        except Exception as e:
            log.error("Error removing old stage: %s", e, exc_info=True)

        new_widget = stage_cls(id="stage-container")
        try:
            await self.mount(new_widget, before=self.query_one("#bottom-bar"))
            log.info("Switched to stage: %s", stage_name)
        except Exception as e:
            log.error("Failed to mount stage %s: %s", stage_name, e)

        log.info("Switched to stage: %s (%s)", stage_name, stage_cls.__name__)
        try:
            self.query_one("#rec-dot", RecDot)._reposition()
        except Exception:
            pass

    async def _refresh_all(self):
        """Refresh all visible widgets and switch stage if needed."""
        await self._switch_stage(self.state.stage)
        # Refresh all Static widgets (including those nested inside VerticalScroll)
        try:
            for widget in self.query("Static"):
                widget.refresh()
        except Exception as e:
            log.error("Error refreshing all widgets: %s", e, exc_info=True)

    # --- Actions ---

    def action_toggle_panels(self):
        """Show/hide the Events + Timers bottom bar (more room for the board)."""
        try:
            self.screen.toggle_class("show-panels")
            on = self.screen.has_class("show-panels")
            log.info("toggle panels -> %s", "shown" if on else "hidden")
        except Exception as e:
            log.error("toggle_panels failed: %s", e, exc_info=True)

    def action_toggle_header(self):
        """Show/hide the top header bar (the corner icon still opens the menu)."""
        try:
            self.screen.toggle_class("show-header")
            on = self.screen.has_class("show-header")
            log.info("toggle header -> %s", "shown" if on else "hidden")
        except Exception as e:
            log.error("toggle_header failed: %s", e, exc_info=True)

    def action_help(self):
        from textual.screen import ModalScreen
        from textual.widgets import Static as S
        from rich.table import Table
        from rich import box

        class HelpScreen(ModalScreen):
            CSS = """
            HelpScreen { align: center middle; }
            #help-box { width: 60; height: auto; max-height: 30; border: round $accent;
                        padding: 1 2; background: $surface; }
            """
            BINDINGS = [Binding("escape", "dismiss", "Close")]

            def compose(self):
                yield S(id="help-box")

            def on_mount(self):
                table = Table(box=box.ROUNDED, expand=False, show_header=True,
                              padding=(0, 2), title="\U0001f3ae Keyboard Shortcuts",
                              title_style="bold bright_cyan")
                table.add_column("Key", style="bold yellow", justify="right")
                table.add_column("Action", style="white")
                for key, action in [
                    ("?", "Help"),
                    ("m / tap header", "In-game menu (Reset / Volume / Help)"),
                    ("v", "Volume mixer (Master / Music / SFX / TTS)"),
                    ("Ctrl+M", "Toggle music on/off"),
                    ("\u2192", "Next music track"),
                    ("Ctrl+C", "Quit"),
                    ("Esc", "Close dialog/help"),
                ]:
                    table.add_row(key, action)
                self.query_one("#help-box").update(table)

            def on_key(self, event):
                self.dismiss()

            def on_click(self, event):
                try:
                    widget, _ = self.get_widget_at(event.screen_x, event.screen_y)
                except Exception:
                    widget = None
                node = widget
                while node is not None:
                    if getattr(node, "id", None) == "help-box":
                        return
                    node = getattr(node, "parent", None)
                self.dismiss()

        self.push_screen(HelpScreen())

    def action_next_track(self):
        """Skip to next music track (only if music is enabled)."""
        if self._subscriber and self._subscriber.music_enabled:
            self._subscriber._publish_music_complete()

    def action_volume_mixer(self):
        """Open the 4-channel volume mixer modal (Master/Music/SFX/TTS)."""
        from gwent_tui.volume_mixer import VolumeMixerModal
        log.info("Opening volume mixer modal")
        self.push_screen(VolumeMixerModal())

    def action_in_game_menu(self):
        """Open the in-game hamburger menu (Reset / Volume / Help / Cancel)."""
        from gwent_tui.in_game_menu_modal import InGameMenuModal
        log.info("Opening in-game menu modal")
        self.push_screen(InGameMenuModal())

    def action_toggle_music(self):
        """Toggle music on/off via MQTT."""
        if self._subscriber:
            self._subscriber.publish_music_toggle()
            self.state._log_event(
                f"\U0001f3b5 Music {'ON' if self._subscriber.music_enabled else 'OFF'}",
                color="plum1")

    def _register_client_tts(self):
        """Register this client's TTS provider with the server over MQTT."""
        from gwent_tui import tts as tts_mod
        provider = tts_mod._provider_name or "auto"
        if self._subscriber:
            self._subscriber.publish_client_tts(provider)

    def on_unmount(self):
        from gwent_tui import tts as tts_mod
        tts_mod.stop_music()
        tts_mod.stop()
        if self._subscriber:
            self._subscriber.disconnect()
        log.info("gwent-tui stopped")


def main():
    _configure_logging()

    parser = argparse.ArgumentParser(description="Gwent TUI — live game dashboard")
    parser.add_argument("--host", default="localhost",
                        help="Gwent MQTT broker hostname")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--tts", default=None,
                        help="TTS provider (piper, say, elevenlabs, openai, gtts). "
                             "Default: say on macOS, piper on Linux")
    parser.add_argument("--no-splash", action="store_true",
                        help="Skip the startup splash screen")
    args = parser.parse_args()

    # Initialise TTS before app starts
    from gwent_tui import tts as tts_mod
    tts_mod.init(args.tts)

    app = GwentTUI(
        mqtt_host=args.host,
        mqtt_port=args.port,
        no_splash=args.no_splash,
    )
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
