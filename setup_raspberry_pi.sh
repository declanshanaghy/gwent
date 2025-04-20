#!/usr/bin/env bash

# Gwent Raspberry Pi Development Environment Setup Script
# This script sets up a Raspberry Pi for Gwent development by installing
# all necessary dependencies, libraries, and tools required for the project.
# Note: The original asyncio-based implementation has been moved to software/gwent-asyncio

set -e  # Exit on error

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[SETUP]${NC} $1"
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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (sudo)"
   exit 1
fi

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Define variables
VENV_NAME="gwent-venv"
VENV_DIR="${HOME}/${VENV_NAME}"
USER_NAME=$(logname)
USER_HOME="/home/${USER_NAME}"
VENV_DIR="${USER_HOME}/${VENV_NAME}"

print_message "Starting Gwent Raspberry Pi development environment setup..."
print_message "User: ${USER_NAME}"
print_message "Virtual environment will be created at: ${VENV_DIR}"

# Step 1: Update the system
print_message "Updating system packages..."
apt-get update
apt-get upgrade -y

# Step 2: Install system dependencies
print_message "Installing system dependencies..."
apt-get install -y \
    python3-dev python3-pip python3-venv python3-pil python3-wheel \
    git \
    ffmpeg \
    libasound2-dev libpulse-dev \
    libsdl2-dev libsmpeg-dev \
    libavformat-dev libavcodec-dev \
    libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
    mosquitto mosquitto-clients redis-server \
    rpi.gpio i2c-tools

# Step 3: Install WiringPi
print_message "Installing WiringPi..."
if [ -f "${DIR}/software/wiringpi-latest.deb" ]; then
    dpkg -i "${DIR}/software/wiringpi-latest.deb"
else
    print_warning "WiringPi deb package not found. Skipping installation."
    print_warning "You may need to install WiringPi manually."
fi

# Step 4: Enable SPI and I2C interfaces
print_message "Enabling SPI and I2C interfaces..."
if command -v raspi-config > /dev/null; then
    # Enable SPI
    raspi-config nonint do_spi 0
    # Enable I2C
    raspi-config nonint do_i2c 0
    print_success "SPI and I2C interfaces enabled"
else
    print_warning "raspi-config not found. Please enable SPI and I2C manually:"
    print_warning "Run 'sudo raspi-config' and enable SPI and I2C under 'Interface Options'"
fi

# Step 5: Add user to required groups
print_message "Adding user to required groups..."
usermod -a -G gpio,spi,i2c,dialout,audio,video "${USER_NAME}"
print_success "User ${USER_NAME} added to required groups"

# Step 6: Create Python virtual environment
print_message "Setting up Python virtual environment..."
if [ -d "${VENV_DIR}" ]; then
    print_warning "Virtual environment already exists at ${VENV_DIR}"
else
    # Create venv as the regular user, not as root
    su - "${USER_NAME}" -c "python3 -m venv ${VENV_DIR}"
    print_success "Virtual environment created at ${VENV_DIR}"
fi

# Step 7: Install Python packages
print_message "Installing Python packages..."
# Activate virtual environment and install packages
su - "${USER_NAME}" -c "source ${VENV_DIR}/bin/activate && \
    pip3 install --upgrade pip wheel setuptools && \
    pip3 install -e ${DIR}/software/gaugette && \
    pip3 install -e ${DIR}/software/MFRC522-python && \
    pip3 install -e ${DIR}/software/gwent"

print_message "Note: The original asyncio-based implementation has been moved to software/gwent-asyncio"

print_success "Python packages installed"

# Step 8: Configure services
print_message "Configuring services..."
# Enable and start Mosquitto MQTT broker
systemctl enable mosquitto
systemctl start mosquitto

# Enable and start Redis server
systemctl enable redis-server
systemctl start redis-server

print_success "Services configured and started"

# Step 9: Install Gwent systemd service
print_message "Installing Gwent systemd service..."
# Copy the service file to systemd directory
if [ -f "${DIR}/gwent.service" ]; then
    cp "${DIR}/gwent.service" /etc/systemd/system/
    # Set correct permissions
    chmod 644 /etc/systemd/system/gwent.service
    # Enable the service to start on boot
    systemctl daemon-reload
    systemctl enable gwent.service
    print_success "Gwent service installed and enabled"
    print_message "You can start the service with: sudo systemctl start gwent.service"
else
    print_warning "gwent.service file not found. Skipping service installation."
    print_warning "You may need to create and install the service manually."
fi

# Step 10: Create test script
print_message "Creating hardware test script..."
TEST_SCRIPT="${DIR}/test_hardware.py"

cat > "${TEST_SCRIPT}" << 'EOF'
#!/usr/bin/env python3

"""
Gwent Hardware Test Script
This script tests the various hardware components used in the Gwent project.
"""

import sys
import time
import os
from pathlib import Path

def print_colored(text, color_code):
    """Print colored text to the terminal."""
    print(f"\033[{color_code}m{text}\033[0m")

def print_header(text):
    """Print a header with a specific format."""
    print("\n" + "=" * 60)
    print_colored(f"  {text}", "1;34")
    print("=" * 60)

def print_success(text):
    """Print a success message."""
    print_colored(f"[SUCCESS] {text}", "1;32")

def print_error(text):
    """Print an error message."""
    print_colored(f"[ERROR] {text}", "1;31")

def print_info(text):
    """Print an info message."""
    print_colored(f"[INFO] {text}", "1;36")

def print_warning(text):
    """Print a warning message."""
    print_colored(f"[WARNING] {text}", "1;33")

def test_gpio():
    """Test GPIO functionality."""
    print_header("Testing GPIO")
    try:
        import RPi.GPIO as GPIO
        print_info("RPi.GPIO imported successfully")
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        print_success("GPIO setup completed")
        
        # Cleanup
        GPIO.cleanup()
        return True
    except ImportError:
        print_error("Failed to import RPi.GPIO. Make sure it's installed.")
        return False
    except Exception as e:
        print_error(f"GPIO test failed: {str(e)}")
        return False

def test_spi():
    """Test SPI functionality."""
    print_header("Testing SPI")
    try:
        import spidev
        print_info("spidev imported successfully")
        
        # Try to open SPI device
        spi = spidev.SpiDev()
        spi.open(0, 0)  # Open SPI port 0, device (CS) 0
        spi.max_speed_hz = 1000000  # 1MHz
        print_success("SPI device opened successfully")
        
        # Close SPI device
        spi.close()
        return True
    except ImportError:
        print_error("Failed to import spidev. Make sure it's installed.")
        return False
    except Exception as e:
        print_error(f"SPI test failed: {str(e)}")
        print_warning("Make sure SPI is enabled in raspi-config")
        return False

def test_i2c():
    """Test I2C functionality."""
    print_header("Testing I2C")
    try:
        import smbus
        print_info("smbus imported successfully")
        
        # Try to open I2C bus
        bus = smbus.SMBus(1)  # 1 indicates /dev/i2c-1
        print_success("I2C bus opened successfully")
        
        # Scan for I2C devices
        print_info("Scanning for I2C devices...")
        devices = []
        for addr in range(0x03, 0x78):
            try:
                bus.read_byte(addr)
                devices.append(addr)
            except:
                pass
        
        if devices:
            print_success(f"Found {len(devices)} I2C devices at addresses: {', '.join([hex(addr) for addr in devices])}")
        else:
            print_warning("No I2C devices found. Make sure they are connected properly.")
        
        return True
    except ImportError:
        print_error("Failed to import smbus. Make sure it's installed.")
        return False
    except Exception as e:
        print_error(f"I2C test failed: {str(e)}")
        print_warning("Make sure I2C is enabled in raspi-config")
        return False

def test_rfid():
    """Test RFID reader."""
    print_header("Testing RFID Reader")
    try:
        import mfrc522
        print_info("mfrc522 library imported successfully")
        
        print_info("Initializing RFID reader...")
        try:
            reader = mfrc522.SimpleMFRC522()
            print_success("RFID reader initialized successfully")
            
            print_info("Waiting for RFID card... (Place a card on the reader or press Ctrl+C to skip)")
            try:
                id, text = reader.read(timeout=10)
                print_success(f"Card detected! ID: {id}, Text: {text}")
            except KeyboardInterrupt:
                print_warning("RFID card reading skipped")
            except Exception as e:
                print_warning(f"Failed to read RFID card: {str(e)}")
                print_warning("Make sure the RFID reader is connected properly")
            
            return True
        except Exception as e:
            print_error(f"Failed to initialize RFID reader: {str(e)}")
            print_warning("Make sure the RFID reader is connected properly and SPI is enabled")
            return False
    except ImportError:
        print_error("Failed to import mfrc522. Make sure it's installed.")
        return False

def test_oled():
    """Test OLED display."""
    print_header("Testing OLED Display")
    try:
        from luma.core.interface.serial import spi
        from luma.oled.device import ssd1306
        from luma.core.render import canvas
        print_info("luma.oled libraries imported successfully")
        
        try:
            # Initialize OLED display
            print_info("Initializing OLED display...")
            serial = spi(device=0, port=0)
            device = ssd1306(serial)
            
            # Draw something on the display
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((10, 10), "Gwent Test", fill="white")
                draw.text((10, 30), "OLED OK!", fill="white")
            
            print_success("OLED display test successful")
            print_info("You should see text on the OLED display")
            time.sleep(3)  # Keep the text visible for a few seconds
            
            # Clear the display
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="black", fill="black")
            
            return True
        except Exception as e:
            print_error(f"OLED display test failed: {str(e)}")
            print_warning("Make sure the OLED display is connected properly and SPI is enabled")
            return False
    except ImportError:
        print_error("Failed to import luma.oled libraries. Make sure they're installed.")
        return False

def test_rotary_encoder():
    """Test rotary encoder."""
    print_header("Testing Rotary Encoder")
    try:
        import gaugette.gpio
        import gaugette.rotary_encoder
        print_info("gaugette libraries imported successfully")
        
        try:
            # Initialize rotary encoder
            print_info("Initializing rotary encoder...")
            gpio = gaugette.gpio.GPIO()
            encoder = gaugette.rotary_encoder.RotaryEncoder(gpio, 1, 0)  # A_PIN=1, B_PIN=0
            encoder.start()
            
            print_info("Rotary encoder initialized successfully")
            print_info("Please rotate the encoder... (5 seconds to test or press Ctrl+C to skip)")
            
            start_time = time.time()
            last_count = 0
            try:
                while time.time() - start_time < 5:
                    delta = encoder.get_cycles()
                    if delta != 0:
                        last_count += delta
                        print_info(f"Rotary encoder count: {last_count}")
                    time.sleep(0.1)
                
                if last_count == 0:
                    print_warning("No rotary encoder movement detected. Make sure it's connected properly.")
                else:
                    print_success("Rotary encoder test successful")
                
                return True
            except KeyboardInterrupt:
                print_warning("Rotary encoder test skipped")
                return True
        except Exception as e:
            print_error(f"Rotary encoder test failed: {str(e)}")
            print_warning("Make sure the rotary encoder is connected properly")
            return False
    except ImportError:
        print_error("Failed to import gaugette libraries. Make sure they're installed.")
        return False

def test_mqtt():
    """Test MQTT functionality."""
    print_header("Testing MQTT")
    try:
        import paho.mqtt.client as mqtt
        print_info("paho-mqtt library imported successfully")
        
        # Test connection to MQTT broker
        client = mqtt.Client()
        try:
            client.connect("localhost", 1883, 60)
            print_success("Connected to MQTT broker successfully")
            client.disconnect()
            return True
        except Exception as e:
            print_error(f"Failed to connect to MQTT broker: {str(e)}")
            print_warning("Make sure the Mosquitto service is running")
            return False
    except ImportError:
        print_error("Failed to import paho-mqtt. Make sure it's installed.")
        return False

def test_redis():
    """Test Redis functionality."""
    print_header("Testing Redis")
    try:
        import redis
        print_info("redis library imported successfully")
        
        # Test connection to Redis server
        r = redis.Redis(host='localhost', port=6379, db=0)
        try:
            r.ping()
            print_success("Connected to Redis server successfully")
            return True
        except Exception as e:
            print_error(f"Failed to connect to Redis server: {str(e)}")
            print_warning("Make sure the Redis service is running")
            return False
    except ImportError:
        print_error("Failed to import redis. Make sure it's installed.")
        return False

def main():
    """Run all hardware tests."""
    print_header("Gwent Hardware Test")
    
    # Run tests
    results = {
        "GPIO": test_gpio(),
        "SPI": test_spi(),
        "I2C": test_i2c(),
        "RFID": test_rfid(),
        "OLED": test_oled(),
        "Rotary Encoder": test_rotary_encoder(),
        "MQTT": test_mqtt(),
        "Redis": test_redis()
    }
    
    # Print summary
    print_header("Test Summary")
    all_passed = True
    for test, passed in results.items():
        if passed:
            print_success(f"{test}: PASSED")
        else:
            print_error(f"{test}: FAILED")
            all_passed = False
    
    if all_passed:
        print_success("\nAll tests passed! Your Gwent hardware setup is working correctly.")
    else:
        print_warning("\nSome tests failed. Please check the error messages and fix the issues.")

if __name__ == "__main__":
    main()
EOF

chmod +x "${TEST_SCRIPT}"
chown "${USER_NAME}:${USER_NAME}" "${TEST_SCRIPT}"
print_success "Hardware test script created at ${TEST_SCRIPT}"

# Step 11: Create a convenience script to activate the virtual environment
print_message "Creating convenience script..."
ACTIVATE_SCRIPT="${DIR}/activate_gwent.sh"

cat > "${ACTIVATE_SCRIPT}" << EOF
#!/usr/bin/env bash

# Activate Gwent virtual environment
source "${VENV_DIR}/bin/activate"
echo "Gwent virtual environment activated"
echo "You can now run Gwent commands, such as:"
echo "  - gwent: Run the main Gwent game"
echo "  - novigrad: Run the Novigrad server"
echo "  - write_card: Write data to an RFID card"
echo "  - read_card: Read data from an RFID card"
echo "  - python ${TEST_SCRIPT}: Run the hardware test script"
EOF

chmod +x "${ACTIVATE_SCRIPT}"
chown "${USER_NAME}:${USER_NAME}" "${ACTIVATE_SCRIPT}"
print_success "Convenience script created at ${ACTIVATE_SCRIPT}"

# Final message
print_message "Gwent Raspberry Pi development environment setup completed!"
print_message "Please reboot your Raspberry Pi to apply all changes:"
print_message "  sudo reboot"
print_message ""
print_message "After reboot, you can:"
print_message "1. Activate the virtual environment: source ${ACTIVATE_SCRIPT}"
print_message "2. Test your hardware: python ${TEST_SCRIPT}"
print_message "3. Run the Gwent game manually: gwent"
print_message "4. Control the Gwent service:"
print_message "   - Start: sudo systemctl start gwent.service"
print_message "   - Stop: sudo systemctl stop gwent.service"
print_message "   - Status: sudo systemctl status gwent.service"
print_message ""
print_message "Note: The Gwent service is configured to start automatically on boot."
print_message "Note: You may need to log out and log back in for group changes to take effect."