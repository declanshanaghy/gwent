#!/usr/bin/env python3
"""
Fix script for the rotary encoder issue.
This script applies a fix to the rotary encoder implementation to make it more robust.
"""

import os
import sys
import argparse
import shutil
import re

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Fix rotary encoder implementation')
    parser.add_argument('--a-pin', type=int, default=None,
                        help='BCM pin number for A signal')
    parser.add_argument('--b-pin', type=int, default=None,
                        help='BCM pin number for B signal')
    parser.add_argument('--sw-pin', type=int, default=None,
                        help='BCM pin number for switch')
    parser.add_argument('--implementation', type=str, choices=['direct', 'gpiozero'], default=None,
                        help='Which implementation to use (direct or gpiozero)')
    parser.add_argument('--bounce-time', type=int, default=None,
                        help='Bounce time in ms for rotation detection')
    parser.add_argument('--backup', action='store_true',
                        help='Create backup files before modifying')
    return parser.parse_args()

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = file_path + '.bak'
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")

def fix_rotary_py(args):
    """Fix the rotary.py file"""
    # Path to the rotary.py file
    rotary_py_path = os.path.join(os.path.dirname(__file__), '..', '..', 'hal', 'rotary.py')
    
    if not os.path.exists(rotary_py_path):
        print(f"Error: Could not find rotary.py at {rotary_py_path}")
        return False
    
    # Create backup if requested
    if args.backup:
        backup_file(rotary_py_path)
    
    # Read the file
    with open(rotary_py_path, 'r') as f:
        content = f.read()
    
    # Make modifications
    modified = content
    
    # Update pin assignments if provided
    if args.a_pin is not None:
        modified = re.sub(r'A_PIN\s*=\s*\d+', f'A_PIN = {args.a_pin}', modified)
    
    if args.b_pin is not None:
        modified = re.sub(r'B_PIN\s*=\s*\d+', f'B_PIN = {args.b_pin}', modified)
    
    if args.sw_pin is not None:
        modified = re.sub(r'SW_PIN\s*=\s*\d+', f'SW_PIN = {args.sw_pin}', modified)
    
    # Update default implementation if provided
    if args.implementation is not None:
        if args.implementation == 'direct':
            impl = 'RotaryImplementation.DIRECT_GPIO'
        else:
            impl = 'RotaryImplementation.GPIOZERO'
        
        modified = re.sub(r'def __init__\(self, implementation=RotaryImplementation\.[A-Z_]+,',
                         f'def __init__(self, implementation={impl},', modified)
    
    # Add debouncing if provided
    if args.bounce_time is not None and args.bounce_time > 0:
        # Add a new parameter for bounce_time
        modified = re.sub(r'def __init__\(self, implementation=([^,]+), log_verbose=False\):',
                         r'def __init__(self, implementation=\1, log_verbose=False, bounce_time=None):',
                         modified)
        
        # Store the bounce_time parameter
        modified = re.sub(r'super\(\).__init__\(log_verbose=log_verbose\)',
                         r'super().__init__(log_verbose=log_verbose)\n        self._bounce_time = bounce_time',
                         modified)
        
        # Pass bounce_time to the encoder initialization
        direct_gpio_pattern = r'self._encoder = DirectGPIORotaryEncoder\(self\.A_PIN, self\.B_PIN, log=self\._log\)'
        direct_gpio_replacement = r'self._encoder = DirectGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log, bounce_time=self._bounce_time)'
        modified = re.sub(direct_gpio_pattern, direct_gpio_replacement, modified)
        
        gpiozero_pattern = r'self._encoder = GwentGPIOZeroRotaryEncoder\(self\.A_PIN, self\.B_PIN, log=self\._log\)'
        gpiozero_replacement = r'self._encoder = GwentGPIOZeroRotaryEncoder(self.A_PIN, self.B_PIN, log=self._log, bounce_time=self._bounce_time)'
        modified = re.sub(gpiozero_pattern, gpiozero_replacement, modified)
    
    # Write the modified content back to the file
    if modified != content:
        with open(rotary_py_path, 'w') as f:
            f.write(modified)
        print(f"Updated {rotary_py_path}")
        return True
    else:
        print("No changes were made to rotary.py")
        return False

def fix_rotary_rpigpio_py(args):
    """Fix the rotary_rpigpio.py file to add bounce_time parameter"""
    # Path to the rotary_rpigpio.py file
    rotary_rpigpio_py_path = os.path.join(os.path.dirname(__file__), '..', '..', 'hal', 'rotary_rpigpio.py')
    
    if not os.path.exists(rotary_rpigpio_py_path):
        print(f"Error: Could not find rotary_rpigpio.py at {rotary_rpigpio_py_path}")
        return False
    
    # Create backup if requested
    if args.backup:
        backup_file(rotary_rpigpio_py_path)
    
    # Read the file
    with open(rotary_rpigpio_py_path, 'r') as f:
        content = f.read()
    
    # Make modifications
    modified = content
    
    # Add bounce_time parameter to __init__
    modified = re.sub(r'def __init__\(self, a_pin, b_pin, callback=None, log=None\):',
                     r'def __init__(self, a_pin, b_pin, callback=None, log=None, bounce_time=None):',
                     modified)
    
    # Store the bounce_time parameter
    modified = re.sub(r'self._log = log or SimpleLogger\(\)',
                     r'self._log = log or SimpleLogger()\n        self.bounce_time = bounce_time or 1  # Default to 1ms if not specified',
                     modified)
    
    # Use bounce_time in add_event_detect
    modified = re.sub(r'GPIO\.add_event_detect\(self\.a_pin, GPIO\.BOTH, callback=self\._pin_change_callback\)',
                     r'GPIO.add_event_detect(self.a_pin, GPIO.BOTH, callback=self._pin_change_callback, bouncetime=self.bounce_time)',
                     modified)
    
    modified = re.sub(r'GPIO\.add_event_detect\(self\.b_pin, GPIO\.BOTH, callback=self\._pin_change_callback\)',
                     r'GPIO.add_event_detect(self.b_pin, GPIO.BOTH, callback=self._pin_change_callback, bouncetime=self.bounce_time)',
                     modified)
    
    # Write the modified content back to the file
    if modified != content:
        with open(rotary_rpigpio_py_path, 'w') as f:
            f.write(modified)
        print(f"Updated {rotary_rpigpio_py_path}")
        return True
    else:
        print("No changes were made to rotary_rpigpio.py")
        return False

def main():
    """Main function"""
    args = parse_args()
    
    print("Rotary Encoder Fix Script")
    print("=========================")
    
    # Apply fixes
    rotary_fixed = fix_rotary_py(args)
    rpigpio_fixed = fix_rotary_rpigpio_py(args)
    
    if rotary_fixed or rpigpio_fixed:
        print("\nFixes applied successfully!")
        print("\nRecommended next steps:")
        print("1. Run the diagnostic tools to verify the fix")
        print("2. If the issue persists, try different pin configurations")
        print("3. If still not working, check hardware connections")
    else:
        print("\nNo fixes were applied.")

if __name__ == "__main__":
    main()