#!/usr/bin/env python3
"""
MFD Diagnostic Tool

This script tests the Multi-Function Display (MFD) components to identify issues.
It provides detailed diagnostics and attempts to fix common problems.
"""

import os
import sys
import time
import logging
import traceback
from pathlib import Path

# Add the parent directory to the path so we can import gwent modules
parent_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import gwent.hal
import gwent.hal.mfd
import gwent.hal.oled_ssd1306
import gwent.hal.rotary
import gwent.messaging.mfd
import gwent.messaging.choice

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mfd_diagnostic.log')
    ]
)

logger = logging.getLogger('mfd_diagnostic')

def test_display_initialization():
    """Test display initialization with different parameters"""
    logger.info("=== Testing Display Initialization ===")
    
    # Test different device/port combinations
    device_port_combinations = [
        (1, 0),  # Default in code
        # (0, 0),
        (0, 1),
        (1, 1)
    ]
    
    successful_combinations = []
    
    print("\n=== MFD Display Initialization Test ===")
    print("This test will try different device/port combinations for the display.")
    print("You will be prompted for feedback after each test.\n")
    
    for device, port in device_port_combinations:
        print(f"\nTesting device={device}, port={port}...")
        logger.info(f"Testing device={device}, port={port}")
        
        presenter = None
        try:
            presenter = gwent.hal.oled_ssd1306.SSD1306Presenter(device=device, port=port)
            logger.info(f"Successfully initialized with device={device}, port={port}")
            
            # Test basic display functionality
            presenter.clear()
            presenter.println(f"Test: dev={device}, port={port}")
            presenter.println("Line 1")
            presenter.println("Line 2")
            presenter.println("Line 3")
            presenter.term.flush()
            
            logger.info("Display test successful")
            
            # Ask for user feedback
            print("\nCheck the display. Do you see the test message?")
            print("1. Yes, display is working correctly")
            print("2. No, display is not working")
            print("3. Skip remaining tests")
            print("4. Exit test")
            
            while True:
                try:
                    response = input("Enter your choice (1-4): ").strip()
                    if response == '1':
                        logger.info("User confirmed display is working correctly")
                        successful_combinations.append((device, port))
                        break
                    elif response == '2':
                        logger.info("User reported display is not working")
                        break
                    elif response == '3':
                        logger.info("User chose to skip remaining tests")
                        # Clean up current display
                        if presenter:
                            presenter.clear()
                            presenter.term.flush()
                        return successful_combinations[0] if successful_combinations else None
                    elif response == '4':
                        logger.info("User chose to exit test")
                        sys.exit(0)
                    else:
                        print("Invalid choice. Please enter 1, 2, 3, or 4.")
                except KeyboardInterrupt:
                    logger.info("Test interrupted by user")
                    sys.exit(0)
                except Exception as e:
                    logger.error(f"Error getting user input: {e}")
                    break
            
            # Clean up
            if presenter:
                presenter.clear()
                presenter.term.flush()
            
        except Exception as e:
            logger.error(f"Failed with device={device}, port={port}: {e}")
            logger.debug(traceback.format_exc())
            print(f"Error: Failed to initialize display with device={device}, port={port}")
            print(f"Error details: {e}")
    
    if successful_combinations:
        logger.info(f"Successful combinations: {successful_combinations}")
        return successful_combinations[0]  # Return the first successful combination
    else:
        logger.error("All display initialization attempts failed")
        print("\nAll display initialization attempts failed.")
        return None

def test_font_loading():
    """Test font loading"""
    logger.info("=== Testing Font Loading ===")
    
    # Get the font directory
    font_dir = Path(gwent.hal.oled_ssd1306.__file__).resolve().parent.joinpath('fonts')
    logger.info(f"Font directory: {font_dir}")
    
    # Check if the directory exists
    if not font_dir.exists():
        logger.error(f"Font directory does not exist: {font_dir}")
        return False
    
    # Check for pixelmix.ttf
    pixelmix_path = font_dir.joinpath('pixelmix.ttf')
    if not pixelmix_path.exists():
        logger.error(f"pixelmix.ttf not found at: {pixelmix_path}")
        return False
    
    logger.info(f"pixelmix.ttf found at: {pixelmix_path}")
    
    # Test loading the font
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(str(pixelmix_path), 8)
        logger.info(f"Successfully loaded font: {font}")
        return True
    except Exception as e:
        logger.error(f"Failed to load font: {e}")
        logger.debug(traceback.format_exc())
        return False

def test_mfd_instance():
    """Test creating an MFD instance"""
    logger.info("=== Testing MFD Instance Creation ===")
    
    try:
        # Force real mode for testing
        original_mode = gwent.hal.real_mode
        gwent.hal.real_mode = lambda: True
        
        mfd_instance = gwent.hal.mfd.instance()
        logger.info(f"Successfully created MFD instance: {mfd_instance}")
        
        # Restore original mode function
        gwent.hal.real_mode = original_mode
        
        return mfd_instance
    except Exception as e:
        logger.error(f"Failed to create MFD instance: {e}")
        logger.debug(traceback.format_exc())
        return None

def test_mfd_display():
    """Test MFD display functionality"""
    logger.info("=== Testing MFD Display Functionality ===")
    
    try:
        # Force real mode for testing
        original_mode = gwent.hal.real_mode
        gwent.hal.real_mode = lambda: True
        
        mfd_instance = gwent.hal.mfd.instance()
        
        # Test error display
        logger.info("Testing error display")
        print("\nTesting error display...")
        error_msg = gwent.messaging.mfd.Message.with_error("Test Error Message")
        mfd_instance.present_error(error_msg, lambda delta, choice: None)
        
        print("\nDo you see the error message on the display?")
        print("1. Yes, continue to next test")
        print("2. No, skip to next test")
        print("3. Exit test")
        
        while True:
            try:
                response = input("Enter your choice (1-3): ").strip()
                if response == '1':
                    logger.info("User confirmed error display is working")
                    break
                elif response == '2':
                    logger.info("User reported error display is not working")
                    break
                elif response == '3':
                    logger.info("User chose to exit test")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                logger.info("Test interrupted by user")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error getting user input: {e}")
                break
        
        # Test prompt display
        logger.info("Testing prompt display")
        print("\nTesting prompt display...")
        prompt_msg = gwent.messaging.mfd.Message.with_prompt("Test Prompt", ok=True, cancel=True)
        
        # Create a non-blocking thread to select OK after a delay
        import threading
        def select_ok():
            time.sleep(5)  # Longer delay to give user time to observe
            # Simulate a button press by directly setting the stop event
            # This is a hack for testing only
            if hasattr(mfd_instance._chooser, '_stop_event'):
                mfd_instance._chooser._stop_event.set()
        
        threading.Thread(target=select_ok, daemon=True).start()
        
        print("\nThe display should now show a prompt with OK and Cancel options.")
        print("The test will automatically select OK after 5 seconds.")
        print("Please observe the display...")
        
        result = mfd_instance.present_prompt(prompt_msg, lambda delta, choice: None)
        logger.info(f"Prompt result: {result}")
        
        print("\nDid you see the prompt with OK and Cancel options?")
        print("1. Yes, continue to next test")
        print("2. No, skip to next test")
        print("3. Exit test")
        
        while True:
            try:
                response = input("Enter your choice (1-3): ").strip()
                if response == '1':
                    logger.info("User confirmed prompt display is working")
                    break
                elif response == '2':
                    logger.info("User reported prompt display is not working")
                    break
                elif response == '3':
                    logger.info("User chose to exit test")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                logger.info("Test interrupted by user")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error getting user input: {e}")
                break
        
        # Test choices display
        logger.info("Testing choices display")
        print("\nTesting choices display...")
        choices = [
            gwent.messaging.choice.Message.from_properties("1", "Option 1"),
            gwent.messaging.choice.Message.from_properties("2", "Option 2"),
            gwent.messaging.choice.Message.from_properties("3", "Option 3")
        ]
        choices_msg = gwent.messaging.mfd.Message.with_choices(choices)
        
        # Create a non-blocking thread to select an option after a delay
        def select_option():
            time.sleep(5)  # Longer delay to give user time to observe
            # Simulate a button press by directly setting the stop event
            if hasattr(mfd_instance._chooser, '_stop_event'):
                mfd_instance._chooser._stop_event.set()
        
        threading.Thread(target=select_option, daemon=True).start()
        
        print("\nThe display should now show a list of 3 options.")
        print("The test will automatically select an option after 5 seconds.")
        print("Please observe the display...")
        
        result = mfd_instance.present_choices(choices_msg, lambda delta, choice: None)
        logger.info(f"Choices result: {result}")
        
        print("\nDid you see the list of options?")
        print("1. Yes, all tests passed")
        print("2. No, choices display is not working")
        print("3. Exit test")
        
        success = False
        while True:
            try:
                response = input("Enter your choice (1-3): ").strip()
                if response == '1':
                    logger.info("User confirmed choices display is working")
                    success = True
                    break
                elif response == '2':
                    logger.info("User reported choices display is not working")
                    success = False
                    break
                elif response == '3':
                    logger.info("User chose to exit test")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                logger.info("Test interrupted by user")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error getting user input: {e}")
                break
        
        # Restore original mode function
        gwent.hal.real_mode = original_mode
        
        return success
    except Exception as e:
        logger.error(f"Failed to test MFD display: {e}")
        logger.debug(traceback.format_exc())
        return False

def fix_display_issues(device_port=None):
    """Apply fixes for common display issues"""
    logger.info("=== Applying Display Fixes ===")
    
    # 1. Fix the SSD1306Presenter initialization
    if device_port:
        device, port = device_port
        logger.info(f"Recommended device={device}, port={port} for SSD1306Presenter")
        
        # Print the code to use these parameters
        logger.info("Use the following code in gwent.hal.mfd.py:")
        logger.info(f"presenter = gwent.hal.oled_ssd1306.SSD1306Presenter(device={device}, port={port})")
    
    # 2. Check for font issues
    font_dir = Path(gwent.hal.oled_ssd1306.__file__).resolve().parent.joinpath('fonts')
    pixelmix_path = font_dir.joinpath('pixelmix.ttf')
    
    if not pixelmix_path.exists():
        logger.info("Font file missing. Attempting to copy from scripts/fonts directory")
        try:
            scripts_font_path = Path(parent_dir).joinpath('scripts', 'fonts', 'pixelmix.ttf')
            if scripts_font_path.exists():
                # Create fonts directory if it doesn't exist
                font_dir.mkdir(exist_ok=True)
                # Copy the font file
                import shutil
                shutil.copy(scripts_font_path, pixelmix_path)
                logger.info(f"Successfully copied font from {scripts_font_path} to {pixelmix_path}")
            else:
                logger.error(f"Font not found at {scripts_font_path}")
        except Exception as e:
            logger.error(f"Failed to copy font: {e}")
    
    # 3. Suggest display refresh improvements
    logger.info("Recommended display refresh improvements:")
    logger.info("1. Add a small delay after display operations")
    logger.info("2. Ensure contrast is set to maximum (255)")
    logger.info("3. Consider adding a display reset sequence at startup")

def test_font_loading_interactive():
    """Test font loading with user interaction"""
    logger.info("=== Testing Font Loading ===")
    print("\n=== Font Loading Test ===")
    
    result = test_font_loading()
    
    print("\nDo you want to continue to the next test?")
    print("1. Yes, continue testing")
    print("2. No, exit test")
    
    while True:
        try:
            response = input("Enter your choice (1-2): ").strip()
            if response == '1':
                logger.info("User chose to continue testing")
                return result
            elif response == '2':
                logger.info("User chose to exit test")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            return result

def test_mfd_instance_interactive():
    """Test creating an MFD instance with user interaction"""
    logger.info("=== Testing MFD Instance Creation ===")
    print("\n=== MFD Instance Creation Test ===")
    
    result = test_mfd_instance()
    
    print("\nDo you want to continue to the next test?")
    print("1. Yes, continue testing")
    print("2. No, exit test")
    
    while True:
        try:
            response = input("Enter your choice (1-2): ").strip()
            if response == '1':
                logger.info("User chose to continue testing")
                return result
            elif response == '2':
                logger.info("User chose to exit test")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            return result

def test_mfd_display_interactive():
    """Test MFD display functionality with user interaction"""
    logger.info("=== Testing MFD Display Functionality ===")
    print("\n=== MFD Display Functionality Test ===")
    print("This test will display various screens on the MFD.")
    print("You will be prompted for feedback after each test.\n")
    
    result = test_mfd_display()
    
    print("\nDid you see all the test screens (error, prompt, choices)?")
    print("1. Yes, all screens displayed correctly")
    print("2. No, some screens did not display correctly")
    
    while True:
        try:
            response = input("Enter your choice (1-2): ").strip()
            if response == '1':
                logger.info("User confirmed all screens displayed correctly")
                return True
            elif response == '2':
                logger.info("User reported some screens did not display correctly")
                return False
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            return result

def main():
    """Main diagnostic function"""
    logger.info("Starting MFD diagnostic tool")
    print("=== MFD Diagnostic Tool ===")
    print("This tool will help diagnose issues with the Multi-Function Display (MFD).")
    print("You will be guided through a series of tests and asked for feedback.\n")
    
    # Test display initialization
    device_port = test_display_initialization()
    
    # Test font loading
    font_ok = test_font_loading_interactive()
    
    # Test MFD instance creation
    mfd_instance = test_mfd_instance_interactive()
    
    # Test MFD display functionality if instance was created
    display_ok = False
    if mfd_instance:
        display_ok = test_mfd_display_interactive()
    
    # Apply fixes
    fix_display_issues(device_port)
    
    # Summary
    logger.info("=== Diagnostic Summary ===")
    print("\n=== Diagnostic Summary ===")
    
    logger.info(f"Display initialization: {'SUCCESS' if device_port else 'FAILED'}")
    print(f"Display initialization: {'SUCCESS' if device_port else 'FAILED'}")
    
    logger.info(f"Font loading: {'SUCCESS' if font_ok else 'FAILED'}")
    print(f"Font loading: {'SUCCESS' if font_ok else 'FAILED'}")
    
    logger.info(f"MFD instance creation: {'SUCCESS' if mfd_instance else 'FAILED'}")
    print(f"MFD instance creation: {'SUCCESS' if mfd_instance else 'FAILED'}")
    
    logger.info(f"MFD display functionality: {'SUCCESS' if display_ok else 'FAILED'}")
    print(f"MFD display functionality: {'SUCCESS' if display_ok else 'FAILED'}")
    
    if device_port and font_ok and mfd_instance and display_ok:
        logger.info("All tests PASSED!")
        print("\nAll tests PASSED!")
    else:
        logger.info("Some tests FAILED. See log for details and recommended fixes.")
        print("\nSome tests FAILED. See log for details and recommended fixes.")

if __name__ == "__main__":
    main()