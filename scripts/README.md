# 🛠️ Gwent Scripts Collection

This directory contains scripts for development, deployment, and maintenance of the Gwent project. They automate common tasks and provide utilities for working with the hardware and software components.

## 🚀 Installation Scripts

| Script | Description |
|--------|-------------|
| `install.sh` | Main installer that orchestrates the system, venv, app, service, and kiosk steps |
| `install-system.sh` | System dependencies + hardware interfaces; installs nginx-light, picamera2, paho-mqtt, rpicam-apps, the camera service, nginx site, recordings cron |
| `install-venv.sh` | Creates the Python virtualenv (`/home/dshanaghy/gwent-venv/`) |
| `install-app.sh` | Installs the Gwent application and its Python dependencies |
| `install-service.sh` | Installs/enables the `gwent` systemd service |
| `install-kiosk.sh` | Sets up the touchscreen kiosk (greetd → cage → kitty → gwent-tui) + `gwent-touch` evdev bridge |
| `install-vars.sh` | Shared variables sourced by the other install scripts |

## 📦 Deployment Scripts

| Script | Description |
|--------|-------------|
| `deploy-and-test.sh` | Deploys the app and runs post-deploy checks |
| `validate-gwent.sh` | Validates that the `gwent` service is running correctly |
| `dev-server.sh` | Runs a server (e.g. `gwent`) locally for dev with file logging |

## 🔧 System Configuration

| File | Description |
|------|-------------|
| `gwent.service` | Systemd unit for the game server (sets `GWENT_DISABLE_MFD=true`) |
| `gwent-camera.service` | Systemd unit for the camera server (`camera-server.py`, system python3) |
| `gwent-touch.service` | Systemd unit for the touchscreen → mouse evdev bridge |
| `greetd-config.toml` | greetd autologin config that launches the kiosk |
| `kiosk-kitty.conf` / `kiosk-tui.sh` | kitty terminal config + launcher for the `gwent-tui` kiosk |
| `nginx-camera.conf` | nginx `:80` site reverse-proxying `/camera/{still,stream,recordings/}` |
| `gwent-camera-cron` / `50-listen-mqtt.conf` | Hourly recordings-cleanup cron + mosquitto listener drop-in |

## 📷 Camera Scripts

| Script | Description |
|--------|-------------|
| `camera-server.py` | picamera2 HTTP + MQTT server; owns the NoIR camera, MJPEG stream, stills, and H.264 game recordings |
| `camera_recordings.py` | Pure-stdlib recordings manager (list/evict/save, 10 GiB budget math) shared by the server + cron |
| `camera-recordings-cleanup.{py,sh}` | Hourly janitor enforcing the 10 GiB cap (deletes oldest unconfirmed only) |
| `camera.sh` | Ad-hoc CLI: `--still` (rpicam-still + chafa) / `--stream` (rpicam-vid + mpv). Fails while `gwent-camera` holds the camera |

## 🃏 Card & Tooling Scripts

| Script | Description |
|--------|-------------|
| `capture-cards.py` | Capture card photos for identification |
| `id-and-chip-card.py` | Identify a physical card and write its RFID chip |
| `gemini.py` | Gemini API helper used by card/image tooling |

## 🧪 Testing Scripts

| Script | Description |
|--------|-------------|
| `validate-gwent.sh` | Service + install validation |
| `test-touch.{py,sh}` | Touchscreen / evdev bridge tests |
| `test-volume-mixer.py` / `test-volume-mixer-interactive.py` | Audio mixer tests |
| `touch-to-mouse.py` | evdev touch → mouse translator (used by `gwent-touch.service`) |

## 🎮 Using the Scripts

Most scripts run directly from the command line:

```bash
# Full install
./scripts/install.sh

# Validate a running install
bash scripts/validate-gwent.sh

# Run a dev server with logging
bash scripts/dev-server.sh gwent start

# Ad-hoc camera still (stop gwent-camera first)
sudo systemctl stop gwent-camera && bash scripts/camera.sh --still
```

Several steps are also available through Makefile targets (`make install`, `make install-system`, `make install-app`, etc.).

> Note: the Makefile still carries legacy `rotary-*` / `oled-test` / `mfd-*` targets for the removed OLED + rotary hardware. Those devices are gone; the drivers remain in the tree but are disabled (`GWENT_DISABLE_MFD=true`).

## 🔍 Font Resources

The `fonts/` subdirectory contains font files used to render text on the IS31FL3731 LED matrices and in TUI assets:

- `C&C Red Alert [INET].ttf`: Red Alert font for game displays
- `ChiKareGo.ttf`: Pixel font
- `FreePixel.ttf`: Free pixel font for general text
- `pixelmix.ttf`: Pixel font
- And several others for different display purposes
