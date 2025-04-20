#!/usr/bin/env python3

"""
Matrix display utilities
"""

import time
import board
import busio
import adafruit_is31fl3731
import adafruit_framebuf
import qwiic_tca9548a


class MatrixDisplay:
    """
    Matrix display using IS31FL3731
    """
    
    def __init__(self, i2c=None, address=0x74, mux=None, mux_channel=None):
        """
        Initialize the matrix display
        
        Args:
            i2c (busio.I2C): I2C bus (default: None, will use board.SCL/SDA)
            address (int): I2C address (default: 0x74)
            mux (qwiic_tca9548a.QwiicTCA9548A): I2C multiplexer (default: None)
            mux_channel (int): I2C multiplexer channel (default: None)
        """
        # Initialize I2C bus if not provided
        if i2c is None:
            self.i2c = busio.I2C(board.SCL, board.SDA)
        else:
            self.i2c = i2c
            
        self.address = address
        self.mux = mux
        self.mux_channel = mux_channel
        
        # Initialize matrix
        if self.mux and self.mux_channel is not None:
            self.mux.disable_all()
            self.mux.enable_channels(self.mux_channel)
            
        self.matrix = adafruit_is31fl3731.Matrix(self.i2c, address=self.address)
        
    def clear(self):
        """
        Clear the display
        """
        for x in range(self.matrix.width):
            for y in range(self.matrix.height):
                self.matrix.pixel(x, y, 0)
                
    def draw_border(self, brightness=255):
        """
        Draw a border around the display
        
        Args:
            brightness (int): Border brightness (default: 255)
        """
        # Draw top and bottom edges
        for x in range(self.matrix.width):
            self.matrix.pixel(x, 0, brightness)
            self.matrix.pixel(x, self.matrix.height - 1, brightness)
            
        # Draw left and right edges
        for y in range(self.matrix.height):
            self.matrix.pixel(0, y, brightness)
            self.matrix.pixel(self.matrix.width - 1, y, brightness)
            
    def draw_text(self, text, brightness=50, scroll=True, scroll_delay=0.1):
        """
        Draw text on the display
        
        Args:
            text (str): Text to display
            brightness (int): Text brightness (default: 50)
            scroll (bool): Whether to scroll the text (default: True)
            scroll_delay (float): Scroll delay in seconds (default: 0.1)
        """
        # Create a framebuffer for the display
        buf = bytearray(32)  # 2 bytes tall x 16 wide = 32 bytes (9 bits is 2 bytes)
        fb = adafruit_framebuf.FrameBuffer(
            buf, self.matrix.width, self.matrix.height, adafruit_framebuf.MVLSB
        )
        
        if scroll:
            # Scroll the text across the display
            frame = 0  # start with frame 0
            for i in range(len(text) * 9):
                fb.fill(0)
                fb.text(text, -i + self.matrix.width, 0, color=1)
                
                # Fill the next frame with scrolling text
                self.matrix.frame(frame, show=False)
                self.clear()
                
                for x in range(self.matrix.width):
                    # Using the FrameBuffer text result
                    bite = buf[x]
                    for y in range(self.matrix.height):
                        bit = 1 << y & bite
                        # If bit > 0 then set the pixel brightness
                        if bit:
                            self.matrix.pixel(x, y, brightness)
                            
                # Show the frame
                self.matrix.frame(frame, show=True)
                frame = 0 if frame else 1
                
                # Delay
                time.sleep(scroll_delay)
        else:
            # Display the text without scrolling
            fb.fill(0)
            fb.text(text, 0, 0, color=1)
            
            # Fill the frame with text
            self.matrix.frame(0, show=False)
            self.clear()
            
            for x in range(self.matrix.width):
                # Using the FrameBuffer text result
                bite = buf[x]
                for y in range(self.matrix.height):
                    bit = 1 << y & bite
                    # If bit > 0 then set the pixel brightness
                    if bit:
                        self.matrix.pixel(x, y, brightness)
                        
            # Show the frame
            self.matrix.frame(0, show=True)
            
    def fade(self, fade_in=500, fade_out=500, pause=1000):
        """
        Fade the display in and out
        
        Args:
            fade_in (int): Fade in time in milliseconds (default: 500)
            fade_out (int): Fade out time in milliseconds (default: 500)
            pause (int): Pause time in milliseconds (default: 1000)
        """
        self.matrix.fade(fade_in=fade_in, fade_out=fade_out, pause=pause)


class MultiMatrixDisplay:
    """
    Multiple matrix displays using IS31FL3731 and I2C multiplexer
    """
    
    def __init__(self, mux_address=0x70, matrix_address=0x74, channels=None):
        """
        Initialize multiple matrix displays
        
        Args:
            mux_address (int): I2C multiplexer address (default: 0x70)
            matrix_address (int): Matrix display address (default: 0x74)
            channels (list): List of I2C multiplexer channels (default: None)
        """
        # Initialize I2C bus
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        # Initialize I2C multiplexer
        self.mux = qwiic_tca9548a.QwiicTCA9548A(address=mux_address)
        
        # Initialize matrix displays
        self.displays = []
        
        if channels is None:
            channels = [0, 7]  # Default channels
            
        for channel in channels:
            self.mux.enable_channels(channel)
            self.displays.append((channel, adafruit_is31fl3731.Matrix(self.i2c, address=matrix_address)))
            self.mux.disable_all()
            
    def get_display(self, index):
        """
        Get a display by index
        
        Args:
            index (int): Display index
            
        Returns:
            tuple: (channel, matrix)
        """
        return self.displays[index]
        
    def clear_all(self):
        """
        Clear all displays
        """
        for display in self.displays:
            channel, matrix = display
            self.mux.disable_all()
            self.mux.enable_channels(channel)
            
            for x in range(matrix.width):
                for y in range(matrix.height):
                    matrix.pixel(x, y, 0)
                    
            self.mux.disable_all()
            
    def draw_border_all(self, brightness=255):
        """
        Draw a border on all displays
        
        Args:
            brightness (int): Border brightness (default: 255)
        """
        for display in self.displays:
            channel, matrix = display
            self.mux.disable_all()
            self.mux.enable_channels(channel)
            
            # Draw top and bottom edges
            for x in range(matrix.width):
                matrix.pixel(x, 0, brightness)
                matrix.pixel(x, matrix.height - 1, brightness)
                
            # Draw left and right edges
            for y in range(matrix.height):
                matrix.pixel(0, y, brightness)
                matrix.pixel(matrix.width - 1, y, brightness)
                
            self.mux.disable_all()