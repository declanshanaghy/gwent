"""TUI stage: MainMenu — State A.

When the backend is idle (no game) it publishes a retained `gwent/menu/present/main`
listing recordings + random + fresh-game options. We render that as a touchable
list. If the backend is mid-game (no main menu retained), we fall back to the
existing registration progress widget.
"""
import logging

from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.widgets.main_menu import MainMenuWidget
from gwent_tui.widgets.menu_choices import MenuChoicesWidget

log = logging.getLogger("gwent_tui.stages.main_menu")


class MainMenuStage(Vertical):
    DEFAULT_CSS = """
    MainMenuStage { height: 1fr; }
    #menu-title { dock: top; height: 1; content-align: center middle; background: $accent; color: black; text-style: bold; }
    #main-menu-choices { height: 1fr; }
    #menu-content { height: 1fr; }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._menu_widget: MenuChoicesWidget | None = None
        self._fallback: MainMenuWidget | None = None
        # Track last visibility decision so we don't log/touch widgets every
        # 1s tick — the periodic refresh in app.py calls us unconditionally.
        self._last_has_main: bool | None = None

    def compose(self):
        yield Static("⚔  GWENT — choose a game", id="menu-title")
        self._menu_widget = MenuChoicesWidget("main", id="main-menu-choices")
        yield self._menu_widget
        self._fallback = MainMenuWidget(id="menu-content")
        yield self._fallback

    def on_mount(self) -> None:
        log.info("MainMenuStage on_mount")
        self._update_visibility()

    def refresh_menu(self) -> None:
        """Called by the App when the menu cache updates."""
        log.debug("MainMenuStage refresh_menu")
        if self._menu_widget is not None:
            self._menu_widget.refresh_choices()
        self._update_visibility()

    def _update_visibility(self) -> None:
        state = getattr(self.app, "state", None)
        has_main = bool(state and state.menus.get("main"))
        if has_main == self._last_has_main:
            return
        self._last_has_main = has_main
        log.info("MainMenuStage visibility -> has_main=%s", has_main)
        if self._menu_widget is not None:
            self._menu_widget.display = has_main
        if self._fallback is not None:
            self._fallback.display = not has_main
