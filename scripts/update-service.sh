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

# Raspberry Pi configuration
PI_USER=${DEPLOY_USER:-"dshanaghy"}
SSH_KEY=${SSH_KEY:-"~/.ssh/id_rsa"}
DEPLOY_TGT=${RASPBERRY_PI_IP:-"192.168.1.225"}

print_message "Updating gwent.service on Raspberry Pi (${DEPLOY_TGT})..."

# Copy the service file to the Raspberry Pi
print_message "Copying gwent.service to Raspberry Pi..."
scp -i ${SSH_KEY} ${DIR}/gwent.service ${PI_USER}@${DEPLOY_TGT}:~/gwent.service

# Install the service file and restart the service
print_message "Installing and restarting the service..."
ssh -i ${SSH_KEY} ${PI_USER}@${DEPLOY_TGT} "sudo cp ~/gwent.service /etc/systemd/system/gwent.service && sudo systemctl daemon-reload && sudo systemctl restart gwent.service"

# Check the service status
print_message "Checking service status..."
ssh -i ${SSH_KEY} ${PI_USER}@${DEPLOY_TGT} "sudo systemctl status gwent.service --no-pager"

# Check if the environment variable is set
print_message "Checking environment variables..."
ssh -i ${SSH_KEY} ${PI_USER}@${DEPLOY_TGT} "sudo systemctl show gwent.service -p Environment"

print_success "Service updated successfully!"