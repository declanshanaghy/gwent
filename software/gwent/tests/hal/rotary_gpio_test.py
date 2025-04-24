import pytest
import time
import threading
import logging
from unittest.mock import patch, MagicMock

# Import the class to test
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, DirectGPIOSwitch


class TestDirectGPIORotaryEncoderAutomated:
    """
    Tests for the DirectGPIORotaryEncoder class using the fallback implementation.
    These tests are fully automated and don't require real hardware.
    """
    
    @pytest.fixture
    def encoder(self):
        """Fixture to create an encoder instance with fallback implementation"""
        # Create a callback to track rotations
        self.callback_called = False
        self.callback_direction = None
        
        def test_callback(direction):
            self.callback_called = True
            self.callback_direction = direction
        
        # Mock os.path.exists to force fallback implementation
        with patch('os.path.exists', return_value=False):
            # Create the encoder with test pins
            encoder = DirectGPIORotaryEncoder(23, 24, callback=test_callback)
            
            # Start the encoder
            encoder.start()
            
            # Yield for use in tests
            yield encoder
            
            # Cleanup after tests
            encoder.stop()
    
    def test_initialization(self):
        """Test that the encoder initializes correctly with fallback implementation"""
        # Mock os.path.exists to force fallback implementation
        with patch('os.path.exists', return_value=False):
            # Create encoder
            encoder = DirectGPIORotaryEncoder(23, 24)
            
            # Check initial state
            assert encoder.a_pin == 23
            assert encoder.b_pin == 24
            assert encoder.counter == 0
            assert encoder.direction is None
            assert encoder.available is True
            assert encoder.running is False
            assert encoder.poll_thread is None
            assert encoder.use_sysfs is False
            
            # Cleanup
            encoder.stop()
    
    def test_read_state(self, encoder):
        """Test the _read_state method returns a valid state"""
        # Read the current state - should be one of: 0, 1, 2, 3
        state = encoder._read_state()
        assert state in [0, 1, 2, 3]
    
    def test_reset(self, encoder):
        """Test the reset method"""
        # Wait for the fallback implementation to simulate a rotation
        time.sleep(2.5)
        
        # Get the current counter value (should be non-zero after simulation)
        counter_before = encoder.get_counter()
        assert counter_before != 0, "Counter should have changed after simulated rotation"
        
        # Reset the encoder
        encoder.reset()
        
        # Check that counter and direction are reset
        assert encoder.get_counter() == 0
        assert encoder.get_direction() is None
    
    def test_automated_rotation(self, encoder):
        """Test encoder responds to simulated rotation"""
        # Reset state
        encoder.reset()
        self.callback_called = False
        self.callback_direction = None
        
        # Wait for the fallback implementation to simulate a rotation
        time.sleep(2.5)
        
        # Check that counter changed
        assert encoder.get_counter() != 0, "Encoder counter did not change after simulated rotation"
        
        # Check that callback was called
        assert self.callback_called, "Callback was not called after simulated rotation"
        assert self.callback_direction is not None, "Callback direction was not set"
    
    def test_counter_direction(self, encoder):
        """Test that counter increases/decreases based on rotation direction"""
        # Reset state
        encoder.reset()
        
        # Wait for the fallback implementation to simulate a clockwise rotation
        time.sleep(2.5)
        
        # Get counter after clockwise rotation
        clockwise_counter = encoder.get_counter()
        assert clockwise_counter > 0, "Counter should be positive after clockwise rotation"
        
        # Reset state
        encoder.reset()
        
        # Wait for the fallback implementation to simulate a counter-clockwise rotation
        # The fallback implementation is designed to simulate counter-clockwise after a reset
        time.sleep(2.5)
        
        # Get counter after counter-clockwise rotation
        counter_clockwise_counter = encoder.get_counter()
        assert counter_clockwise_counter < 0, "Counter should be negative after counter-clockwise rotation"
    
    def test_get_cycles(self, encoder):
        """Test the get_cycles method"""
        # Reset state
        encoder.reset()
        
        # Wait for the fallback implementation to simulate a rotation
        time.sleep(2.5)
        
        # Get direction before calling get_cycles
        direction_before = encoder.get_direction()
        assert direction_before is not None, "Direction should not be None after simulated rotation"
        
        # Call get_cycles and check it returns the direction
        cycles = encoder.get_cycles()
        assert cycles in [-1, 1], f"Expected cycles to be -1 or 1, got {cycles}"
        
        # Check that direction is reset
        assert encoder.get_direction() is None
        
        # Check that get_cycles returns 0 after direction is reset
        assert encoder.get_cycles() == 0
    
    def test_process_state_change(self):
        """Test the _process_state_change method directly"""
        # Mock os.path.exists to force fallback implementation
        with patch('os.path.exists', return_value=False):
            # Create encoder without starting it
            encoder = DirectGPIORotaryEncoder(23, 24)
            
            # Set initial state
            encoder.last_state = 0b00
            
            # Test clockwise rotation sequence
            # 00 -> 01 -> 11 -> 10 -> 00
            encoder._process_state_change(0b01)
            assert encoder.direction == 1
            
            encoder._process_state_change(0b11)
            assert encoder.direction == 1
            
            encoder._process_state_change(0b10)
            assert encoder.direction == 1
            
            encoder._process_state_change(0b00)
            assert encoder.direction == 1
            assert encoder.counter == 1
            
            # Reset
            encoder.reset()
            
            # Test counter-clockwise rotation sequence
            # 00 -> 10 -> 11 -> 01 -> 00
            encoder.last_state = 0b00
            
            encoder._process_state_change(0b10)
            assert encoder.direction == -1
            
            encoder._process_state_change(0b11)
            assert encoder.direction == -1
            
            encoder._process_state_change(0b01)
            assert encoder.direction == -1
            
            encoder._process_state_change(0b00)
            assert encoder.direction == -1
            assert encoder.counter == -1
            
            # Cleanup
            encoder.stop()


class TestDirectGPIOSwitch:
    """Tests for the DirectGPIOSwitch class using the fallback implementation"""
    
    @pytest.fixture
    def switch(self):
        """Fixture to create a switch instance with fallback implementation"""
        # Mock os.path.exists to force fallback implementation
        with patch('os.path.exists', return_value=False):
            # Create the switch with a test pin
            switch = DirectGPIOSwitch(25)
            
            # Yield for use in tests
            yield switch
    
    def test_initialization(self):
        """Test that the switch initializes correctly with fallback implementation"""
        # Mock os.path.exists to force fallback implementation
        with patch('os.path.exists', return_value=False):
            # Create switch
            switch = DirectGPIOSwitch(25)
            
            # Check initial state
            assert switch.pin == 25
            assert switch.available is True
            assert switch.use_sysfs is False
    
    def test_get_state(self, switch):
        """Test the get_state method"""
        # By default, the switch is pulled up (not pressed)
        assert switch.get_state() is False
        
        # Simulate pressing the switch by changing the pin state
        switch._pin_state = 0
        assert switch.get_state() is True
        
        # Simulate releasing the switch
        switch._pin_state = 1
        assert switch.get_state() is False


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])