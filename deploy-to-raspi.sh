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

# Step 1: Build the gwent package
print_message "Building gwent package..."
cd "${DIR}/software/gwent"
python3 setup.py sdist
PACKAGE_PATH=$(ls -t dist/gwent-*.tar.gz | head -1)
PACKAGE_NAME=$(basename ${PACKAGE_PATH})
cd "${DIR}"
print_success "Package built: ${PACKAGE_PATH}"

# Step 2: Provide instructions for manual deployment
print_message "To deploy the package to your Raspberry Pi, follow these steps:"
echo ""
echo "1. Ensure SSH agent is running and has the correct key:"
echo "   eval \$(ssh-agent -s)"
echo "   ssh-add ${SSH_KEY}"
echo ""
echo "2. Copy the package to the Raspberry Pi:"
echo "   scp -i ${SSH_KEY} ${PACKAGE_PATH} ${PI_USER}@${RASPBERRY_PI_IP}:~/"
echo ""
echo "3. SSH into the Raspberry Pi:"
echo "   ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP}"
echo ""
echo "4. Install the package on the Raspberry Pi:"
echo "   source ${VENV_DIR}/bin/activate"
echo "   pip install --upgrade ~/${PACKAGE_NAME}"
echo ""
echo "5. Restart the gwent service:"
echo "   sudo systemctl restart gwent.service"
echo ""
echo "6. Check the service status:"
echo "   sudo systemctl status gwent.service"
echo ""

print_success "Deployment instructions prepared. Follow the steps above to complete the deployment."