#!/usr/bin/env bash

# This script installs or updates the gwent systemd service

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

echo "Installing gwent systemd service..."

# Copy the service file to the systemd directory
sudo cp ${DIR}/gwent.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Check if the service is already enabled
if systemctl is-enabled --quiet gwent.service; then
    echo "Restarting gwent service..."
    sudo systemctl restart gwent.service
else
    echo "Enabling and starting gwent service..."
    sudo systemctl enable gwent.service
    sudo systemctl start gwent.service
fi

echo "Gwent service installation complete."
echo "Service status:"
systemctl status gwent.service --no-pager

# Show logs
echo "Recent logs:"
journalctl -u gwent.service -n 10 --no-pager