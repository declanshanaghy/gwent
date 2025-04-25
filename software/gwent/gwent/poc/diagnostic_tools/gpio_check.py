#!/usr/bin/env python3
"""
Utility script to check for GPIO pin conflicts.
This script checks if any GPIO pins are already exported/in use,
which could cause conflicts with the rotary encoder.
"""

import os
import sys
import argparse

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Check for GPIO pin conflicts')
    parser.add_argument('--pins', type=str, default="17,22,27",
                        help='Comma-separated list of BCM pin numbers to check (default: 17,22,27)')
    return parser.parse_args()

def check_gpio_pins(pins):
    """Check if the specified GPIO pins are already exported/in use"""
    gpio_path = "/sys/class/gpio"
    
    # Check if the gpio path exists (should exist on Raspberry Pi)
    if not os.path.exists(gpio_path):
        print(f"ERROR: GPIO path {gpio_path} does not exist.")
        print("This script should be run on a Raspberry Pi.")
        return False
    
    # Check each pin
    conflicts = []
    for pin in pins:
        pin_path = f"{gpio_path}/gpio{pin}"
        if os.path.exists(pin_path):
            # Pin is exported, try to get more information
            try:
                direction = "unknown"
                direction_path = f"{pin_path}/direction"
                if os.path.exists(direction_path):
                    with open(direction_path, 'r') as f:
                        direction = f.read().strip()
                
                value = "unknown"
                value_path = f"{pin_path}/value"
                if os.path.exists(value_path):
                    with open(value_path, 'r') as f:
                        value = f.read().strip()
                
                conflicts.append({
                    'pin': pin,
                    'direction': direction,
                    'value': value
                })
            except Exception as e:
                conflicts.append({
                    'pin': pin,
                    'error': str(e)
                })
    
    return conflicts

def list_processes_using_gpio():
    """List processes that might be using GPIO pins"""
    try:
        import subprocess
        print("\nProcesses that might be using GPIO pins:")
        
        # Look for processes using GPIO-related libraries
        for lib in ["gpio", "RPi.GPIO", "gpiozero", "wiringpi"]:
            try:
                cmd = f"ps aux | grep -i {lib} | grep -v grep"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    print(f"\nProcesses using {lib}:")
                    print(result.stdout)
            except Exception as e:
                print(f"Error checking for {lib} processes: {e}")
        
        # Check for specific services
        for service in ["gwent.service"]:
            try:
                cmd = f"systemctl status {service}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if "Active: active" in result.stdout:
                    print(f"\nService {service} is running:")
                    status_lines = result.stdout.split('\n')[:5]
                    print('\n'.join(status_lines))
            except Exception as e:
                print(f"Error checking service {service}: {e}")
                
    except Exception as e:
        print(f"Error listing processes: {e}")

def main():
    """Main function"""
    args = parse_args()
    
    # Parse pin list
    try:
        pins = [int(pin.strip()) for pin in args.pins.split(',')]
    except ValueError:
        print("ERROR: Invalid pin format. Please provide comma-separated integers.")
        sys.exit(1)
    
    print(f"Checking for GPIO pin conflicts on pins: {pins}")
    
    # Check for conflicts
    conflicts = check_gpio_pins(pins)
    
    if conflicts:
        print("\nWARNING: The following GPIO pins are already in use:")
        for conflict in conflicts:
            if 'error' in conflict:
                print(f"  - GPIO{conflict['pin']}: Error checking pin: {conflict['error']}")
            else:
                print(f"  - GPIO{conflict['pin']}: direction={conflict['direction']}, value={conflict['value']}")
        
        print("\nThis may cause conflicts with the rotary encoder.")
        print("Consider stopping any services or processes using these pins before running the rotary encoder.")
        
        # List processes that might be using GPIO
        list_processes_using_gpio()
        
        print("\nTo unexport a pin, you can run:")
        for pin in [conflict['pin'] for conflict in conflicts]:
            print(f"  echo {pin} > /sys/class/gpio/unexport")
    else:
        print("\nNo GPIO pin conflicts found. All specified pins are available.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())