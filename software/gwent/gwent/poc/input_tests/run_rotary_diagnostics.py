#!/usr/bin/env python3
"""
Helper script to run the rotary encoder diagnostic tools.
This script provides a simple menu to select and run the different diagnostic tools.
"""

import os
import sys
import subprocess

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    """Print the header for the diagnostic tool"""
    clear_screen()
    print("=" * 60)
    print("Rotary Encoder Diagnostic Tools".center(60))
    print("=" * 60)
    print()

def print_menu():
    """Print the main menu"""
    print("Please select a diagnostic tool to run:")
    print()
    print("1. Enhanced Diagnostic Tool")
    print("   - Detailed pin state monitoring and visualization")
    print()
    print("2. Pin Configuration Test")
    print("   - Test different pin configurations to find the correct one")
    print()
    print("3. Debouncing Test")
    print("   - Test different debouncing settings")
    print()
    print("4. View README")
    print("   - Display the debugging guide")
    print()
    print("0. Exit")
    print()

def run_command(command):
    """Run a command and wait for it to complete"""
    try:
        print("\nRunning command:", " ".join(command))
        print("\nPress Enter to execute the command...")
        input()
        
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
    except KeyboardInterrupt:
        print("\nCommand interrupted by user")
    
    input("\nPress Enter to return to the menu...")

def run_enhanced_diagnostic():
    """Run the enhanced diagnostic tool"""
    print_header()
    print("Enhanced Diagnostic Tool")
    print("This tool provides detailed pin state monitoring and visualization.")
    print()
    
    # Ask for parameters
    swap_pins = input("Swap A and B pins? (y/n, default: n): ").lower() == 'y'
    
    try:
        monitor_time = float(input("Monitoring time in seconds (default: 0.5): ") or "0.5")
    except ValueError:
        monitor_time = 0.5
    
    print("\nPress Enter to start the pin state monitoring phase...")
    input()
    
    # Build the command
    command = ["python3", "-m", "gwent.poc.input_tests.rotary_diagnostic"]
    
    if swap_pins:
        command.append("--swap-pins")
    
    command.extend(["--monitor-time", str(monitor_time)])
    
    # Run the command
    run_command(command)

def run_pin_configuration_test():
    """Run the pin configuration test"""
    print_header()
    print("Pin Configuration Test")
    print("This tool tests different pin configurations to find the correct one.")
    print()
    
    # Ask for parameters
    try:
        start_config = int(input("Starting configuration index (0-2, default: 0): ") or "0")
    except ValueError:
        start_config = 0
    
    print("\nThis test will try different pin configurations.")
    print("For each configuration, you'll need to test the rotary encoder.")
    print("Press Enter to begin testing pin configurations...")
    input()
    
    # Build the command
    command = ["python3", "-m", "gwent.poc.input_tests.rotary_pin_test"]
    
    if start_config > 0:
        command.extend(["--start-config", str(start_config)])
    
    # Run the command
    run_command(command)

def run_debouncing_test():
    """Run the debouncing test"""
    print_header()
    print("Debouncing Test")
    print("This tool tests different debouncing settings.")
    print()
    
    # Ask for parameters
    try:
        bounce_time = int(input("Bounce time in ms for rotation (default: 0): ") or "0")
    except ValueError:
        bounce_time = 0
    
    try:
        min_interval = float(input("Minimum interval between events in seconds (default: 0.0): ") or "0.0")
    except ValueError:
        min_interval = 0.0
    
    print("\nThis test will help identify optimal debouncing settings.")
    print("You'll need to rotate the encoder and observe the results.")
    print("Press Enter to begin testing debouncing settings...")
    input()
    
    # Build the command
    command = ["python3", "-m", "gwent.poc.input_tests.rotary_debounce_test"]
    
    if bounce_time > 0:
        command.extend(["--bounce-time", str(bounce_time)])
    
    if min_interval > 0:
        command.extend(["--min-interval", str(min_interval)])
    
    # Run the command
    run_command(command)

def view_readme():
    """View the README file"""
    print_header()
    
    # Try to use 'less' if available, otherwise just print the file
    readme_path = os.path.join(os.path.dirname(__file__), "ROTARY_DEBUG_README.md")
    
    try:
        if os.name == 'posix':
            subprocess.run(["less", readme_path])
        else:
            with open(readme_path, 'r') as f:
                print(f.read())
    except Exception as e:
        print(f"Error displaying README: {e}")
    
    input("\nPress Enter to return to the menu...")

def main():
    """Main function"""
    while True:
        print_header()
        print_menu()
        
        choice = input("Enter your choice (0-4): ")
        
        if choice == '0':
            print("Exiting...")
            break
        elif choice == '1':
            run_enhanced_diagnostic()
        elif choice == '2':
            run_pin_configuration_test()
        elif choice == '3':
            run_debouncing_test()
        elif choice == '4':
            view_readme()
        else:
            input("Invalid choice. Press Enter to try again...")

if __name__ == "__main__":
    main()