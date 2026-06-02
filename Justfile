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
gwent-stop *args:
    bash scripts/dev-server.sh gwent stop {{args}}

# Restart gwent game server
gwent-restart *args:
    bash scripts/dev-server.sh gwent restart {{args}}

# Show dev server status
status *args:
    bash scripts/dev-server.sh gwent status {{args}}

# Start all services
up *args:
    bash scripts/dev-server.sh all start {{args}}

# Stop all services
down *args:
    bash scripts/dev-server.sh all stop {{args}}

# Restart all services
restart *args:
    bash scripts/dev-server.sh all restart {{args}}

# Start gwent-tui terminal dashboard
tui *args:
    "{{tui_bin}}" {{args}}

# Touch verification — launches scripts/test-touch.py inside kitty
touch-test:
    bash scripts/test-touch.sh

# Programmatic test of the volume mixer modal (Textual Pilot, headless)
test-volume-mixer:
    "{{venv_bin}}/python" scripts/test-volume-mixer.py

# Interactive volume mixer test — drives the REAL modal on the panel.
# Requires running inside the kiosk's kitty so touch + visuals are exercised.
test-volume-mixer-ui:
    "{{venv_bin}}/python" scripts/test-volume-mixer-interactive.py

# Dump current game state (sends SIGUSR1 to gwent)
dump-state *args:
    kill -USR1 $(pgrep -f "{{venv_bin}}/gwent") 2>/dev/null || echo "gwent not running"

# Tail gwent dev log
log *args:
    tail -f /tmp/logs/gwent.log {{args}}

# === Card Utilities ==========================================================

# Validate all card JSON files
validate-cards *args:
    "{{venv_bin}}/validate-cards" {{args}}

# Read a card JSON file
read-card-file *args:
    "{{venv_bin}}/read-card-file" {{args}}

# Get a random card
random-card *args:
    "{{venv_bin}}/get-random-card" {{args}}

# Import cards from external sources
import-cards *args:
    "{{venv_bin}}/import-cards" {{args}}

# Write next card to RFID tag
write-next *args:
    "{{venv_bin}}/write-next" {{args}}

# Download Skellige cards from Witcher fandom wiki
download-skellige *args:
    "{{venv_bin}}/download-skellige-cards" {{args}}

# === Hardware Tests ==========================================================

# Read a physical RFID card
read-card *args:
    "{{venv_bin}}/read_card" {{args}}

# Write data to a physical RFID card
write-card *args:
    "{{venv_bin}}/write_card" {{args}}

# Test RFID scanner
rfid-test *args:
    "{{venv_bin}}/rfid-test" {{args}}

# Test rotary encoder (pigpio)
rotary-test *args:
    "{{venv_bin}}/rotary-pigpio" {{args}}

# === Display Tests ===========================================================

# Test SSD1306 OLED display
oled-ssd1306-test *args:
    "{{venv_bin}}/oled-ssd1306-test" {{args}}

# Test SSD1305 OLED (Pillow)
oled-ssd1305-pillow-test *args:
    "{{venv_bin}}/oled-ssd1305-pillow-test" {{args}}

# Test SSD1305 OLED (luma)
oled-ssd1305-luma-test *args:
    "{{venv_bin}}/oled-ssd1305-luma-test" {{args}}

# Test LED matrix
matrix-test *args:
    "{{venv_bin}}/matrix-test" {{args}}

# Run LED matrix marquee
matrix-marquee *args:
    "{{venv_bin}}/matrix-marquee" {{args}}

# === Diagnostics =============================================================

# Check GPIO permissions
gpio-check *args:
    "{{venv_bin}}/gpio-check" {{args}}

# Manage GPIO service
gpio-service *args:
    "{{venv_bin}}/gpio-service-manager" {{args}}

# Run MFD diagnostic
mfd-diagnostic *args:
    "{{venv_bin}}/mfd-diagnostic" {{args}}

# Run audio diagnostic
audio-diagnostic *args:
    "{{venv_bin}}/audio-diagnostic" {{args}}

# Explore TTS voices
tts-voice-explorer *args:
    "{{venv_bin}}/tts-voice-explorer" {{args}}

# Explore TTS services
tts-service-explorer *args:
    "{{venv_bin}}/tts-service-explorer" {{args}}

# === Installation ============================================================

# Full install (system + venv + app + service)
install *args:
    bash scripts/install.sh {{args}}

# Install system packages only
install-system *args:
    bash scripts/install-system.sh {{args}}

# Create Python virtualenv
install-venv *args:
    bash scripts/install-venv.sh {{args}}

# Install gwent app into venv
install-app *args:
    bash scripts/install-app.sh {{args}}

# Install gwent systemd service
install-service *args:
    bash scripts/install-service.sh {{args}}

# Install gwent-tui into venv
install-tui *args:
    "{{venv_dir}}/bin/pip" install -e software/gwent-tui {{args}}

# === Remote Deployment (Pi) ==================================================

# Rsync project to Pi
rsync *args:
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
pi-restart *args:
    ssh -i {{ssh_key}} {{deploy_user}}@{{deploy_tgt}} sudo systemctl restart gwent {{args}}

# Stream gwent service logs from Pi
pi-logs *args:
    ssh -i {{ssh_key}} {{deploy_user}}@{{deploy_tgt}} "journalctl -fu gwent" {{args}}

# Validate gwent on Pi
pi-validate *args:
    bash scripts/validate-gwent.sh {{args}}

# Deploy, restart, and validate on Pi
pi-full: deploy pi-restart pi-validate

# Run hardware tests on Pi
pi-test-hardware *args:
    RASPBERRY_PI_IP={{deploy_tgt}} DEPLOY_USER={{deploy_user}} SSH_KEY={{ssh_key}} bash scripts/deploy-and-test.sh {{args}}

# Download cards from Pi
pi-download-cards *args:
    rsync -talvx -e "ssh -i {{ssh_key}}" {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/software/data/cards/* ./software/data/cards/ {{args}}

# Upload cards to Pi
pi-upload-cards *args:
    rsync -talvx -e "ssh -i {{ssh_key}}" ./software/data/cards/* {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/software/data/cards/ {{args}}

# Download tmp directory from Pi
pi-download-tmp *args:
    rsync -talvx --exclude=gwent-sfx -e "ssh -i {{ssh_key}}" {{deploy_user}}@{{deploy_tgt}}:{{deploy_dir}}/tmp/* ./tmp/ {{args}}

# === Testing =================================================================

# Run gwent unit tests
test *args:
    "{{venv_bin}}/pytest" software/gwent {{args}}

# Run gwent tests with coverage
test-cov *args:
    "{{venv_bin}}/pytest" software/gwent --cov=gwent --cov-report=term-missing {{args}}
