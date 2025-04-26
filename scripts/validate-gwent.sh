#!/usr/bin/env bash

# Script to validate that gwent is running correctly on the Raspberry Pi
# This script checks if the gwent service is running and if the necessary components are working

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
RASPBERRY_PI_IP=${RASPBERRY_PI_IP:-"192.168.1.225"}
PI_USER=${DEPLOY_USER:-"dshanaghy"}
SSH_KEY=${SSH_KEY:-"~/.ssh/id_rsa"}

print_message "Validating gwent on Raspberry Pi (${RASPBERRY_PI_IP})..."

# Step 1: Check if the gwent service is running
print_message "Checking if gwent service is running..."
SERVICE_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active gwent.service" 2>/dev/null || echo "inactive")

if [ "${SERVICE_STATUS}" = "active" ]; then
    print_success "Gwent service is running."
else
    print_error "Gwent service is not running. Status: ${SERVICE_STATUS}"
    print_message "Attempting to start the service..."
    ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl start gwent.service" || {
        print_error "Failed to start gwent service."
        exit 1
    }
    
    # Check again after starting
    SERVICE_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active gwent.service" 2>/dev/null || echo "inactive")
    if [ "${SERVICE_STATUS}" = "active" ]; then
        print_success "Gwent service started successfully."
    else
        print_error "Failed to start gwent service. Please check the logs."
        exit 1
    fi
fi

# Step 2: Check if the MQTT broker is running
print_message "Checking if MQTT broker is running..."
MQTT_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active mosquitto.service" 2>/dev/null || echo "inactive")

if [ "${MQTT_STATUS}" = "active" ]; then
    print_success "MQTT broker is running."
else
    print_warning "MQTT broker is not running. Status: ${MQTT_STATUS}"
    print_message "Attempting to start the MQTT broker..."
    ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl start mosquitto.service" || {
        print_error "Failed to start MQTT broker."
        exit 1
    }
    
    # Check again after starting
    MQTT_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active mosquitto.service" 2>/dev/null || echo "inactive")
    if [ "${MQTT_STATUS}" = "active" ]; then
        print_success "MQTT broker started successfully."
    else
        print_warning "Failed to start MQTT broker. This may affect gwent functionality."
    fi
fi

# Step 3: Check if the pigpio daemon is running
print_message "Checking if pigpio daemon is running..."
PIGPIO_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active pigpiod.service" 2>/dev/null || echo "inactive")

if [ "${PIGPIO_STATUS}" = "active" ]; then
    print_success "pigpio daemon is running."
else
    print_warning "pigpio daemon is not running. Status: ${PIGPIO_STATUS}"
    print_message "Attempting to start the pigpio daemon..."
    ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "sudo systemctl start pigpiod.service" || {
        print_error "Failed to start pigpio daemon."
        exit 1
    }
    
    # Check again after starting
    PIGPIO_STATUS=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "systemctl is-active pigpiod.service" 2>/dev/null || echo "inactive")
    if [ "${PIGPIO_STATUS}" = "active" ]; then
        print_success "pigpio daemon started successfully."
    else
        print_warning "Failed to start pigpio daemon. This may affect rotary encoder functionality."
    fi
fi

# Step 4: Check if the MFD component is working
print_message "Checking MFD component..."
print_message "Running MFD diagnostic tool..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.mfd_diagnostic --non-interactive" > /dev/null 2>&1 || {
    print_warning "MFD diagnostic tool reported issues. You may want to run 'make mfd-diagnostic' for detailed diagnostics."
}

# Step 5: Check gwent logs for errors
print_message "Checking gwent logs for errors..."
ERROR_COUNT=$(ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "journalctl -u gwent.service -n 50 | grep -c 'ERROR'" 2>/dev/null || echo "0")

if [ "${ERROR_COUNT}" -eq "0" ]; then
    print_success "No recent errors found in gwent logs."
else
    print_warning "Found ${ERROR_COUNT} errors in recent gwent logs."
    print_message "Recent errors:"
    ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "journalctl -u gwent.service -n 50 | grep 'ERROR'" || true
fi

print_success "Gwent validation completed!"
print_message "To view detailed logs, run: ssh ${PI_USER}@${RASPBERRY_PI_IP} 'journalctl -fu gwent.service'"