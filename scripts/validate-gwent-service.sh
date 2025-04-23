#!/bin/bash
# Script to validate and fix the gwent service on the Raspberry Pi

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Load environment variables
source "${DIR}/install-vars.sh"

# Expand ~ in VENV_DIR if present
VENV_DIR="${VENV_DIR/#\~/$HOME}"

# Initialize flags
CRITICAL_ERRORS=0
WARNINGS_FOUND=0

# Always check logs for errors and warnings
echo "Checking logs for recent errors and warnings..."

# First check for critical errors (missing modules, exceptions, etc.)
if journalctl -u gwent -n 20 --no-pager | grep -i "ModuleNotFoundError\|ImportError\|Exception\|Traceback"; then
    echo "❌ Critical errors found in logs!"
    CRITICAL_ERRORS=1
# Then check for non-critical warnings
elif journalctl -u gwent -n 20 --no-pager | grep -i "error\|warn\|fail"; then
    echo "⚠️ Non-critical warnings found in logs"
    WARNINGS_FOUND=1
else
    echo "✅ No errors or warnings found in recent logs"
fi

# Check if service is active
if systemctl is-active --quiet gwent; then
    echo "✅ Gwent service is running"
    systemctl status gwent | grep "Active:"
    
    # If critical errors were found in logs, try to fix them
    if [ $CRITICAL_ERRORS -eq 1 ]; then
        echo "❌ Service is running but has critical errors in logs."
        exit 2  # Exit with code 2 to indicate service running but with critical errors
    elif [ $WARNINGS_FOUND -eq 1 ]; then
        echo "⚠️ Service is running with non-critical warnings in logs."
        echo "These warnings are not preventing the service from functioning properly."
        echo "You can safely ignore these warnings or check the logs for more details:"
        echo "  journalctl -u gwent -n 50"
        exit 0  # Still exit with 0 for non-critical warnings
    fi
    
    exit 0  # Exit with code 0 for success (service running, no errors or only normal initialization warnings)
else
    echo "❌ Gwent service is NOT running"
    
    # Get service status for debugging
    echo "Current status:"
    systemctl status gwent
    
    # Attempt to restart the service
    echo "Attempting to restart the service..."
    sudo systemctl restart gwent
    sleep 2
    
    # Check if restart fixed the issue
    if systemctl is-active --quiet gwent; then
        echo "✅ Service successfully restarted"
        systemctl status gwent | grep "Active:"
        exit 0
    else
        echo "❌ Service restart failed"
        
        # Check for specific errors and try to fix them
        # This section previously contained pygame installation code
        # It has been removed as pygame is now installed via install-system.sh
        
        # Check if service is enabled
        if ! systemctl is-enabled --quiet gwent; then
            echo "Service is not enabled. Enabling..."
            sudo systemctl enable gwent
        fi
        
        # Check if the service file exists and is valid
        if [ ! -f /etc/systemd/system/gwent.service ]; then
            echo "Service file missing. Reinstalling..."
            sudo cp ${DEPLOY_DIR}/gwent.service /etc/systemd/system/
            sudo systemctl daemon-reload
        fi
        
        # Check if the service file has the correct paths
        echo "Checking service file configuration..."
        SERVICE_FILE="/etc/systemd/system/gwent.service"
        
        # Check for common path issues
        if grep -q "/home/pi/gwent-venv" $SERVICE_FILE && [ ! -d "/home/pi/gwent-venv" ]; then
            echo "Service file has incorrect virtual environment path. Updating..."
            sudo sed -i 's|/home/pi/gwent-venv|'"${VENV_DIR}"'|g' $SERVICE_FILE
            sudo systemctl daemon-reload
        fi
        
        # Check if ExecStart is using the correct command
        if ! grep -q "ExecStart=.*bin/python -m gwent.game.main" $SERVICE_FILE; then
            echo "Service file has incorrect ExecStart command. Checking current command:"
            grep "ExecStart" $SERVICE_FILE
            
            # If it's using 'gwent' command instead of python -m gwent.game.main
            if grep -q "ExecStart=.*bin/gwent" $SERVICE_FILE; then
                echo "Updating ExecStart to use python module directly..."
                sudo sed -i 's|ExecStart=.*/bin/gwent|ExecStart='"${VENV_DIR}"'/bin/python -m gwent.game.main|g' $SERVICE_FILE
                sudo systemctl daemon-reload
            fi
        fi
        
        # Check if PYTHONPATH is set correctly
        if ! grep -q "Environment=PYTHONPATH=" $SERVICE_FILE; then
            echo "Service file missing PYTHONPATH environment variable. Adding..."
            sudo sed -i '/\[Service\]/a Environment=PYTHONPATH='"${DEPLOY_DIR}"'/software' $SERVICE_FILE
            sudo systemctl daemon-reload
        else
            # Check if PYTHONPATH includes the software directory
            if ! grep -q "Environment=PYTHONPATH=.*${DEPLOY_DIR}/software" $SERVICE_FILE; then
                echo "Service file has incorrect PYTHONPATH. Updating..."
                sudo sed -i 's|Environment=PYTHONPATH=.*|Environment=PYTHONPATH='"${DEPLOY_DIR}"'/software|g' $SERVICE_FILE
                sudo systemctl daemon-reload
            fi
        fi
        
        # Check WorkingDirectory
        if ! grep -q "WorkingDirectory=/home" $SERVICE_FILE; then
            echo "Service file missing or has incorrect WorkingDirectory. Adding..."
            sudo sed -i '/\[Service\]/a WorkingDirectory=/home/'"$USER"'' $SERVICE_FILE
            sudo systemctl daemon-reload
        fi
        
        # Try one more restart
        echo "Attempting final restart..."
        sudo systemctl restart gwent
        sleep 2
        
        # Final check
        if systemctl is-active --quiet gwent; then
            echo "✅ Service is now running after fixes"
            systemctl status gwent | grep "Active:"
            exit 0
        else
            echo "❌ Failed to fix service. Manual intervention required."
            echo "Possible issues:"
            echo "1. Python environment issues - check if virtual environment exists:"
            echo "   ls -la ${VENV_DIR}/"
            echo "2. Missing dependencies. Try installing the gwent package:"
            echo "   cd ${DEPLOY_DIR}/software/gwent && sudo pip3 install -e ."
            echo "3. Service file configuration issues. Current service file:"
            echo "   cat /etc/systemd/system/gwent.service"
            echo "4. Permission problems. Check file permissions:"
            echo "   ls -la ${VENV_DIR}/bin/"
            echo "5. Check system logs for more details:"
            echo "   journalctl -u gwent -n 50"
            exit 1
        fi
    fi
fi