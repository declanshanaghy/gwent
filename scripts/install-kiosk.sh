#!/usr/bin/env bash
#
# Configures the Pi to boot directly into a fullscreen gwent-tui kiosk:
#   greetd (autologin) -> cage (Wayland kiosk) -> kitty -> kiosk-tui.sh
#
# Idempotent: safe to re-run. Requires apt packages from install-system.sh
# (greetd, cage, kitty).

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "${DIR}/install-vars.sh"

echo "Installing gwent kiosk..."

# Sanity: required commands must be installed already.
# greetd lives in /usr/sbin which isn't in non-root PATH; check the file directly.
for cmd in cage kitty just; do
    if ! command -v "$cmd" > /dev/null; then
        echo "  ERROR: '$cmd' not found in PATH. Run install-system.sh first." >&2
        exit 1
    fi
done
if [ ! -x /usr/sbin/greetd ]; then
    echo "  ERROR: /usr/sbin/greetd not installed. Run install-system.sh first." >&2
    exit 1
fi
# evdev required for the touch bridge.
if ! /usr/bin/python3 -c "import evdev" 2>/dev/null; then
    echo "  ERROR: python3-evdev not installed. Run install-system.sh first." >&2
    exit 1
fi

# 1. Wrapper script — make executable
chmod +x "${DIR}/kiosk-tui.sh"
chmod +x "${DIR}/touch-to-mouse.py"

# 1b. Touch bridge systemd service — translates DSI touchscreen events into
# a virtual mouse so cage/kitty/Textual receive clicks. Must start BEFORE
# greetd so cage discovers the virtual pointer at compositor startup.
sudo install -m 644 "${DIR}/gwent-touch.service" /etc/systemd/system/gwent-touch.service
sudo systemctl daemon-reload
sudo systemctl enable gwent-touch.service
echo "  gwent-touch.service installed and enabled"

# 2. Kitty config — per-user
KITTY_CFG_DIR="${HOME}/.config/kitty"
mkdir -p "${KITTY_CFG_DIR}"
cp "${DIR}/kiosk-kitty.conf" "${KITTY_CFG_DIR}/kitty.conf"
echo "  kitty config -> ${KITTY_CFG_DIR}/kitty.conf"

# 3. greetd config — system-wide
sudo install -m 644 "${DIR}/greetd-config.toml" /etc/greetd/config.toml
echo "  greetd config -> /etc/greetd/config.toml"

# 4. Disable lightdm if present, enable greetd
if systemctl list-unit-files lightdm.service > /dev/null 2>&1; then
    if systemctl is-enabled --quiet lightdm.service 2>/dev/null; then
        echo "  Disabling lightdm.service..."
        sudo systemctl disable lightdm.service
    fi
fi
sudo systemctl enable greetd.service

# 4b. Free vt1 from getty so greetd can own it.
# raspi-config's "console autologin" leaves a drop-in that auto-logs into
# tty1 via agetty — it grabs vt1 before greetd can, leaving the panel
# showing a bash prompt instead of the kiosk.
AUTOLOGIN_DROPIN="/etc/systemd/system/getty@tty1.service.d/autologin.conf"
if [ -f "${AUTOLOGIN_DROPIN}" ]; then
    echo "  Removing leftover getty@tty1 autologin override..."
    sudo rm -f "${AUTOLOGIN_DROPIN}"
    sudo rmdir --ignore-fail-on-non-empty /etc/systemd/system/getty@tty1.service.d 2>/dev/null || true
fi
if systemctl is-enabled --quiet getty@tty1.service 2>/dev/null; then
    echo "  Disabling getty@tty1 (greetd owns vt1 now; use Ctrl+Alt+F2 for a console)..."
    sudo systemctl disable getty@tty1.service
fi

# 5. greetd requires graphical.target
sudo systemctl set-default graphical.target > /dev/null

echo
echo "Kiosk install complete. Reboot to switch over:"
echo "  sudo reboot"
echo
echo "After reboot:"
echo "  - DSI panel auto-shows gwent-tui (no login)"
echo "  - Ctrl+Alt+F2 for a maintenance getty"
echo "  - Rollback: sudo systemctl disable greetd && sudo systemctl enable lightdm && sudo reboot"
