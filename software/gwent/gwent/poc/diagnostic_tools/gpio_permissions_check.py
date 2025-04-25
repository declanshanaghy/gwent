#!/usr/bin/env python3
"""
GPIO Permissions and Usage Check Script.
This script checks for GPIO permission issues and identifies processes using GPIO pins.
"""

import os
import sys
import subprocess
import argparse

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Check GPIO permissions and usage')
    parser.add_argument('--pins', type=str, default="17,22,27",
                        help='Comma-separated list of GPIO pins to check (default: 17,22,27)')
    return parser.parse_args()

def check_gpio_group():
    """Check if the current user is in the gpio group"""
    try:
        # Check if the gpio group exists
        result = subprocess.run(['getent', 'group', 'gpio'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.returncode != 0:
            print("The 'gpio' group does not exist on this system.")
            print("This might be normal depending on your Raspberry Pi OS version.")
            return False
        
        # Check if the current user is in the gpio group
        current_user = os.environ.get('USER', os.environ.get('LOGNAME', 'unknown'))
        groups_result = subprocess.run(['groups', current_user], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
        
        if 'gpio' in groups_result.stdout:
            print(f"✅ User '{current_user}' is in the gpio group.")
            return True
        else:
            print(f"❌ User '{current_user}' is NOT in the gpio group.")
            print("This may cause permission issues when accessing GPIO pins.")
            print("To fix this, run: sudo usermod -a -G gpio $USER")
            print("Then log out and log back in for the changes to take effect.")
            return False
    except Exception as e:
        print(f"Error checking gpio group: {e}")
        return False

def check_gpio_device_permissions():
    """Check permissions on /dev/gpiomem"""
    try:
        if os.path.exists('/dev/gpiomem'):
            result = subprocess.run(['ls', '-l', '/dev/gpiomem'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
            print("GPIO device permissions:")
            print(result.stdout.strip())
            
            # Check if the device is readable by the current user
            if os.access('/dev/gpiomem', os.R_OK):
                print("✅ Current user has read access to /dev/gpiomem")
            else:
                print("❌ Current user does NOT have read access to /dev/gpiomem")
                print("This will prevent GPIO access.")
                print("To fix this, run: sudo chmod g+rw /dev/gpiomem")
                return False
            return True
        else:
            print("❌ /dev/gpiomem does not exist. This is unusual for a Raspberry Pi.")
            return False
    except Exception as e:
        print(f"Error checking GPIO device permissions: {e}")
        return False

def check_processes_using_gpio():
    """Check for processes that might be using GPIO pins"""
    try:
        # Look for processes using GPIO
        print("\nChecking for processes using GPIO...")
        
        # Check for Python processes that might be using GPIO
        python_procs = subprocess.run(['pgrep', '-f', 'python'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, 
                                     text=True)
        
        if python_procs.returncode == 0:
            pids = python_procs.stdout.strip().split('\n')
            current_pid = str(os.getpid())
            
            for pid in pids:
                if pid and pid != current_pid:  # Skip the current process
                    cmd = subprocess.run(['ps', '-p', pid, '-o', 'cmd='], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, 
                                        text=True)
                    cmd_output = cmd.stdout.strip()
                    
                    # Look for GPIO-related processes
                    if any(x in cmd_output.lower() for x in ['gpio', 'rotary', 'pin']):
                        print(f"⚠️  Process {pid} might be using GPIO: {cmd_output}")
        
        # Check for specific GPIO-related services
        services = ['pigpiod', 'gpio', 'gpiod']
        for service in services:
            result = subprocess.run(['pgrep', '-f', service], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
            if result.returncode == 0:
                print(f"⚠️  Found {service} service running. This might be using GPIO pins.")
                
        return True
    except Exception as e:
        print(f"Error checking processes: {e}")
        return False

def check_gpio_pin_exports(pins):
    """Check if GPIO pins are exported in sysfs"""
    try:
        gpio_path = '/sys/class/gpio'
        if not os.path.exists(gpio_path):
            print("❌ GPIO sysfs interface not available.")
            return False
        
        print("\nChecking GPIO pin exports...")
        for pin in pins:
            export_path = f"{gpio_path}/gpio{pin}"
            if os.path.exists(export_path):
                print(f"⚠️  GPIO pin {pin} is exported. This might cause conflicts.")
                
                # Check direction
                direction_path = f"{export_path}/direction"
                if os.path.exists(direction_path):
                    with open(direction_path, 'r') as f:
                        direction = f.read().strip()
                        print(f"   - Direction: {direction}")
                
                # Check value
                value_path = f"{export_path}/value"
                if os.path.exists(value_path):
                    with open(value_path, 'r') as f:
                        value = f.read().strip()
                        print(f"   - Value: {value}")
                        
                print(f"   To unexport this pin, run: echo {pin} | sudo tee /sys/class/gpio/unexport")
            else:
                print(f"✅ GPIO pin {pin} is not exported.")
        
        return True
    except Exception as e:
        print(f"Error checking GPIO pin exports: {e}")
        return False

def check_gpio_library_conflicts():
    """Check for potential GPIO library conflicts"""
    try:
        print("\nChecking for potential GPIO library conflicts...")
        
        # Check if pigpio daemon is running
        pigpio_result = subprocess.run(['pgrep', 'pigpiod'], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
        
        if pigpio_result.returncode == 0:
            print("⚠️  pigpiod daemon is running. This might conflict with RPi.GPIO or gpiozero.")
            print("   If you're not using pigpio explicitly, consider stopping it:")
            print("   sudo killall pigpiod")
        else:
            print("✅ pigpiod daemon is not running.")
        
        return True
    except Exception as e:
        print(f"Error checking GPIO library conflicts: {e}")
        return False

def run():
    """Run the GPIO permissions and usage check"""
    args = parse_args()
    
    print("=" * 60)
    print("GPIO Permissions and Usage Check".center(60))
    print("=" * 60)
    
    # Parse pins
    try:
        pins = [int(pin.strip()) for pin in args.pins.split(',')]
    except ValueError:
        print(f"Error: Invalid pin format. Please use comma-separated numbers.")
        return 1
    
    print(f"Checking GPIO pins: {', '.join(map(str, pins))}")
    print()
    
    # Run checks
    check_gpio_group()
    check_gpio_device_permissions()
    check_processes_using_gpio()
    check_gpio_pin_exports(pins)
    check_gpio_library_conflicts()
    
    print("\nRecommendations:")
    print("1. If other processes are using GPIO pins, stop them before running your tests")
    print("2. Ensure your user has proper permissions to access GPIO")
    print("3. Try running the diagnostic tools with sudo if permission issues persist")
    print("4. If using RPi.GPIO, try switching to gpiozero or vice versa")
    print("5. Reboot the Raspberry Pi to reset all GPIO states")
    
    return 0

if __name__ == "__main__":
    sys.exit(run())