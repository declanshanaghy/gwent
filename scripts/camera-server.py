#!/usr/bin/env python3
"""Camera HTTP + MQTT server for the onboard Pi NoIR camera (IMX219).

Owns the camera continuously via picamera2 and serves:

    GET /still   -> single JPEG frame (current camera view)
    GET /stream  -> live MJPEG stream (multipart/x-mixed-replace)

Listens on 127.0.0.1:8081; nginx reverse-proxies it at 0.0.0.0:80/camera/
(including /camera/recordings/ served straight off disk by nginx).

MQTT control plane (broker on localhost, user geralt):

    gwent/camera/ctrl   (in)  {"action": on|off|record-start|record-stop|
                               save|discard|evict-saved, "game_id": ...,
                               "bytes_needed": ..., "timestamp": ISO8601}
    gwent/camera/state  (out, retained) full camera/recordings status

Recording: H.264 (vc4 hardware) at 3 Mbps, 1280x960@30, fragmented MP4 via
FfmpegOutput so a crash mid-recording still leaves a playable file. The H264
encoder attaches to the running camera alongside the MJPEG stream encoder
(verified concurrent on vc4). Files land in tmp/recordings/unconfirmed/ and
are promoted to saved/ on user confirmation at Game Over. Budget/eviction
policy lives in camera_recordings.py (10 GiB cap, 1.5 GiB headroom).

Camera on/off is a logical flag (persisted in tmp/recordings/.camera-on so it
survives restarts): the MJPEG stream stays available regardless; the flag
gates game recording and the TUI live view.

NOTE: while this service is running it owns the camera, so scripts/camera.sh
(rpicam-still/-vid) will fail with "camera busy". Stop the service first:
    sudo systemctl stop gwent-camera
"""

import io
import json
import logging
import os
import signal
import sys
import threading
from datetime import datetime
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn

import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder, Quality
from picamera2.outputs import FfmpegOutput, FileOutput

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_recordings  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "tmp" / "logs"
LOG_FILE = LOG_DIR / "camera-server.log"

BIND_ADDR = ("127.0.0.1", 8081)
# 4:3 keeps the full IMX219 field of view; 1280x960 is safely inside the
# vc4 hardware encoder limits for both MJPEG and H264.
STREAM_SIZE = (1280, 960)
FRAMERATE = 30
# The onboard module is a NoIR — without this tuning everything is magenta
# from IR contamination.
TUNING_FILE = "imx219_noir.json"

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "geralt"
MQTT_PASS = "gwent"
CH_CAMERA_CTRL = "gwent/camera/ctrl"
CH_CAMERA_STATE = "gwent/camera/state"

CAMERA_ON_FLAG = camera_recordings.REC_ROOT / ".camera-on"

logger = logging.getLogger("camera-server")


def iso_now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class ISOFormatter(logging.Formatter):
    """ISO 8601 timestamps with timezone offset."""

    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).astimezone().isoformat(
            timespec="seconds"
        )


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = ISOFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    for handler in (
        logging.StreamHandler(sys.stdout),  # journald via systemd
        logging.FileHandler(LOG_FILE),
    ):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class StreamingOutput(io.BufferedIOBase):
    """Holds the latest MJPEG frame; notifies stream readers on each write."""

    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class RecordingController:
    """Owns the H264 recording lifecycle + camera_on flag + state snapshots.

    Thread-safe: HTTP threads, the MQTT thread, and the main thread all call
    in here.
    """

    def __init__(self, picam2):
        self._picam2 = picam2
        self._lock = threading.Lock()
        self._h264 = None
        self._ffout = None
        self._game_id = None
        self._camera_on = CAMERA_ON_FLAG.is_file()
        # TUI live-view panel visibility. Deliberately NOT persisted —
        # always starts hidden (off by default); recording is unaffected.
        self._live_view = False
        logger.info("camera_on restored from flag file: %s", self._camera_on)

    # -- camera on/off ------------------------------------------------------

    @property
    def camera_on(self):
        return self._camera_on

    def set_camera(self, on):
        with self._lock:
            self._camera_on = bool(on)
            try:
                if on:
                    CAMERA_ON_FLAG.touch()
                else:
                    CAMERA_ON_FLAG.unlink(missing_ok=True)
            except OSError as exc:
                logger.error("failed to persist camera_on flag: %s", exc)
            logger.info("camera turned %s", "ON" if on else "OFF")
            if not on and self._h264 is not None:
                self._record_stop_locked()

    def set_live_view(self, on):
        with self._lock:
            self._live_view = bool(on)
            logger.info("live view %s (recording unaffected)",
                        "SHOWN" if on else "HIDDEN")

    # -- recording ----------------------------------------------------------

    @staticmethod
    def _safe_game_id(game_id):
        # filename-safe: basename only, no path tricks
        return Path(str(game_id)).name or "unknown"

    def record_start(self, game_id):
        with self._lock:
            if not self._camera_on:
                logger.warning("record-start ignored: camera is OFF")
                return False
            if self._h264 is not None:
                logger.warning("record-start while recording %s — stopping it",
                               self._game_id)
                self._record_stop_locked()

            game_id = self._safe_game_id(game_id)
            camera_recordings.ensure_dirs()
            # Auto-evict oldest unconfirmed to reach headroom (never saved/)
            freed, deleted = camera_recordings.evict_unconfirmed(logger)
            if not camera_recordings.headroom_ok():
                logger.warning(
                    "record-start refused: %.2f GB free in budget < %.2f GB "
                    "headroom and only saved/ recordings remain",
                    camera_recordings.budget_free() / 1e9,
                    camera_recordings.HEADROOM_BYTES / 1e9)
                return False

            path = camera_recordings.recording_path(game_id)
            self._h264 = H264Encoder(bitrate=camera_recordings.BITRATE)
            # Fragmented MP4: playable even if we die mid-recording
            self._ffout = FfmpegOutput(
                f"-movflags +frag_keyframe+empty_moov {path}")
            self._picam2.start_encoder(self._h264, self._ffout, name="main")
            self._game_id = game_id
            logger.info("recording started: %s (%.1f Mbps, evicted %d/%0.1f MB)",
                        path.name, camera_recordings.BITRATE / 1e6,
                        len(deleted), freed / 1e6)
            return True

    def _record_stop_locked(self):
        if self._h264 is None:
            return None
        game_id = self._game_id
        try:
            self._picam2.stop_encoder(self._h264)
        except Exception:
            logger.exception("error stopping H264 encoder")
        self._h264 = None
        self._ffout = None
        self._game_id = None
        path = camera_recordings.recording_path(game_id)
        size = path.stat().st_size if path.is_file() else 0
        logger.info("recording stopped: %s (%.1f MB, unconfirmed)",
                    path.name, size / 1e6)
        return game_id

    def record_stop(self):
        with self._lock:
            return self._record_stop_locked()

    def save(self, game_id):
        with self._lock:
            game_id = self._safe_game_id(game_id)
            if self._game_id == game_id:
                logger.info("save requested for in-flight %s — stopping first",
                            game_id)
                self._record_stop_locked()
            return camera_recordings.move_to_saved(f"{game_id}.mp4", logger)

    def discard(self, game_id):
        # Discard = leave in unconfirmed/ (evictable). Just stop if in-flight.
        with self._lock:
            game_id = self._safe_game_id(game_id)
            if self._game_id == game_id:
                self._record_stop_locked()
            logger.info("recording %s discarded (left in unconfirmed/)", game_id)

    def evict_saved(self, bytes_needed):
        with self._lock:
            freed, deleted = camera_recordings.evict_saved(logger, bytes_needed)
            logger.info("evict-saved: freed %.2f GB (%d files)",
                        freed / 1e9, len(deleted))
            return freed, deleted

    # -- state --------------------------------------------------------------

    def snapshot(self):
        with self._lock:
            recording = self._h264 is not None
            game_id = self._game_id
        recs = []
        exclude = f"{game_id}.mp4" if game_id else None
        for r in camera_recordings.list_recordings():
            sub = "saved" if r["saved"] else "unconfirmed"
            recs.append({
                "file": r["file"],
                "size": r["size"],
                "saved": r["saved"],
                "in_progress": r["file"] == exclude,
                "url_path": f"/camera/recordings/{sub}/{r['file']}",
                "mtime": datetime.fromtimestamp(r["mtime"]).astimezone()
                         .isoformat(timespec="seconds"),
            })
        return {
            "online": True,
            "camera_on": self._camera_on,
            "live_view": self._live_view,
            "recording": recording,
            "current_game_id": game_id,
            "current_file": f"{game_id}.mp4" if game_id else None,
            "recordings": recs,
            "bytes_used": camera_recordings.bytes_used(),
            "bytes_budget": camera_recordings.BUDGET_BYTES,
            "bytes_free_in_budget": camera_recordings.budget_free(),
            "headroom_bytes": camera_recordings.HEADROOM_BYTES,
            "headroom_ok": camera_recordings.headroom_ok(),
            "timestamp": iso_now(),
        }


class CameraMqtt:
    """MQTT control plane: gwent/camera/ctrl in, retained state out."""

    def __init__(self, recorder):
        self._recorder = recorder
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"gwent-camera-{os.getpid()}")
        self._client.username_pw_set(MQTT_USER, MQTT_PASS)
        # Crash LWT: mark offline (retained) so clients don't trust stale state
        self._client.will_set(
            CH_CAMERA_STATE,
            json.dumps({"online": False, "camera_on": False,
                        "recording": False, "timestamp": None}),
            qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def start(self):
        self._client.connect(MQTT_HOST, MQTT_PORT)
        self._client.loop_start()

    def stop(self):
        # Graceful: final retained state marks offline but preserves camera_on
        snap = self._recorder.snapshot()
        snap["online"] = False
        snap["recording"] = False
        self.publish_state(snap)
        self._client.loop_stop()
        self._client.disconnect()

    def publish_state(self, snap=None):
        snap = snap or self._recorder.snapshot()
        self._client.publish(CH_CAMERA_STATE, json.dumps(snap),
                             qos=1, retain=True)
        logger.info("state published: camera_on=%s recording=%s used=%.2fGB "
                    "recordings=%d", snap["camera_on"], snap["recording"],
                    snap["bytes_used"] / 1e9, len(snap["recordings"]))

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        # Subscribe in on_connect so broker reconnects re-subscribe
        logger.info("MQTT connected (%s); subscribing to %s",
                    reason_code, CH_CAMERA_CTRL)
        client.subscribe(CH_CAMERA_CTRL, qos=1)
        self.publish_state()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError) as exc:
            logger.error("bad ctrl payload on %s: %s (%r)",
                         msg.topic, exc, msg.payload[:200])
            return
        action = payload.get("action")
        game_id = payload.get("game_id")
        logger.info("ctrl received: %s", payload)
        try:
            if action == "on":
                self._recorder.set_camera(True)
            elif action == "off":
                self._recorder.set_camera(False)
            elif action == "view-on":
                self._recorder.set_live_view(True)
            elif action == "view-off":
                self._recorder.set_live_view(False)
            elif action == "record-start":
                self._recorder.record_start(game_id)
            elif action == "record-stop":
                self._recorder.record_stop()
            elif action == "save":
                self._recorder.save(game_id)
            elif action == "discard":
                self._recorder.discard(game_id)
            elif action == "evict-saved":
                bytes_needed = int(payload.get(
                    "bytes_needed", camera_recordings.HEADROOM_BYTES))
                self._recorder.evict_saved(bytes_needed)
            else:
                logger.error("unknown ctrl action: %r", action)
                return
        except Exception:
            logger.exception("ctrl action %s failed", action)
        self.publish_state()


class CameraHandler(server.BaseHTTPRequestHandler):
    # Set at startup
    picam2 = None
    output = None
    still_lock = threading.Lock()

    def log_message(self, fmt, *args):
        logger.info("%s %s", self.client_address[0], fmt % args)

    def do_GET(self):
        if self.path in ("/still", "/still/"):
            self.serve_still()
        elif self.path in ("/stream", "/stream/"):
            self.serve_stream()
        else:
            logger.warning("404 %s %s", self.client_address[0], self.path)
            self.send_error(404, "Use /still or /stream")

    def serve_still(self):
        buf = io.BytesIO()
        # capture_file is not thread-safe across concurrent requests
        with self.still_lock:
            self.picam2.capture_file(buf, format="jpeg")
        data = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_stream(self):
        logger.info("stream started for %s", self.client_address[0])
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header(
            "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
        )
        self.end_headers()
        try:
            while True:
                with self.output.condition:
                    self.output.condition.wait()
                    frame = self.output.frame
                self.wfile.write(b"--FRAME\r\n")
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            logger.info("stream ended for %s", self.client_address[0])


class CameraServer(ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    setup_logging()
    logger.info("starting: tuning=%s stream=%dx%d@%d bind=%s:%d",
                TUNING_FILE, *STREAM_SIZE, FRAMERATE, *BIND_ADDR)
    camera_recordings.ensure_dirs()

    tuning = Picamera2.load_tuning_file(TUNING_FILE)
    picam2 = Picamera2(tuning=tuning)
    picam2.configure(picam2.create_video_configuration(
        main={"size": STREAM_SIZE},
        controls={"FrameRate": FRAMERATE}))
    output = StreamingOutput()
    picam2.start_recording(MJPEGEncoder(), FileOutput(output),
                           quality=Quality.MEDIUM)
    logger.info("camera MJPEG stream started")

    recorder = RecordingController(picam2)
    camera_mqtt = CameraMqtt(recorder)
    camera_mqtt.start()

    CameraHandler.picam2 = picam2
    CameraHandler.output = output
    httpd = CameraServer(BIND_ADDR, CameraHandler)

    def shutdown(signum, _frame):
        logger.info("received %s, shutting down", signal.Signals(signum).name)
        # shutdown() must come from another thread than serve_forever()
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("stopping: finalize recording, mqtt, camera")
        recorder.record_stop()       # finalizes in-flight mp4 (stays unconfirmed)
        camera_mqtt.stop()
        picam2.stop_recording()
        picam2.close()
        logger.info("shutdown complete")


if __name__ == "__main__":
    main()
