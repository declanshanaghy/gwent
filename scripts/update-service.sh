#!/usr/bin/env bash

# Script to update the gwent.service file on the Raspberry Pi

set -e  # Exit on error

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[UPDATE]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Load environment variables
source "${DIR}/install-vars.sh"

# Check if the service file exists in the scripts directory
if [ ! -f "${DIR}/gwent.service" ]; then
    print_error "Service file not found in ${DIR}/gwent.service"
    exit 1
fi

# Check if the service is already installed
if [ -f "/etc/systemd/system/gwent.service" ]; then
    print_message "Updating existing gwent service..."
else
    print_message "Installing new gwent service..."
fi

# Install or update the service file and restart the service
print_message "Installing and restarting the service..."
sudo cp "${DIR}/gwent.service" /etc/systemd/system/gwent.service && sudo systemctl daemon-reload && sudo systemctl restart gwent.service

# Check the service status
print_message "Checking service status..."
sudo systemctl status gwent.service --no-pager

# Check if the environment variable is set
print_message "Checking environment variables..."
sudo systemctl show gwent.service -p Environment

# Check if the service is enabled to start at boot
if sudo systemctl is-enabled gwent.service &>/dev/null; then
    print_message "Service is already enabled to start at boot"
else
    print_message "Enabling service to start at boot..."
    sudo systemctl enable gwent.service
fi

print_success "Service updated successfully!"