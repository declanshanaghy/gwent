#!/usr/bin/env python3
"""
GPIO Service Manager Script.
This script helps manage GPIO-related services that might conflict with rotary encoder tests.
"""

import os
import sys
import subprocess
import argparse

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Manage GPIO-related services')
    parser.add_argument('--action', type=str, choices=['check', 'stop', 'start', 'restart'],
                        default='check', help='Action to perform on GPIO services')
    parser.add_argument('--service', type=str, default='gpio',
                        help='Service name to manage (default: gpio)')
    return parser.parse_args()

def check_service_status(service_name):
    """Check if a service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.stdout.strip() == 'active':
            print(f"✅ Service '{service_name}' is running.")
            return True
        else:
            print(f"❌ Service '{service_name}' is not running.")
            return False
    except Exception as e:
        print(f"Error checking service status: {e}")
        return False

def stop_service(service_name):
    """Stop a service"""
    try:
        print(f"Stopping service '{service_name}'...")
        result = subprocess.run(['sudo', 'systemctl', 'stop', service_name], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.returncode == 0:
            print(f"✅ Service '{service_name}' stopped successfully.")
            return True
        else:
            print(f"❌ Failed to stop service '{service_name}'.")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error stopping service: {e}")
        return False

def start_service(service_name):
    """Start a service"""
    try:
        print(f"Starting service '{service_name}'...")
        result = subprocess.run(['sudo', 'systemctl', 'start', service_name], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.returncode == 0:
            print(f"✅ Service '{service_name}' started successfully.")
            return True
        else:
            print(f"❌ Failed to start service '{service_name}'.")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error starting service: {e}")
        return False

def restart_service(service_name):
    """Restart a service"""
    try:
        print(f"Restarting service '{service_name}'...")
        result = subprocess.run(['sudo', 'systemctl', 'restart', service_name], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.returncode == 0:
            print(f"✅ Service '{service_name}' restarted successfully.")
            return True
        else:
            print(f"❌ Failed to restart service '{service_name}'.")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error restarting service: {e}")
        return False

def check_gpio_processes():
    """Check for processes that might be using GPIO pins"""
    try:
        print("\nChecking for processes using GPIO...")
        
        # Look for GPIO-related processes
        processes = ['gpio', 'pigpio', 'gpiod', 'rotary']
        found_processes = False
        
        for process in processes:
            result = subprocess.run(['pgrep', '-f', process], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
            
            if result.returncode == 0:
                found_processes = True
                pids = result.stdout.strip().split('\n')
                
                for pid in pids:
                    if pid:  # Skip empty lines
                        cmd = subprocess.run(['ps', '-p', pid, '-o', 'cmd='], 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE, 
                                            text=True)
                        cmd_output = cmd.stdout.strip()
                        
                        # Skip the current process
                        if 'gpio_service_manager.py' not in cmd_output:
                            print(f"⚠️  Process {pid}: {cmd_output}")
        
        if not found_processes:
            print("✅ No GPIO-related processes found.")
        
        return found_processes
    except Exception as e:
        print(f"Error checking processes: {e}")
        return False

def run():
    """Run the GPIO service manager"""
    args = parse_args()
    
    print("=" * 60)
    print("GPIO Service Manager".center(60))
    print("=" * 60)
    
    service_name = args.service
    
    if args.action == 'check':
        check_service_status(service_name)
        check_gpio_processes()
    elif args.action == 'stop':
        if check_service_status(service_name):
            stop_service(service_name)
        check_gpio_processes()
    elif args.action == 'start':
        if not check_service_status(service_name):
            start_service(service_name)
        check_gpio_processes()
    elif args.action == 'restart':
        restart_service(service_name)
        check_gpio_processes()
    
    print("\nRecommendations:")
    print("1. If you're having issues with rotary encoder tests, try stopping the GPIO service:")
    print("   python -m gwent.poc.diagnostic_tools.gpio_service_manager --action stop")
    print("2. After your tests, you can restart the GPIO service if needed:")
    print("   python -m gwent.poc.diagnostic_tools.gpio_service_manager --action start")
    print("3. If you're using pigpio for your tests, make sure the pigpio daemon is running:")
    print("   sudo systemctl start pigpiod")
    
    return 0

if __name__ == "__main__":
    sys.exit(run())