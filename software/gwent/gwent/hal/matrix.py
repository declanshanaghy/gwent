import threading
import time
import sys
import os

import gwent.game
import gwent.hal

# Import the necessary libraries for the matrix display
try:
    import qwiic_tca9548a
    import board
    import busio
    import adafruit_is31fl3731
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    
# Default configuration
DEFAULT_MUX_ADDRESS = 0x70
DEFAULT_MATRIX_ADDRESS = 0x74
DEFAULT_MATRIX_CHANNEL = 0  # Default channel for the score display
DEFAULT_BRIGHTNESS = 50      # Default brightness level (0-255)


def instance():
    """
    Get an instance of the matrix display.
    Returns a _RealMatrix if in real mode and hardware is available,
    otherwise returns a _FakeMatrix.
    """
    if gwent.hal.real_mode() and HARDWARE_AVAILABLE:
        return _RealMatrix()
    else:
        return _FakeMatrix()


class _FakeMatrix(gwent.game.BaseComponent):
    def display_score(self, score: int):
        self._log.info({
            'action': 'display score',
            'score': score
        })


class _RealMatrix(gwent.game.BaseComponent):
    def __init__(self, mux_address=DEFAULT_MUX_ADDRESS,
                 matrix_address=DEFAULT_MATRIX_ADDRESS, channel=DEFAULT_MATRIX_CHANNEL):
        """
        Initialize the _RealMatrix class.
        
        Args:
            mux_address: I2C address of the TCA9548A multiplexer
            matrix_address: I2C address of the IS31FL3731 matrix
            channel: Channel on the multiplexer where the matrix is connected
        """
        super().__init__()
        self._log_verbose = False
        self._mux_address = mux_address
        self._matrix_address = matrix_address
        self._channel = channel
        self._mux = None
        self._matrix = None
        self._i2c = None
        self._initialized = False
        
    def init(self):
        """Initialize the matrix display hardware"""
        super().init()
        
        if not HARDWARE_AVAILABLE:
            self._log.warning("Hardware libraries not available, matrix display will not function")
            return
            
        try:
            self._log.info("Initializing matrix display hardware")
            
            # Initialize the multiplexer
            self._log.info(f"Initializing TCA9548A multiplexer at address 0x{self._mux_address:02x}")
            self._mux = qwiic_tca9548a.QwiicTCA9548A(address=self._mux_address)
            
            if not self._mux.is_connected():
                self._log.error("TCA9548A multiplexer not found!")
                return
                
            # Initialize the I2C bus
            self._log.info("Initializing I2C bus")
            self._i2c = busio.I2C(board.SCL, board.SDA)
            
            # Enable the channel for the matrix
            self._log.info(f"Enabling channel {self._channel}")
            self._mux.disable_all()
            self._mux.enable_channels(self._channel)
            
            # Initialize the matrix
            self._log.info(f"Initializing IS31FL3731 matrix at address 0x{self._matrix_address:02x}")
            self._matrix = adafruit_is31fl3731.IS31FL3731(self._i2c, address=self._matrix_address)
            
            # Clear the display
            self._log.info("Clearing display")
            self.clear()
            
            self._initialized = True
            self._log.info("Matrix display initialized successfully")
            
        except Exception as e:
            self._log.error(f"Error initializing matrix display: {e}")
            import traceback
            self._log.error(f"Traceback: {traceback.format_exc()}")
            self._initialized = False
    
    def shutdown(self):
        """Shutdown the matrix display hardware"""
        if self._initialized:
            try:
                self._log.info("Shutting down matrix display")
                self.clear()
                if self._mux:
                    self._mux.disable_all()
            except Exception as e:
                self._log.error(f"Error shutting down matrix display: {e}")
        super().shutdown()
    
    def clear(self):
        """Clear the display"""
        if not self._initialized:
            return
            
        try:
            # Clear all pixels on the matrix
            for x in range(self._matrix.width):
                for y in range(self._matrix.height):
                    self._matrix.pixel(x, y, 0)
            self._log.info("Display cleared")
        except Exception as e:
            self._log.error(f"Error clearing display: {e}")
    
    def display_score(self, score: int):
        """
        Display a score on the matrix display.
        
        Args:
            score: The score to display
        """
        self._log.info({
            'action': 'display score',
            'score': score
        })
        
        # Always print the score for debugging purposes
        print(f'Player Total Score: {score}')
        
        if not self._initialized:
            self._log.warning("Matrix display not initialized, cannot display score")
            return
            
        try:
            # Clear the display first
            self.clear()
            
            # Enable the channel for the matrix
            self._mux.disable_all()
            self._mux.enable_channels(self._channel)
            
            # Convert the score to a string
            score_str = str(score)
            
            # Draw the score on the display
            self.draw_text(score_str, DEFAULT_BRIGHTNESS)
            
        except Exception as e:
            self._log.error(f"Error displaying score: {e}")
    
    def draw_text(self, text, brightness=DEFAULT_BRIGHTNESS):
        """
        Draw text on the display.
        
        Args:
            text: The text to display
            brightness: The brightness level (0-255)
        """
        if not self._initialized:
            return
            
        try:
            # Clear the display first
            self.clear()
            
            # Simple approach - just draw digits one by one
            # This is a very basic implementation that only works for small displays
            # and short text (like scores)
            
            # Calculate starting position to center the text
            char_width = 4  # Each character is about 4 pixels wide
            spacing = 1     # 1 pixel spacing between characters
            total_width = len(text) * (char_width + spacing) - spacing
            start_x = max(0, (self._matrix.width - total_width) // 2)
            
            # Draw each character
            x = start_x
            for char in text:
                self._draw_digit(char, x, brightness)
                x += char_width + spacing
                
        except Exception as e:
            self._log.error(f"Error drawing text: {e}")
    
    def _draw_digit(self, digit, x_offset, brightness=DEFAULT_BRIGHTNESS):
        """
        Draw a single digit on the display.
        
        Args:
            digit: The digit to draw (0-9)
            x_offset: The x position to start drawing
            brightness: The brightness level (0-255)
        """
        if not self._initialized:
            return
            
        try:
            # Simple patterns for digits 0-9
            patterns = {
                '0': [
                    [1, 1, 1],
                    [1, 0, 1],
                    [1, 0, 1],
                    [1, 0, 1],
                    [1, 1, 1]
                ],
                '1': [
                    [0, 1, 0],
                    [1, 1, 0],
                    [0, 1, 0],
                    [0, 1, 0],
                    [1, 1, 1]
                ],
                '2': [
                    [1, 1, 1],
                    [0, 0, 1],
                    [1, 1, 1],
                    [1, 0, 0],
                    [1, 1, 1]
                ],
                '3': [
                    [1, 1, 1],
                    [0, 0, 1],
                    [0, 1, 1],
                    [0, 0, 1],
                    [1, 1, 1]
                ],
                '4': [
                    [1, 0, 1],
                    [1, 0, 1],
                    [1, 1, 1],
                    [0, 0, 1],
                    [0, 0, 1]
                ],
                '5': [
                    [1, 1, 1],
                    [1, 0, 0],
                    [1, 1, 1],
                    [0, 0, 1],
                    [1, 1, 1]
                ],
                '6': [
                    [1, 1, 1],
                    [1, 0, 0],
                    [1, 1, 1],
                    [1, 0, 1],
                    [1, 1, 1]
                ],
                '7': [
                    [1, 1, 1],
                    [0, 0, 1],
                    [0, 1, 0],
                    [1, 0, 0],
                    [1, 0, 0]
                ],
                '8': [
                    [1, 1, 1],
                    [1, 0, 1],
                    [1, 1, 1],
                    [1, 0, 1],
                    [1, 1, 1]
                ],
                '9': [
                    [1, 1, 1],
                    [1, 0, 1],
                    [1, 1, 1],
                    [0, 0, 1],
                    [1, 1, 1]
                ]
            }
            
            # Get the pattern for this digit
            pattern = patterns.get(digit, patterns.get('0'))
            
            # Calculate vertical position to center the digit
            y_offset = (self._matrix.height - len(pattern)) // 2
            
            # Draw the pattern
            for y, row in enumerate(pattern):
                for x, pixel in enumerate(row):
                    if pixel:
                        self._matrix.pixel(x_offset + x, y_offset + y, brightness)
                        
        except Exception as e:
            self._log.error(f"Error drawing digit: {e}")
    
    def draw_border(self, brightness=DEFAULT_BRIGHTNESS):
        """
        Draw a border around the edge of the display.
        
        Args:
            brightness: The brightness level (0-255)
        """
        if not self._initialized:
            return
            
        try:
            # First draw the top and bottom edges
            for x in range(self._matrix.width):
                self._matrix.pixel(x, 0, brightness)
                self._matrix.pixel(x, self._matrix.height - 1, brightness)
                
            # Now draw the left and right edges
            for y in range(self._matrix.height):
                self._matrix.pixel(0, y, brightness)
                self._matrix.pixel(self._matrix.width - 1, y, brightness)
                
        except Exception as e:
            self._log.error(f"Error drawing border: {e}")
    
    def set_brightness(self, brightness):
        """
        Set the global brightness level for the display.
        
        Args:
            brightness: The brightness level (0-255)
        """
        if not self._initialized:
            return
            
        try:
            # This is a simple implementation that doesn't actually change
            # the global brightness, but it could be implemented if the
            # hardware supports it
            self._log.info(f"Setting brightness to {brightness}")
        except Exception as e:
            self._log.error(f"Error setting brightness: {e}")
    
    def display_animation(self, frames, delay=0.1):
        """
        Display an animation on the matrix.
        
        Args:
            frames: A list of frames, where each frame is a list of (x, y, brightness) tuples
            delay: The delay between frames in seconds
        """
        if not self._initialized:
            return
            
        try:
            for frame in frames:
                # Clear the display
                self.clear()
                
                # Draw the frame
                for x, y, brightness in frame:
                    self._matrix.pixel(x, y, brightness)
                
                # Wait for the specified delay
                time.sleep(delay)
                
        except Exception as e:
            self._log.error(f"Error displaying animation: {e}")
    
    def display_score_animation(self, score: int, old_score: int = None):
        """
        Display an animation when the score changes.
        
        Args:
            score: The new score
            old_score: The old score (if None, no animation is shown)
        """
        if not self._initialized:
            self._log.warning("Matrix display not initialized, cannot display score animation")
            return
            
        try:
            # If no old score is provided, just display the score
            if old_score is None:
                self.display_score(score)
                return
                
            # If the score hasn't changed, just display it
            if score == old_score:
                self.display_score(score)
                return
                
            # Determine if the score increased or decreased
            increased = score > old_score
            
            # Create a simple animation
            if increased:
                # Flash the border to indicate score increase
                for _ in range(3):
                    self.clear()
                    time.sleep(0.1)
                    self.draw_border(brightness=100)
                    time.sleep(0.1)
            else:
                # Fade out to indicate score decrease
                for brightness in range(100, 0, -20):
                    self.clear()
                    self.draw_border(brightness=brightness)
                    time.sleep(0.1)
            
            # Display the new score
            self.display_score(score)
            
        except Exception as e:
            self._log.error(f"Error displaying score animation: {e}")
            # Fall back to just displaying the score
            self.display_score(score)
