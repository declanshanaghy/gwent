#!/usr/bin/env bash

# Script to deploy gwent package to Raspberry Pi
# This script builds the package and provides instructions for manual deployment

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

# Raspberry Pi configuration
RASPBERRY_PI_IP=${RASPBERRY_PI_IP:-"192.168.1.225"}
PI_USER="dshanaghy"
PI_HOME="/home/${PI_USER}"
VENV_DIR="${PI_HOME}/${VENV_NAME}"
SSH_KEY="~/.ssh/id_rsa"

print_message "Starting gwent package deployment to Raspberry Pi (${RASPBERRY_PI_IP})..."

# Step 0: Initialize and update Git submodules
print_message "Initializing and updating Git submodules..."
cd "${DIR}/.."
git submodule init
git submodule update
print_success "Git submodules initialized and updated."

# Step 1: Build the gwent package
print_message "Building gwent package..."
cd "${DIR}/../software/gwent"
python3 setup.py sdist
PACKAGE_PATH=$(ls -t dist/gwent-*.tar.gz | head -1)
PACKAGE_NAME=$(basename ${PACKAGE_PATH})
FULL_PACKAGE_PATH="${DIR}/../software/gwent/${PACKAGE_PATH}"
cd "${DIR}/.."
print_success "Package built: ${FULL_PACKAGE_PATH}"

# Step 2: Ensure SSH agent is running
print_message "Ensuring SSH agent is running..."
eval $(ssh-agent -s) > /dev/null
ssh-add ${SSH_KEY} 2>/dev/null || print_warning "Could not add SSH key. You may need to enter your password."

# Step 3: Copy the package to the Raspberry Pi
print_message "Copying package to Raspberry Pi..."
scp -i ${SSH_KEY} ${FULL_PACKAGE_PATH} ${PI_USER}@${RASPBERRY_PI_IP}:~/ || {
    print_error "Failed to copy package to Raspberry Pi."
    exit 1
}
print_success "Package copied to Raspberry Pi."

# Step 4: Copy and install local dependencies first
print_message "Copying local dependencies to Raspberry Pi..."
scp -i ${SSH_KEY} -r ${DIR}/../software/gaugette ${DIR}/../software/MFRC522-python ${PI_USER}@${RASPBERRY_PI_IP}:~/ || {
    print_error "Failed to copy local dependencies to Raspberry Pi."
    exit 1
}
print_success "Local dependencies copied to Raspberry Pi."

print_message "Installing local dependencies on Raspberry Pi..."
# Install gaugette with pip
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source ${VENV_DIR}/bin/activate && pip install -e ~/gaugette" || {
    print_error "Failed to install gaugette on Raspberry Pi."
    exit 1
}

# For MFRC522-python, just make sure it's in the Python path
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "mkdir -p ${VENV_DIR}/lib/python3.*/site-packages/ && ln -sf ~/MFRC522-python/MFRC522 ${VENV_DIR}/lib/python3.*/site-packages/" || {
    print_error "Failed to link MFRC522-python on Raspberry Pi."
    exit 1
}
print_success "Local dependencies installed on Raspberry Pi."

# Step 5: Install pygame using apt-get
print_message "Installing pygame using apt-get..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo apt-get update && sudo apt-get install -y python3-pygame" || {
    print_error "Failed to install pygame using apt-get."
    exit 1
}
print_success "Pygame installed using apt-get."

# Step 6: Install the gwent package on the Raspberry Pi
print_message "Installing gwent package on Raspberry Pi..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source ${VENV_DIR}/bin/activate && pip install --upgrade ~/${PACKAGE_NAME}" || {
    print_error "Failed to install gwent package on Raspberry Pi."
    exit 1
}
print_success "Gwent package installed on Raspberry Pi."

# Step 5: Restart the gwent service
print_message "Restarting gwent service..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl restart gwent.service" || {
    print_error "Failed to restart gwent service."
    exit 1
}
print_success "Gwent service restarted."

# Step 6: Check the service status
print_message "Checking service status..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl status gwent.service --no-pager" || {
    print_warning "Gwent service may not be running properly."
}

print_success "Deployment completed successfully!"
print_message "To validate that gwent is running correctly, run: make validate"