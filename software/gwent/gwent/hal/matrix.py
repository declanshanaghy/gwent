import threading
import time
import sys
import os

import gwent.game
import gwent.hal

# Import the necessary libraries for the matrix display
import qwiic_tca9548a
import board
import busio
import adafruit_is31fl3731

# Default configuration
DEFAULT_MUX_ADDRESS = 0x70
DEFAULT_MATRIX_ADDRESS = 0x74
DEFAULT_BRIGHTNESS = 10      # Default brightness level (0-255)

MATRIX_CHANNEL_DEFAULT=7 # Nothing connected to this channel
MATRIX_CHANNEL_PLAYER_ROUND_KEEPER = 0
MATRIX_CHANNEL_PLAYER_ONE = 1
MATRIX_CHANNEL_PLAYER_TWO = 2

def instance(channel):
    """
    Get an instance of the matrix display.
    Returns a _RealMatrix if in real mode and hardware is available,
    otherwise returns a _FakeMatrix.
    """
    if gwent.hal.real_mode():
        return _RealMatrix(channel=channel)
    else:
        return _FakeMatrix()


class _FakeMatrix(gwent.game.BaseComponent):
    def display_score(self, score: int):
        self._log.info({
            'action': 'display score',
            'score': score
        })

    def display_round_scores(self, plr1_score: int, plr2_score: int):
        self._log.info({
            'action': 'display round scores',
            'plr1_score': plr1_score,
            'plr2_score': plr2_score
        })

    def display_gems(self, gems: int):
        self._log.info({'action': 'display gems', 'gems': gems})

    def display_gem_pair(self, p1_gems: int, p2_gems: int):
        self._log.info({'action': 'display gem pair', 'p1_gems': p1_gems, 'p2_gems': p2_gems})

    def init(self): pass
    def shutdown(self): pass
    def clear(self): pass
    def display_centered_score(self, score, player=None): pass


class _RealMatrix(gwent.game.BaseComponent):
    def __init__(self, mux_address=DEFAULT_MUX_ADDRESS,
                 matrix_address=DEFAULT_MATRIX_ADDRESS, channel=MATRIX_CHANNEL_DEFAULT):
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
        
        self.take_control()
        
        # Initialize the matrix
        self._log.info(f"Initializing IS31FL3731 matrix at address 0x{self._matrix_address:02x}")
        self._matrix = adafruit_is31fl3731.IS31FL3731(self._i2c, address=self._matrix_address)
        
        # Clear the display
        self._log.info("Clearing display")
        self.clear()
        
        self._initialized = True
        self._log.info("Matrix display initialized successfully")
    
    def take_control(self):
        # This will need to use a mutex eventually
        # Enable the channel for the matrix
        self._log.info(f"Enabling channel {self._channel}")
        self._mux.disable_all()
        self._mux.enable_channels(self._channel)
        

    def shutdown(self):
        """Shutdown the matrix display hardware"""
        if self._initialized:
            try:
                self._log.info("Shutting down matrix display")
                self.take_control()
                self.clear()
                if self._mux:
                    self._mux.disable_all()
            except Exception as e:
                self._log.error(f"Error shutting down matrix display: {e}")
    
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
            # Convert the score to a string
            score_str = str(score)
            
            # Clear the display first
            self.take_control()
            self.clear()
            
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
            # Larger patterns for digits 0-9 (4x6 instead of 3x5)
            patterns = {
                '0': [
                    [1, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1]
                ],
                '1': [
                    [0, 0, 1, 0],
                    [0, 1, 1, 0],
                    [1, 0, 1, 0],
                    [0, 0, 1, 0],
                    [0, 0, 1, 0],
                    [1, 1, 1, 1]
                ],
                '2': [
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1],
                    [1, 1, 1, 1],
                    [1, 0, 0, 0],
                    [1, 1, 1, 1]
                ],
                '3': [
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1],
                    [1, 1, 1, 1]
                ],
                '4': [
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1]
                ],
                '5': [
                    [1, 1, 1, 1],
                    [1, 0, 0, 0],
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1],
                    [1, 1, 1, 1]
                ],
                '6': [
                    [1, 1, 1, 1],
                    [1, 0, 0, 0],
                    [1, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1]
                ],
                '7': [
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 1, 0],
                    [0, 1, 0, 0],
                    [1, 0, 0, 0],
                    [1, 0, 0, 0]
                ],
                '8': [
                    [1, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1]
                ],
                '9': [
                    [1, 1, 1, 1],
                    [1, 0, 0, 1],
                    [1, 1, 1, 1],
                    [0, 0, 0, 1],
                    [0, 0, 0, 1],
                    [1, 1, 1, 1]
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
            
    def display_round_scores(self, plr1_score: int, plr2_score: int):
        """
        Display round scores for both players using maximum display space.
        Player 1 score pinned to top left corner, Player 2 score pinned to top right corner.
        
        Args:
            plr1_score: Round score for player 1 (displayed on the left)
            plr2_score: Round score for player 2 (displayed on the right)
        """
        self._log.info({
            'action': 'display round scores',
            'plr1_score': plr1_score,
            'plr2_score': plr2_score
        })
        
        # Always print the scores for debugging purposes
        print(f'Player 1 Score: {plr1_score}, Player 2 Score: {plr2_score}')
        
        if not self._initialized:
            self._log.warning("Matrix display not initialized, cannot display player scores")
            return
            
        try:
            # Log display dimensions
            self._log.info(f"Display dimensions: {self._matrix.width}x{self._matrix.height}")
            
            # Convert scores to strings
            plr1_str = str(plr1_score)
            plr2_str = str(plr2_score)
            self._log.info(f"Displaying scores: Player 1: '{plr1_str}', Player 2: '{plr2_str}'")
            
            # Clear the display first
            self.take_control()
            self.clear()
            
            # Draw player 1 score pinned to the top left corner
            self._log.info("Drawing Player 1 score in top left corner")
            
            # Position at left, vertically centered
            plr1_x = 0
            plr1_y = (self._matrix.height - 7) // 2
            
            # Draw player 1 score
            for char in plr1_str:
                pattern = self._get_digit_pattern(char)
                for y, row in enumerate(pattern):
                    for x, pixel in enumerate(row):
                        if pixel:
                            self._matrix.pixel(plr1_x + x, plr1_y + y, DEFAULT_BRIGHTNESS)
                # We only display the first digit since we're using the full 7x7 space
                break
            
            # Draw player 2 score pinned to the top right corner
            self._log.info("Drawing Player 2 score in top right corner")
            
            # Position at right, vertically centered
            plr2_x = self._matrix.width - 7  # 7 is the width of our digit pattern
            plr2_y = (self._matrix.height - 7) // 2
            
            # Draw player 2 score
            for char in plr2_str:
                pattern = self._get_digit_pattern(char)
                for y, row in enumerate(pattern):
                    for x, pixel in enumerate(row):
                        if pixel:
                            self._matrix.pixel(plr2_x + x, plr2_y + y, DEFAULT_BRIGHTNESS)
                # We only display the first digit since we're using the full 7x7 space
                break
            
            self._matrix.fade(fade_in=500, fade_out=500, pause=4.0)
                
        except Exception as e:
            self._log.error(f"Error displaying round scores: {e}", exc_info=True)
            # Try to display a simple fallback
            try:
                self.clear()
                # Draw a simple representation of the scores
                self._matrix.pixel(0, 0, DEFAULT_BRIGHTNESS)  # Top left for player 1
                self._matrix.pixel(self._matrix.width - 1, 0, DEFAULT_BRIGHTNESS)  # Top right for player 2
            except Exception as fallback_error:
                self._log.error(f"Fallback display also failed: {fallback_error}")
    
    def display_centered_score(self, score: int, player: str = None):
        """
        Display a score centered on the display with dots below it.
        Uses slimmer 7x4 pixel patterns and can display up to 3 digits.
        The number of dots displayed depends on the player parameter.
        
        Args:
            score: The score to display
            player: The player identifier (e.g., "player1", "player2")
                   Determines how many dots are displayed below the digit
        """
        self._log.info({
            'action': 'display centered score',
            'score': score
        })
        
        # Always print the score for debugging purposes
        print(f'Centered Score: {score}')
        
        if not self._initialized:
            self._log.warning("Matrix display not initialized, cannot display centered score")
            return
            
        try:
            # Convert score to string and limit to 3 digits
            score_str = str(score)
            if len(score_str) > 3:
                score_str = score_str[:3]
            
            # Clear the display first
            self.take_control()
            self.clear()
            
            # Log display dimensions
            width = self._matrix.width
            height = self._matrix.height
            self._log.info(f"Display dimensions: {width}x{height}")
            
            # 9x5 patterns to fill the full display height
            slim_patterns = {
                '0': [
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0]
                ],
                '1': [
                    [0,0,1,0,0],
                    [0,1,1,0,0],
                    [1,0,1,0,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [1,1,1,1,1]
                ],
                '2': [
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [0,0,0,0,1],
                    [0,0,0,1,0],
                    [0,0,1,0,0],
                    [0,1,0,0,0],
                    [1,0,0,0,0],
                    [1,0,0,0,0],
                    [1,1,1,1,1]
                ],
                '3': [
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [0,0,1,1,0],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0]
                ],
                '4': [
                    [0,0,0,1,0],
                    [0,0,1,1,0],
                    [0,1,0,1,0],
                    [1,0,0,1,0],
                    [1,1,1,1,1],
                    [0,0,0,1,0],
                    [0,0,0,1,0],
                    [0,0,0,1,0],
                    [0,0,0,1,0]
                ],
                '5': [
                    [1,1,1,1,1],
                    [1,0,0,0,0],
                    [1,0,0,0,0],
                    [1,1,1,1,0],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0]
                ],
                '6': [
                    [0,1,1,1,0],
                    [1,0,0,0,0],
                    [1,0,0,0,0],
                    [1,0,0,0,0],
                    [1,1,1,1,0],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0]
                ],
                '7': [
                    [1,1,1,1,1],
                    [0,0,0,0,1],
                    [0,0,0,1,0],
                    [0,0,0,1,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [0,1,0,0,0],
                    [0,1,0,0,0],
                    [0,1,0,0,0]
                ],
                '8': [
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,0]
                ],
                '9': [
                    [0,1,1,1,0],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [1,0,0,0,1],
                    [0,1,1,1,1],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [0,0,0,0,1],
                    [0,1,1,1,0]
                ]
            }

            # Calculate dimensions for the entire score display
            digit_width = 5  # 5 pixels wide
            digit_height = 9  # 9 pixels high (full display)
            digit_spacing = 1  # 1 pixel spacing between digits
            
            # Calculate total width needed for all digits with spacing
            total_width = len(score_str) * digit_width + (len(score_str) - 1) * digit_spacing
            
            # Calculate starting position to center the entire score
            start_x = (width - total_width) // 2
            center_y = (height - digit_height) // 2
            
            self._log.info(f"Centering score '{score_str}' at position: ({start_x}, {center_y})")
            
            # Draw each digit of the score
            x = start_x
            for digit in score_str:
                pattern = slim_patterns.get(digit, slim_patterns.get('0'))
                
                # Draw the digit
                for y, row in enumerate(pattern):
                    for x_rel, pixel in enumerate(row):
                        if pixel:
                            self._matrix.pixel(x + x_rel, center_y + y, DEFAULT_BRIGHTNESS)
                
                # Move to the next digit position
                x += digit_width + digit_spacing
            
        except Exception as e:
            self._log.error(f"Error displaying centered score: {e}", exc_info=True)
            # Try to display a simple fallback
            try:
                self.clear()
                # Draw a simple representation of the score
                self._matrix.pixel(self._matrix.width // 2, self._matrix.height // 2, DEFAULT_BRIGHTNESS)
            except Exception as fallback_error:
                self._log.error(f"Fallback display also failed: {fallback_error}")
                
    def display_gems(self, gems: int):
        """Display gem icons on the matrix. Each gem is a 5x5 diamond shape.
        Up to 2 gems side by side on the 16x9 display."""
        self._log.info({'action': 'display_gems', 'gems': gems})
        print(f'Gems: {gems}')

        if not self._initialized:
            return

        try:
            self.take_control()
            self.clear()
            self._draw_gems(gems, x_offset=0, width=self._matrix.width)
        except Exception as e:
            self._log.error(f"Error displaying gems: {e}", exc_info=True)

    def display_gem_pair(self, p1_gems: int, p2_gems: int):
        """Display gems for both players side by side on a 16x9 display.
        P1 gems on the left half, P2 gems on the right half.
        A dot below P1 side, two dots below P2 side."""
        self._log.info({'action': 'display_gem_pair', 'p1_gems': p1_gems, 'p2_gems': p2_gems})
        print(f'Gems: P1={p1_gems}, P2={p2_gems}')

        if not self._initialized:
            return

        try:
            self.take_control()
            self.clear()

            mid = self._matrix.width // 2  # 8

            # P1 gems on left half
            self._draw_gems(p1_gems, x_offset=0, width=mid)

            # P2 gems on right half
            self._draw_gems(p2_gems, x_offset=mid, width=mid)

        except Exception as e:
            self._log.error(f"Error displaying gem pair: {e}", exc_info=True)

    def _draw_gems(self, gems, x_offset, width):
        """Draw gem diamonds within a horizontal region.
        Two gems are staggered vertically so they don't look like a flat row."""
        # 5x5 diamond
        diamond = [
            [0,0,1,0,0],
            [0,1,1,1,0],
            [1,1,1,1,1],
            [0,1,1,1,0],
            [0,0,1,0,0],
        ]
        gem_w = 5
        gem_h = 5

        gems = max(0, min(gems, 2))
        if gems == 0:
            return

        if gems == 1:
            # Center gem in region
            x = x_offset + (width - gem_w) // 2
            y = (self._matrix.height - gem_h) // 2
            for dy, row in enumerate(diamond):
                for dx, val in enumerate(row):
                    if val:
                        self._matrix.pixel(x + dx, y + dy, DEFAULT_BRIGHTNESS)
        elif gems == 2:
            # Stack vertically since side-by-side won't fit with 5px wide gems
            # in a 7-8px wide region. Offset horizontally for visual interest.
            y_top = 0
            y_bot = 4
            x_left = x_offset + (width - gem_w) // 2 - 1
            x_right = x_offset + (width - gem_w) // 2 + 1
            # Clamp to bounds
            x_left = max(x_offset, x_left)
            x_right = min(x_offset + width - gem_w, x_right)
            for x, y in [(x_left, y_top), (x_right, y_bot)]:
                for dy, row in enumerate(diamond):
                    for dx, val in enumerate(row):
                        if val:
                            self._matrix.pixel(x + dx, y + dy, DEFAULT_BRIGHTNESS)

    def _get_digit_pattern(self, digit):
        """
        Get the pattern for a digit.
        
        Args:
            digit: The digit to get the pattern for (0-9)
            
        Returns:
            The pattern for the digit (7x7 pixels with lines max 2 pixels thick)
        """

        # No spaces between commas and digits in patterns so it's more visually appealing
        patterns = {
            '0': [
                [0,1,1,1,1,1,0],
                [1,0,0,0,0,0,1],
                [1,0,0,0,0,0,1],
                [1,0,0,0,0,0,1],
                [1,0,0,0,0,0,1],
                [1,0,0,0,0,0,1],
                [0,1,1,1,1,1,0]
            ],
            '1': [
                [0,0,0,1,0,0,0],
                [0,0,1,1,0,0,0],
                [0,1,0,1,0,0,0],
                [0,0,0,1,0,0,0],
                [0,0,0,1,0,0,0],
                [0,0,0,1,0,0,0],
                [0,1,1,1,1,1,0]
            ],
            '2': [
                [0,1,1,1,1,1,0],
                [1,1,0,0,0,1,1],
                [0,0,0,0,0,1,0],
                [0,0,1,1,1,0,0],
                [0,1,0,0,0,0,0],
                [1,0,0,0,0,0,0],
                [1,1,1,1,1,1,1]
            ],
            '3': [
                [0,1,1,1,1,1,0],
                [1,1,0,0,0,1,1],
                [0,0,0,0,0,1,0],
                [0,0,1,1,1,1,0],
                [0,0,0,0,0,1,0],
                [1,1,0,0,0,1,1],
                [0,1,1,1,1,1,0]
            ],
            '4': [
                [0,0,0,1,1,0,0],
                [0,0,1,0,1,0,0],
                [0,1,0,0,1,0,0],
                [1,0,0,0,1,0,0],
                [1,1,1,1,1,1,1],
                [0,0,0,0,1,0,0],
                [0,0,0,0,1,0,0]
            ],
            '5': [
                [1,1,1,1,1,1,1],
                [1,0,0,0,0,0,0],
                [1,0,0,0,0,0,0],
                [1,1,1,1,1,1,0],
                [0,0,0,0,0,1,1],
                [1,0,0,0,0,1,0],
                [0,1,1,1,1,0,0]
            ],
            '6': [
                [0,1,1,1,1,1,0],
                [1,1,0,0,0,0,0],
                [1,0,0,0,0,0,0],
                [1,1,1,1,1,1,0],
                [1,1,0,0,0,1,1],
                [1,0,0,0,0,0,1],
                [0,1,1,1,1,1,0]
            ],
            '7': [
                [1,1,1,1,1,1,1],
                [0,0,0,0,0,1,0],
                [0,0,0,0,1,0,0],
                [0,0,0,1,0,0,0],
                [0,0,1,0,0,0,0],
                [0,1,0,0,0,0,0],
                [1,0,0,0,0,0,0]
            ],
            '8': [
                [0,1,1,1,1,1,0],
                [1,1,0,0,0,1,1],
                [1,0,0,0,0,0,1],
                [0,1,1,1,1,1,0],
                [1,0,0,0,0,0,1],
                [1,1,0,0,0,1,1],
                [0,1,1,1,1,1,0]
            ],
            '9': [
                [0,1,1,1,1,1,0],
                [1,1,0,0,0,1,1],
                [1,0,0,0,0,0,1],
                [0,1,1,1,1,1,1],
                [0,0,0,0,0,1,0],
                [0,0,0,0,1,0,0],
                [0,1,1,1,0,0,0]
            ]
        }
        
        return patterns.get(digit, patterns.get('0'))
