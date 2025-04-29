"""
Display tests for the Gwent project.

This package contains scripts for testing OLED displays and LED matrix displays.
"""

def run_matrix_test():
    """
    Run the TCA9548A Matrix I2C test.
    This function is used as an entry point for the matrix-test, oled-direct-test,
    and display-diagnostic commands.
    """
    # Import the module with the hyphenated filename
    # We use importlib to handle the non-standard module name
    import importlib.util
    import os
    import sys
    
    # Get the directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to the module file
    module_path = os.path.join(current_dir, 'TCA9548A-MatrixI2C-test.py')
    
    # Load the module
    spec = importlib.util.spec_from_file_location('matrix_test_module', module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['matrix_test_module'] = module
    spec.loader.exec_module(module)
    
    # Call the run function from the module
    module.run()

def run_matrix_marquee():
    """
    Run the TCA9548A Matrix I2C marquee display.
    This function is used as an entry point for the matrix-marquee command.
    """
    # Import the module with the hyphenated filename
    # We use importlib to handle the non-standard module name
    import importlib.util
    import os
    import sys
    
    # Get the directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to the module file
    module_path = os.path.join(current_dir, 'TCA9548A-MatrixI2C-marquee.py')
    
    # Load the module
    spec = importlib.util.spec_from_file_location('matrix_marquee_module', module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['matrix_marquee_module'] = module
    spec.loader.exec_module(module)
    
    # Call the run function from the module
    module.run()