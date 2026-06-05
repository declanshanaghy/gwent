#!/usr/bin/env bash

#############################################################################
#
# Perform all the following steps before running `make install-system`
#
#############################################################################
#
# sudo apt-get update
# sudo rpi-update
#
# Enable SPI & I2C
# sudo raspi-config
#
# sudo usermod -G sudo,gpio,spi,i2c -a ${USER}
#
# Install ssh pub key in ~/.ssh/authorized_keys
#
# no password sudo
# %sudo  ALL=(ALL) NOPASSWD: ALL
#
#############################################################################

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Download and install WiringPi from GitHub
echo "Downloading WiringPi from GitHub..."
WIRINGPI_URL="https://github.com/WiringPi/WiringPi/releases/download/3.14/wiringpi_3.14_arm64.deb"
WIRINGPI_DEB="/tmp/wiringpi_3.14_arm64.deb"

# Download the package
if command -v wget > /dev/null; then
  wget -q -O "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
    echo "Failed to download WiringPi package using wget. Trying curl..."
    if command -v curl > /dev/null; then
      curl -s -L -o "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
        echo "Error: Failed to download WiringPi package. Please check your internet connection."
        echo "If WiringPi is required, please install it manually."
      }
    else
      echo "Error: Neither wget nor curl is available. Cannot download WiringPi package."
      echo "If WiringPi is required, please install it manually."
    fi
  }
else
  if command -v curl > /dev/null; then
    curl -s -L -o "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
      echo "Error: Failed to download WiringPi package. Please check your internet connection."
      echo "If WiringPi is required, please install it manually."
    }
  else
    echo "Error: Neither wget nor curl is available. Cannot download WiringPi package."
    echo "If WiringPi is required, please install it manually."
  fi
fi

# Install the package if download was successful
if [ -f "$WIRINGPI_DEB" ]; then
  echo "Installing WiringPi from downloaded package..."
  sudo dpkg -i "$WIRINGPI_DEB" || {
    echo "Warning: Failed to install WiringPi package. Attempting to fix broken packages..."
    sudo apt --fix-broken install -y
  }

  # Clean up the downloaded file
  rm -f "$WIRINGPI_DEB"
else
  echo "WiringPi package download failed or file not found."
  echo "If WiringPi is required, please install it manually."
fi

echo "Installing just command runner..."
if ! command -v just > /dev/null; then
  sudo apt-get install -y just || {
    echo "just not in apt, installing via cargo..."
    if command -v cargo > /dev/null; then
      cargo install just
    else
      echo "Warning: Could not install just. Install manually: https://github.com/casey/just"
    fi
  }
else
  echo "just is already installed."
fi

echo "Installing Python and development packages..."
sudo apt-get install -y \
  python3-dev python3-pip python3-venv python3-pil python3-wheel \
  python3-opencv

echo "Installing build tools for native Python extensions..."
sudo apt-get install -y \
  swig i2c-tools liblgpio-dev

echo "Installing audio and display dependencies..."
sudo apt-get install -y \
  ffmpeg mpg123 \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
  mosquitto

echo "Installing kiosk display stack (greetd + cage + kitty)..."
# greetd:         minimal login manager (replaces lightdm) with autologin
# cage:           single-window Wayland kiosk compositor (wlroots)
# kitty:          terminal emulator with Kitty Graphics Protocol — required by
#                 gwent-tui for inline card image overlays via textual-image.
# python3-evdev:  reads /dev/input/event* and writes to /dev/uinput from the
#                 gwent-touch.service daemon, bridging touchscreen → wl_pointer
#                 (cage/kitty don't consume wl_touch on their own).
# fonts-*:        glyph coverage for the TUI. Liberation Mono (default
#                 monospace) lacks emoji/symbols, so faction/ability/range
#                 icons and panel glyphs render as tofu boxes without these.
#                 Noto Color Emoji = color emoji; Symbola = monochrome catch-all
#                 for misc symbols/dingbats. kitty falls back to them via
#                 fontconfig automatically.
sudo apt-get install -y greetd cage kitty python3-evdev \
  fonts-noto-color-emoji fonts-symbola
# Rebuild the fontconfig cache so kitty discovers the new fonts.
fc-cache -f >/dev/null 2>&1 || true

# Default ALSA output to 3.5mm headphone jack instead of HDMI
ASOUNDRC="${HOME}/.asoundrc"
if [ ! -f "$ASOUNDRC" ]; then
  echo "Configuring ALSA default to 3.5mm headphone jack..."
  cat > "$ASOUNDRC" << 'EOF'
# Default to 3.5mm headphone jack (card 2) instead of HDMI
defaults.pcm.card 2
defaults.ctl.card 2
EOF
else
  echo "ALSA config already exists at ${ASOUNDRC}"
fi

echo "Installing camera tooling (scripts/camera.sh)..."
# rpicam-apps: CLI capture/stream from the CSI camera module (rpicam-still/-vid)
# chafa:       best-in-class terminal image viewer; auto-detects kitty graphics
#              protocol / sixel / unicode symbols — renders --still inline
# mpv:         video player with terminal video outputs (--vo=kitty / --vo=tct)
#              — renders the --stream live feed in the console
sudo apt-get install -y rpicam-apps chafa mpv

echo "Installing camera HTTP server (nginx + picamera2)..."
# python3-picamera2: libcamera Python bindings — camera-server.py owns the
#                    camera and serves /still + /stream on 127.0.0.1:8081
# python3-paho-mqtt: MQTT control plane (gwent/camera/ctrl + retained state)
# nginx-light:       reverse proxy exposing it at 0.0.0.0:80/camera/{still,stream}
#                    and serving recordings at /camera/recordings/
sudo apt-get install -y nginx-light python3-picamera2 python3-paho-mqtt

# nginx site: replaces the stock default site (both claim default_server :80)
sudo cp ${DIR}/nginx-camera.conf /etc/nginx/sites-available/gwent-camera
sudo ln -sf ../sites-available/gwent-camera /etc/nginx/sites-enabled/gwent-camera
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# Recordings tree (world-readable so nginx can serve downloads)
mkdir -p ${DIR}/../tmp/recordings/unconfirmed ${DIR}/../tmp/recordings/saved
chmod 755 ${DIR}/../tmp ${DIR}/../tmp/recordings \
  ${DIR}/../tmp/recordings/unconfirmed ${DIR}/../tmp/recordings/saved
# ${HOME} is 700; grant ONLY www-data traverse rights (no world access) so
# nginx can reach the recordings dir for /camera/recordings/ downloads
sudo setfacl -m u:www-data:x "${HOME}"

# Recordings budget janitor: hourly cron deleting oldest unconfirmed
# recordings once usage exceeds the 10GB cap (never touches saved/)
echo "Installing camera recordings cleanup cron..."
sudo cp ${DIR}/gwent-camera-cron /etc/cron.d/gwent-camera
sudo chmod 644 /etc/cron.d/gwent-camera

# gwent-camera systemd service (picamera2 HTTP server)
sudo cp ${DIR}/gwent-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gwent-camera
sudo systemctl restart gwent-camera

echo "Installing GPIO libraries for rotary encoder support..."
sudo apt-get install -y \
  pigpio-tools python3-pigpio \
  python3-gpiozero

# Install pigpio daemon from source if pigpiod is not available
# (Debian Trixie dropped the pigpio daemon package)
if ! command -v pigpiod > /dev/null; then
  echo "pigpiod not found in system packages, building from source..."
  PIGPIO_BUILD_DIR="/tmp/pigpio-build"
  rm -rf "$PIGPIO_BUILD_DIR"
  mkdir -p "$PIGPIO_BUILD_DIR"
  cd "$PIGPIO_BUILD_DIR"
  wget -q https://github.com/joan2937/pigpio/archive/master.zip
  unzip -q master.zip
  cd pigpio-master
  make -j$(nproc)
  sudo make install
  cd /
  rm -rf "$PIGPIO_BUILD_DIR"
  echo "pigpiod built and installed from source."
fi

# Create pigpiod systemd service if it doesn't exist
if [ ! -f /etc/systemd/system/pigpiod.service ]; then
  echo "Creating pigpiod systemd service..."
  sudo tee /etc/systemd/system/pigpiod.service > /dev/null << 'EOF'
[Unit]
Description=pigpio daemon
After=local-fs.target network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/pigpiod
ExecStop=/bin/kill -SIGTERM $MAINPID

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
fi

# Enable and start the pigpio daemon
echo "Enabling and starting pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Configure mosquitto
MOSQUITTO_CONF="/etc/mosquitto/conf.d/50-listen-mqtt.conf"
if [ ! -f "$MOSQUITTO_CONF" ]; then
    echo "Configuring mosquitto..."
    sudo cp ${DIR}/50-listen-mqtt.conf $MOSQUITTO_CONF
fi

# Configure mosquitto credentials
MOSQUITTO_PASSWD="/etc/mosquitto/passwd"
if [ ! -f "$MOSQUITTO_PASSWD" ]; then
    echo "Creating mosquitto credentials (user: geralt)..."
    sudo mosquitto_passwd -b -c "$MOSQUITTO_PASSWD" geralt gwent
    sudo chmod 640 "$MOSQUITTO_PASSWD"
    sudo chown root:mosquitto "$MOSQUITTO_PASSWD"
fi

echo "Restarting mosquitto service..."
sudo systemctl restart mosquitto

# Install piper TTS and download voice models for gwent-tui announcements
echo "Installing piper TTS voice models..."
PIPER_VOICE_DIR="${HOME}/.local/share/piper-voices"
mkdir -p "${PIPER_VOICE_DIR}"

PIPER_BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_MODELS=(
  "en_US-ryan-medium"
  "en_GB-northern_english_male-medium"
  "en_GB-alan-medium"
  "en_US-joe-medium"
  "en_US-bryce-medium"
)

for model in "${PIPER_MODELS[@]}"; do
  onnx_file="${PIPER_VOICE_DIR}/${model}.onnx"
  json_file="${PIPER_VOICE_DIR}/${model}.onnx.json"

  if [ -f "${onnx_file}" ] && [ -f "${json_file}" ]; then
    echo "  ${model}: already downloaded"
    continue
  fi

  # Build the HuggingFace path from the model name
  # e.g. en_US-ryan-medium -> en/en_US/ryan/medium/en_US-ryan-medium.onnx
  lang_code="${model%%_*}"             # en
  locale="${model%%-*}"                # en_US
  rest="${model#*-}"                   # ryan-medium
  voice_name="${rest%-*}"              # ryan
  quality="${rest##*-}"                # medium
  onnx_url="${PIPER_BASE_URL}/${lang_code}/${locale}/${voice_name}/${quality}/${model}.onnx"
  json_url="${onnx_url}.json"

  echo "  ${model}: downloading (~60MB)..."
  curl -sL -o "${onnx_file}" "${onnx_url}" && \
  curl -sL -o "${json_file}" "${json_url}" && \
  echo "  ${model}: done" || \
  echo "  ${model}: download failed (non-critical)"
done

echo "System installation complete."
echo "  mosquitto:    $(systemctl is-active mosquitto)"
echo "  pigpiod:      $(systemctl is-active pigpiod)"
echo "  nginx:        $(systemctl is-active nginx)"
echo "  gwent-camera: $(systemctl is-active gwent-camera)"
