"""CameraView — floating, draggable live-camera panel with REC indicator.

Visible while the camera is ON **and** live view is enabled (both from the
retained `gwent/camera/state` → GameState.camera_on / camera_live_view; the
show/hide toggle lives in the main menu and never affects recording).

A background thread polls the camera service's /still endpoint (~3 fps) and
frames render inline via the kitty graphics protocol (TGPImage) — the same
pathway CardImageOverlay uses for card art.

Floats on the `corner` layer (like #menu-corner, positioned imperatively) and
can be DRAGGED anywhere on screen — press/touch and move; the offset is
remembered for the session.

Profuse logging per feedback_profuse_logging — the kiosk has no console.
"""

import io
import logging
import threading

from PIL import Image
from textual.containers import Container

from textual_image.widget import TGPImage

log = logging.getLogger("gwent_tui.camera_view")

# Straight to the camera service (skips nginx — same host).
STILL_URL = "http://127.0.0.1:8081/still"
POLL_INTERVAL = 0.33   # ~3 fps
FETCH_TIMEOUT = 2.0
ERROR_BACKOFF = 2.0

# Panel size in cells (kiosk is ~114x34). 4:3 frame: 36 wide ≈ 13.5 tall at
# the ~1:2 cell aspect; +2 for the border.
PANEL_W = 38
PANEL_H = 15


class CameraView(Container):
    """Floating draggable live view; lifecycle driven by app._check_updates()."""

    DEFAULT_CSS = """
    CameraView {
        layer: corner;
        display: none;
        width: 38;
        height: 15;
        background: black;
        border: heavy $accent;
    }
    CameraView.visible { display: block; }
    CameraView #camera-image { width: 100%; height: 100%; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._poll_thread = None
        self._stop = threading.Event()
        self._offset = None          # (x, y) — current panel position
        self._frame_count = 0
        # Drag state: grab offset within the panel while the pointer is down.
        self._drag_grab = None

    def compose(self):
        yield TGPImage("", id="camera-image")

    # ------------------------------------------------------------------------
    # Lifecycle — single owner: app._check_updates() each tick
    # ------------------------------------------------------------------------

    def check_and_update(self):
        state = self.app.state
        want = bool(state.camera_on and state.camera_live_view)
        running = self._poll_thread is not None and self._poll_thread.is_alive()

        if want and not running:
            log.info("camera live view SHOW — starting /still poll thread")
            self._stop.clear()
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True, name="camera-view-poll")
            self._poll_thread.start()
            self.add_class("visible")
            self._apply_offset()
        elif not want and running:
            log.info("camera live view HIDE — stopping poll thread")
            self._stop.set()
            self._poll_thread = None
            self.remove_class("visible")

        if want:
            if state.camera_recording:
                self.border_title = "[red]⏺ REC[/]"
            else:
                self.border_title = "[green]📷 LIVE[/]"

    def _apply_offset(self):
        """Default to bottom-right; afterwards wherever the user dragged it."""
        try:
            sw = self.app.size.width
            sh = self.app.size.height
            if self._offset is None:
                self._offset = (max(0, sw - PANEL_W - 1),
                                max(0, sh - PANEL_H - 1))
            x, y = self._offset
            # Clamp inside the screen (e.g. after a resize)
            x = max(0, min(x, sw - PANEL_W))
            y = max(0, min(y, sh - PANEL_H))
            self._offset = (x, y)
            self.styles.offset = self._offset
            log.info("camera view placed at %s (screen %dx%d)",
                     self._offset, sw, sh)
        except Exception as e:
            log.debug("camera view placement failed: %s", e)

    # ------------------------------------------------------------------------
    # Dragging — press/touch anywhere on the panel and move
    # ------------------------------------------------------------------------

    def on_mouse_down(self, event) -> None:
        try:
            x, y = self._offset or (0, 0)
            self._drag_grab = (event.screen_x - x, event.screen_y - y)
            self.capture_mouse()
            log.info("camera view drag start at screen (%d,%d) grab=%s",
                     event.screen_x, event.screen_y, self._drag_grab)
        except Exception as e:
            log.error("camera view drag start failed: %s", e, exc_info=True)

    def on_mouse_move(self, event) -> None:
        if self._drag_grab is None:
            return
        try:
            gx, gy = self._drag_grab
            sw = self.app.size.width
            sh = self.app.size.height
            x = max(0, min(event.screen_x - gx, sw - PANEL_W))
            y = max(0, min(event.screen_y - gy, sh - PANEL_H))
            if (x, y) != self._offset:
                self._offset = (x, y)
                self.styles.offset = self._offset
        except Exception as e:
            log.debug("camera view drag move failed: %s", e)

    def on_mouse_up(self, event) -> None:
        if self._drag_grab is None:
            return
        try:
            self._drag_grab = None
            self.release_mouse()
            log.info("camera view drag end at %s", self._offset)
        except Exception as e:
            log.error("camera view drag end failed: %s", e, exc_info=True)

    # ------------------------------------------------------------------------
    # Poll thread
    # ------------------------------------------------------------------------

    def _poll_loop(self):
        import urllib.request
        log.info("camera poll loop started (%s @ %.2fs)", STILL_URL, POLL_INTERVAL)
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(STILL_URL, timeout=FETCH_TIMEOUT) as r:
                    data = r.read()
                img = Image.open(io.BytesIO(data))
                img.load()
                self.app.call_from_thread(self._set_frame, img)
            except Exception as e:
                log.warning("camera frame fetch failed: %s", e)
                self._stop.wait(ERROR_BACKOFF)
            self._stop.wait(POLL_INTERVAL)
        log.info("camera poll loop exited after %d frames", self._frame_count)

    def _set_frame(self, img):
        try:
            self._frame_count += 1
            self.query_one("#camera-image", TGPImage).image = img
        except Exception as e:
            log.error("camera frame render failed: %s", e, exc_info=True)
