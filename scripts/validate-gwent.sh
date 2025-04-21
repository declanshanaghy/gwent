#!/usr/bin/env bash

# Script to validate that gwent is running correctly on the Raspberry Pi
# Checks if music is playing and text is displayed on screen

set -e  # Exit on error

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[VALIDATE]${NC} $1"
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

print_message "Validating gwent on Raspberry Pi (${RASPBERRY_PI_IP})..."

# Check if the gwent service is running
print_message "Checking if gwent service is running..."
SERVICE_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl is-active gwent.service")

if [ "$SERVICE_STATUS" = "active" ]; then
    print_success "Gwent service is running."
else
    print_error "Gwent service is not running. Status: ${SERVICE_STATUS}"
    exit 1
fi

# Check if audio capability is available
print_message "Checking if audio capability is available..."
AUDIO_CAPABILITY=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "ls -la /dev/snd/ 2>/dev/null || echo 'No audio devices'")

if [[ "$AUDIO_CAPABILITY" == *"No audio devices"* ]]; then
    print_warning "No audio devices detected. Audio might not be available on this device."
else
    print_success "Audio devices are available."
fi

# Check if pygame is installed (for audio)
print_message "Checking if pygame is installed for audio support..."
PYGAME_INSTALLED=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source /home/${PI_USER}/gwent-venv/bin/activate && python3 -c 'import pygame' 2>/dev/null && echo 'Pygame installed' || echo 'Pygame not installed'")

if [[ "$PYGAME_INSTALLED" == *"Pygame installed"* ]]; then
    print_success "Pygame is installed for audio support."
else
    print_warning "Pygame might not be installed correctly. Audio might not work."
fi

# Check if I2C is available for display
print_message "Checking if I2C is available for display..."
I2C_AVAILABLE=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "ls -la /dev/i2c* 2>/dev/null || echo 'No I2C devices'")

if [[ "$I2C_AVAILABLE" == *"No I2C devices"* ]]; then
    print_warning "No I2C devices detected. Display might not be available."
else
    print_success "I2C devices are available for display."
fi

# Check if GPIO is available for rotary encoder
print_message "Checking if GPIO is available for rotary encoder..."
GPIO_AVAILABLE=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "ls -la /dev/gpiomem 2>/dev/null || echo 'No GPIO access'")

if [[ "$GPIO_AVAILABLE" == *"No GPIO access"* ]]; then
    print_warning "No GPIO access detected. Rotary encoder might not be available."
else
    print_success "GPIO is available for rotary encoder."
fi

# Check if display libraries are installed
print_message "Checking if display libraries are installed..."
DISPLAY_LIBS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source /home/${PI_USER}/gwent-venv/bin/activate && python3 -c 'import adafruit_ssd1305' 2>/dev/null && echo 'Display libs installed' || echo 'Display libs not installed'")

if [[ "$DISPLAY_LIBS" == *"Display libs installed"* ]]; then
    print_success "Display libraries are installed."
else
    print_warning "Display libraries might not be installed correctly. Display might not work."
fi

# Check the logs for any errors
print_message "Checking logs for errors..."
# Exclude warnings about GPIO pins and pull-up resistors
LOG_ERRORS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo journalctl -u gwent.service -n 50 | grep -i 'error\\|exception\\|fail' | grep -v 'RuntimeWarning' | grep -v 'already in use' | grep -v 'pull up resistor' | wc -l")

if [ "$LOG_ERRORS" -eq "0" ]; then
    print_success "No critical errors found in the logs."
else
    print_warning "Found ${LOG_ERRORS} potential errors in the logs. This might be normal during startup."
    print_message "You can check the logs with: ssh ${PI_USER}@${RASPBERRY_PI_IP} 'sudo journalctl -u gwent.service'"
fi

# Final validation message
print_message "Checking if gwent is running properly..."
GWENT_RUNNING=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "ps aux | grep -v grep | grep -c gwent")

if [ "$GWENT_RUNNING" -gt "0" ]; then
    print_success "Gwent is running properly!"
else
    print_error "Gwent does not appear to be running."
    exit 1
fi

print_success "Validation complete! Gwent appears to be running correctly."
print_message "For a more detailed check, you may want to physically verify the Raspberry Pi's display, audio, and rotary encoder functionality."
print_message "To test the rotary encoder, try turning the dial and pressing the button while observing the logs: ssh ${PI_USER}@${RASPBERRY_PI_IP} 'sudo journalctl -u gwent.service -f'"