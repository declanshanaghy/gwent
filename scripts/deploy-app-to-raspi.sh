#!/usr/bin/env bash

# Script to deploy only the gwent application to Raspberry Pi
# This script syncs the code to the Pi and runs it in place without installation
# System dependencies should be installed separately using install-system.sh

set -e  # Exit on error

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
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

# Set PI_HOME based on DEPLOY_USER
PI_HOME="/home/${DEPLOY_USER}"

print_message "Starting gwent application deployment to Raspberry Pi (${DEPLOY_TGT})..."

# The rsync is already done by the Makefile before calling this script
print_message "Code has been synced to the Raspberry Pi via rsync."

# Install the application using install-app.sh
print_message "Installing the application using install-app.sh..."
print_message "You may be prompted for the password for ${DEPLOY_USER}@${DEPLOY_TGT}"
ssh -o StrictHostKeyChecking=no -o BatchMode=no ${DEPLOY_USER}@${DEPLOY_TGT} "cd ${DEPLOY_DIR} && bash ${DEPLOY_DIR}/scripts/install-app.sh" || {
    print_error "Failed to install application on Raspberry Pi."
    exit 1
}
print_success "Application installed on Raspberry Pi."

# Ensure PYTHONPATH is set up correctly in the service file
print_message "Ensuring service file is configured to run gwent in place..."
print_message "You may be prompted for the password for ${DEPLOY_USER}@${DEPLOY_TGT}"
ssh -o StrictHostKeyChecking=no -o BatchMode=no ${DEPLOY_USER}@${DEPLOY_TGT} "
    SERVICE_FILE='/etc/systemd/system/gwent.service'
    if [ -f \$SERVICE_FILE ]; then
        # Check if Environment=PYTHONPATH line exists
        if ! grep -q 'Environment=PYTHONPATH=' \$SERVICE_FILE; then
            echo 'Adding PYTHONPATH to service file...'
            sudo sed -i '/\\[Service\\]/a Environment=PYTHONPATH=${DEPLOY_DIR}/software' \$SERVICE_FILE
            sudo systemctl daemon-reload
        else
            # Update existing PYTHONPATH line
            echo 'Updating PYTHONPATH in service file...'
            sudo sed -i 's|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=${DEPLOY_DIR}/software|g' \$SERVICE_FILE
            sudo systemctl daemon-reload
        fi
        
        # Ensure ExecStart is using python -m gwent.game.main
        if ! grep -q 'ExecStart=.*bin/python -m gwent.game.main' \$SERVICE_FILE; then
            echo 'Updating ExecStart to use python module directly...'
            sudo sed -i 's|ExecStart=.*|ExecStart=${VENV_DIR}/bin/python -m gwent.game.main|g' \$SERVICE_FILE
            sudo systemctl daemon-reload
        fi
    else
        echo 'Service file not found. Please install the service first.'
        exit 1
    fi
" || {
    print_error "Failed to configure service file on Raspberry Pi."
    exit 1
}
print_success "Service file configured to run gwent in place."

# Step 5: Restart the gwent service
print_message "Restarting gwent service..."
print_message "You may be prompted for the password for ${DEPLOY_USER}@${DEPLOY_TGT}"
ssh -o StrictHostKeyChecking=no -o BatchMode=no ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl restart gwent.service" || {
    print_error "Failed to restart gwent service."
    exit 1
}
print_success "Gwent service restarted."

# Step 6: Check the service status
print_message "Checking service status..."
print_message "You may be prompted for the password for ${DEPLOY_USER}@${DEPLOY_TGT}"
ssh -o StrictHostKeyChecking=no -o BatchMode=no ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl status gwent.service --no-pager" || {
    print_warning "Gwent service may not be running properly."
}

print_success "Application deployment completed successfully!"