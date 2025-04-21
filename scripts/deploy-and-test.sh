#!/usr/bin/env bash

# Script to deploy gwent package to Raspberry Pi and run hardware tests
# This script builds the package, deploys it, and runs the hardware tests

set -e  # Exit on error

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[DEPLOY-TEST]${NC} $1"
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
PI_HOME="/home/${PI_USER}"
VENV_DIR="${PI_HOME}/${VENV_NAME}"
SSH_KEY=${SSH_KEY:-"~/.ssh/id_rsa"}
TEST_RESULTS_DIR="${DIR}/../test-results"

# Create test results directory if it doesn't exist
mkdir -p "${TEST_RESULTS_DIR}"

print_message "Starting gwent package deployment and testing on Raspberry Pi (${RASPBERRY_PI_IP})..."

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

# Step 4: Install the package on the Raspberry Pi
print_message "Installing package on Raspberry Pi..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "source ${VENV_DIR}/bin/activate && pip install --upgrade ~/${PACKAGE_NAME}" || {
    print_error "Failed to install package on Raspberry Pi."
    exit 1
}
print_success "Package installed on Raspberry Pi."

# Step 5: Run hardware tests on the Raspberry Pi
print_message "Running hardware tests on Raspberry Pi..."
TEST_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_LOG_FILE="${TEST_RESULTS_DIR}/hardware_test_${TEST_TIMESTAMP}.log"
TEST_XML_FILE="${TEST_RESULTS_DIR}/hardware_test_${TEST_TIMESTAMP}.xml"

# Create a temporary script to run the tests
TMP_TEST_SCRIPT=$(mktemp)
cat > ${TMP_TEST_SCRIPT} << 'EOF'
#!/bin/bash
source ${VENV_DIR}/bin/activate
cd ~/gwent
# Install pytest if not already installed
pip install pytest pytest-cov
# Create tests directory if it doesn't exist
mkdir -p tests
# Create test-results directory if it doesn't exist
mkdir -p test-results
# Run the hardware tests with JUnit XML output
# The conftest.py will handle setting up the log file with the same timestamp
python -m pytest -v -m hardware tests/
# Copy the test results
find test-results -name "*.xml" -type f -exec cat {} \;
EOF

# Copy the test script to the Raspberry Pi
scp -i ${SSH_KEY} ${TMP_TEST_SCRIPT} ${PI_USER}@${RASPBERRY_PI_IP}:~/run_hardware_tests.sh || {
    print_error "Failed to copy test script to Raspberry Pi."
    rm ${TMP_TEST_SCRIPT}
    exit 1
}

# Make the script executable
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "chmod +x ~/run_hardware_tests.sh" || {
    print_error "Failed to make test script executable."
    rm ${TMP_TEST_SCRIPT}
    exit 1
}

# Run the tests and capture the output
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "VENV_DIR=${VENV_DIR} ~/run_hardware_tests.sh" > /dev/null 2>&1 || {
    print_warning "Some tests may have failed. Check the test results for details."
}

# Clean up the temporary script
rm ${TMP_TEST_SCRIPT}

# Copy the XML test results and log file from the Raspberry Pi
print_message "Copying test results from Raspberry Pi..."
scp -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP}:~/gwent/test-results/*.xml ${TEST_RESULTS_DIR}/ 2>/dev/null || {
    print_warning "Failed to copy XML test results from Raspberry Pi."
}

scp -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP}:~/gwent/test-results/*.log ${TEST_RESULTS_DIR}/ 2>/dev/null || {
    print_warning "Failed to copy log files from Raspberry Pi."
}

# Find the most recent XML file and log file
LATEST_XML=$(ls -t ${TEST_RESULTS_DIR}/hardware_test_*.xml 2>/dev/null | head -1)
LATEST_LOG=$(ls -t ${TEST_RESULTS_DIR}/hardware_test_*.log 2>/dev/null | head -1)

# Display test results
print_message "Hardware test results:"
if [ -f "${LATEST_LOG}" ]; then
    cat ${LATEST_LOG}
else
    print_warning "No log file found."
fi

# Check if any tests failed
if [ -f "${LATEST_XML}" ]; then
    if grep -q "failures=\"[1-9]" ${LATEST_XML} || grep -q "errors=\"[1-9]" ${LATEST_XML}; then
        print_error "Some hardware tests failed. See ${LATEST_LOG} for details."
        exit 1
    else
        print_success "All hardware tests passed!"
    fi
else
    print_error "No XML test results found."
    exit 1
fi

# Step 6: Clean up
print_message "Cleaning up..."
ssh -i ${SSH_KEY} ${PI_USER}@${RASPBERRY_PI_IP} "rm -f ~/run_hardware_tests.sh ~/${PACKAGE_NAME}" || {
    print_warning "Failed to clean up files on Raspberry Pi."
}

print_success "Deployment and testing completed successfully!"
if [ -f "${LATEST_LOG}" ]; then
    print_message "Test log saved to: ${LATEST_LOG}"
fi
if [ -f "${LATEST_XML}" ]; then
    print_message "XML test results saved to: ${LATEST_XML}"
fi