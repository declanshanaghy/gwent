# Gwent Companion — Justfile
# Run `just` to see all available recipes

set dotenv-load
set positional-arguments

# --- Configuration -----------------------------------------------------------

venv_dir   := env("VENV_DIR", home_dir() / "gwent-venv")
venv_bin   := venv_dir / "bin"
gwent_bin  := venv_bin / "gwent"
tui_bin    := venv_bin / "gwent-tui"

deploy_user := env("DEPLOY_USER", "dshanaghy")
deploy_tgt  := env("RASPBERRY_PI_IP", "192.168.1.225")
ssh_key     := env("SSH_KEY", "~/.ssh/id_rsa")
deploy_dir  := "~/gwent"

# --- Default / Help ----------------------------------------------------------

# List all recipes
default:
    @just --list --unsorted

# === Development =============================================================

# Start gwent game server (dev mode)
gwent *args:
    bash scripts/dev-server.sh gwent start {{args}}

# Stop gwent game server
gwent-stop:
    bash scripts/dev-server.sh gwent stop

# Restart gwent game server
gwent-restart *args:
    bash scripts/dev-server.sh gwent restart {{args}}

# Show dev server status
status:
    bash scripts/dev-server.sh gwent status

# Start glory-gate React frontend
glory-gate:
    bash scripts/dev-server.sh glory-gate start

# Stop glory-gate
glory-gate-stop:
    bash scripts/dev-server.sh glory-gate stop

# Start all services (gwent + glory-gate)
up *args:
    bash scripts/dev-server.sh all start {{args}}

# Stop all services
down:
    bash scripts/dev-server.sh all stop

# Restart all services
restart *args:
    bash scripts/dev-server.sh all restart {{args}}

# Start gwent-tui terminal dashboard
tui:
    "{{tui_bin}}"

# Dump current game state (sends SIGUSR1 to gwent)
dump-state:
    kill -USR1 $(pgrep -f "{{venv_bin}}/gwent") 2>/dev/null || echo "gwent not running"

# Tail gwent dev log
log:
    tail -f /tmp/logs/gwent.log

# Tail glory-gate dev log
log-glory-gate:
    tail -f /tmp/logs/glory-gate.log

# === Card Utilities ==========================================================

# Validate all card JSON files
validate-cards:
    "{{venv_bin}}/validate-cards"

# Read a card JSON file
read-card-file:
    "{{venv_bin}}/read-card-file"

# Get a random card
random-card:
    "{{venv_bin}}/get-random-card"

# Import cards from external sources
import-cards:
    "{{venv_bin}}/import-cards"

# Write next card to RFID tag
write-next *args:
    "{{venv_bin}}/write-next" {{args}}

# Download Skellige cards from Witcher fandom wiki
download-skellige:
    "{{venv_bin}}/download-skellige-cards"

# === Hardware Tests ==========================================================

# Read a physical RFID card
read-card:
    "{{venv_bin}}/read_card"

# Write data to a physical RFID card
write-card file:
    "{{venv_bin}}/write_card" {{file}}

# Test RFID scanner
rfid-test:
    "{{venv_bin}}/rfid-test"

# Test rotary encoder (pigpio)
rotary-test:
    "{{venv_bin}}/rotary-pigpio"

# === Display Tests ===========================================================

# Test SSD1306 OLED display
oled-ssd1306-test:
    "{{venv_bin}}/oled-ssd1306-test"

# Test SSD1305 OLED (Pillow)
oled-ssd1305-pillow-test:
    "{{venv_bin}}/oled-ssd1305-pillow-test"

# Test SSD1305 OLED (luma)
oled-ssd1305-luma-test:
    "{{venv_bin}}/oled-ssd1305-luma-test"

# Test LED matrix
matrix-test:
    "{{venv_bin}}/matrix-test"

# Run LED matrix marquee
matrix-marquee:
    "{{venv_bin}}/matrix-marquee"

# === Diagnostics =============================================================

# Check GPIO permissions
gpio-check:
    "{{venv_bin}}/gpio-check"

# Manage GPIO service
gpio-service action="start":
    "{{venv_bin}}/gpio-service-manager" --action {{action}}

# Run MFD diagnostic
mfd-diagnostic:
    "{{venv_bin}}/mfd-diagnostic"

# Run audio diagnostic
audio-diagnostic:
    "{{venv_bin}}/audio-diagnostic"

# Explore TTS voices
tts-voice-explorer:
    "{{venv_bin}}/tts-voice-explorer"

# Explore TTS services
tts-service-explorer:
    "{{venv_bin}}/tts-service-explorer"

# === Installation ============================================================

# Full install (system + venv + app + service)
install:
    bash scripts/install.sh

# Install system packages only
install-system:
    bash scripts/install-system.sh

# Create Python virtualenv
install-venv:
    bash scripts/install-venv.sh

# Install gwent app into venv
install-app:
    bash scripts/install-app.sh

# Install gwent systemd service
install-service:
    bash scripts/install-service.sh

# Install gwent-tui into venv
install-tui:
    "{{venv_dir}}/bin/pip" install -e software/gwent-tui

# === Remote Deployment (Pi) ==================================================

# Rsync project to Pi
rsync:
    @echo "rsync to {{deploy_tgt}}"
    rsync -talvx --delete \
        --exclude=software/data/cards \
        --exclude=tmp \
        --exclude='*.pyc' \
        --exclude=software/gwent/.eggs \
        --exclude=.git \
        --exclude='*.egg-info' \
        --exclude=__pycache__ \
        -e "ssh -i {{ssh_key}}" . {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/

# Deploy to Pi (rsync + install)
deploy: rsync
    ssh -i {{ssh_key}} {{deploy_user}}@{{deploy_tgt}} bash -c {{deploy_dir}}/scripts/install-app.sh

# Restart gwent service on Pi
pi-restart:
    ssh -i {{ssh_key}} {{deploy_user}}@{{deploy_tgt}} sudo systemctl restart gwent

# Stream gwent service logs from Pi
pi-logs:
    ssh -i {{ssh_key}} {{deploy_user}}@{{deploy_tgt}} "journalctl -fu gwent"

# Validate gwent on Pi
pi-validate:
    bash scripts/validate-gwent.sh

# Deploy, restart, and validate on Pi
pi-full: deploy pi-restart pi-validate

# Run hardware tests on Pi
pi-test-hardware:
    RASPBERRY_PI_IP={{deploy_tgt}} DEPLOY_USER={{deploy_user}} SSH_KEY={{ssh_key}} bash scripts/deploy-and-test.sh

# Download cards from Pi
pi-download-cards:
    rsync -talvx -e "ssh -i {{ssh_key}}" {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/software/data/cards/* ./software/data/cards/

# Upload cards to Pi
pi-upload-cards:
    rsync -talvx -e "ssh -i {{ssh_key}}" ./software/data/cards/* {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/software/data/cards/

# Download tmp directory from Pi
pi-download-tmp:
    rsync -talvx --exclude=gwent-sfx -e "ssh -i {{ssh_key}}" {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/tmp/* ./tmp/

# === Testing =================================================================

# Run gwent unit tests
test *args:
    "{{venv_bin}}/pytest" software/gwent {{args}}

# Run gwent tests with coverage
test-cov:
    "{{venv_bin}}/pytest" software/gwent --cov=gwent --cov-report=term-missing
