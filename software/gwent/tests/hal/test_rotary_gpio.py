import pytest
import time
import threading
import subprocess
import os

# Import the class to test
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, SimpleLogger

# Define GPIO pins to use for testing
# These should be connected to a real rotary encoder
A_PIN = 23  # GPIO23
B_PIN = 24  # GPIO24

@pytest.fixture(scope="session", autouse=True)
def manage_gwent_service():
    """
    Fixture to manage the gwent service during testing.
    Stops the service before tests and restarts it after tests.
    """
    # Stop the gwent service before running tests
    print("\nStopping gwent service before tests...")
    subprocess.run(["sudo", "systemctl", "stop", "gwent.service"], check=True)
    
    # Wait for the service to fully stop
    time.sleep(2)
    
    # Make sure GPIO pins are unexported before starting tests
    try:
        # Unexport pins if they're already exported
        for pin in [A_PIN, B_PIN]:
            gpio_path = f"/sys/class/gpio/gpio{pin}"
            if os.path.exists(gpio_path):
                with open("/sys/class/gpio/unexport", "w") as f:
                    f.write(str(pin))
                print(f"Unexported GPIO{pin}")
    except Exception as e:
        print(f"Error unexporting GPIO pins: {e}")
    
    # Yield control to the tests
    yield
    
    # Clean up any remaining GPIO exports
    try:
        for pin in [A_PIN, B_PIN]:
            gpio_path = f"/sys/class/gpio/gpio{pin}"
            if os.path.exists(gpio_path):
                with open("/sys/class/gpio/unexport", "w") as f:
                    f.write(str(pin))
                print(f"Unexported GPIO{pin}")
    except Exception as e:
        print(f"Error cleaning up GPIO pins: {e}")
    
    # Restart the gwent service after tests
    print("\nRestarting gwent service after tests...")
    subprocess.run(["sudo", "systemctl", "start", "gwent.service"], check=True)

class TestDirectGPIORotaryEncoder:
    """Tests for the DirectGPIORotaryEncoder class with real hardware"""
    
    @pytest.fixture
    def encoder(self):
        """Fixture to create an encoder instance with real GPIO pins"""
        # Create a callback to track rotations
        self.callback_called = False
        self.callback_direction = None
        
        def test_callback(direction):
            self.callback_called = True
            self.callback_direction = direction
        
        # Create the encoder with real pins
        encoder = DirectGPIORotaryEncoder(A_PIN, B_PIN, callback=test_callback)
        
        # Start the encoder
        encoder.start()
        
        # Yield for use in tests
        yield encoder
        
        # Cleanup after tests
        try:
            # Stop the encoder polling thread
            encoder.stop()
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def test_initialization(self):
        """Test that the encoder initializes correctly"""
        # Create encoder
        encoder = DirectGPIORotaryEncoder(A_PIN, B_PIN)
        
        # Check initial state
        assert encoder.a_pin == A_PIN
        assert encoder.b_pin == B_PIN
        assert encoder.counter == 0
        assert encoder.direction is None
        assert encoder.available is True
        assert encoder.running is False
        assert encoder.poll_thread is None
        
        # Cleanup
        try:
            # Make sure to clean up resources
            encoder.stop()
        except:
            pass
    
    def test_read_state(self, encoder):
        """Test the _read_state method returns a valid state"""
        # Read the current state - should be one of: 0, 1, 2, 3
        state = encoder._read_state()
        assert state in [0, 1, 2, 3]
    
    def test_reset(self, encoder):
        """Test the reset method"""
        # First manually rotate the encoder
        print("\nPlease rotate the encoder clockwise at least one click...")
        time.sleep(3)  # Give time for manual rotation
        
        # Get the current counter value
        counter_before = encoder.get_counter()
        
        # Reset the encoder
        encoder.reset()
        
        # Check that counter and direction are reset
        assert encoder.counter == 0
        assert encoder.direction is None
    
    def test_manual_rotation(self, encoder):
        """Test encoder responds to manual rotation"""
        # Reset state
        encoder.reset()
        self.callback_called = False
        self.callback_direction = None
        
        # Instruct user to rotate
        print("\nPlease rotate the encoder clockwise at least one click...")
        
        # Wait for rotation
        max_wait = 5  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if encoder.get_counter() != 0:
                break
            time.sleep(0.1)
        
        # Check that counter changed
        assert encoder.get_counter() != 0, "Encoder counter did not change. Please rotate the encoder."
        
        # Check that callback was called
        assert self.callback_called, "Callback was not called. Please rotate the encoder."
    
    def test_counter_direction(self, encoder):
        """Test that counter increases/decreases based on rotation direction"""
        # Reset state
        encoder.reset()
        
        # Instruct user to rotate clockwise
        print("\nPlease rotate the encoder clockwise at least one click...")
        time.sleep(3)  # Give time for manual rotation
        
        # Get counter after clockwise rotation
        clockwise_counter = encoder.get_counter()
        
        # Reset state
        encoder.reset()
        
        # Instruct user to rotate counter-clockwise
        print("\nPlease rotate the encoder counter-clockwise at least one click...")
        time.sleep(3)  # Give time for manual rotation
        
        # Get counter after counter-clockwise rotation
        counter_clockwise_counter = encoder.get_counter()
        
        # Check that directions are opposite
        # Note: We can't assert exact values since we don't know how many clicks the user will rotate
        if clockwise_counter != 0 and counter_clockwise_counter != 0:
            assert (clockwise_counter > 0 and counter_clockwise_counter < 0) or \
                   (clockwise_counter < 0 and counter_clockwise_counter > 0), \
                   "Encoder did not detect opposite directions correctly"
    
    def test_get_cycles(self, encoder):
        """Test the get_cycles method"""
        # Reset state
        encoder.reset()
        
        # Instruct user to rotate
        print("\nPlease rotate the encoder in either direction...")
        time.sleep(3)  # Give time for manual rotation
        
        # Get direction before calling get_cycles
        direction_before = encoder.direction
        
        # Only proceed if direction is not None (i.e., rotation occurred)
        if direction_before is not None:
            # Call get_cycles and check it returns the direction
            cycles = encoder.get_cycles()
            assert cycles in [-1, 1], f"Expected cycles to be -1 or 1, got {cycles}"
            
            # Check that direction is reset
            assert encoder.direction is None
            
            # Check that get_cycles returns 0 after direction is reset
            assert encoder.get_cycles() == 0