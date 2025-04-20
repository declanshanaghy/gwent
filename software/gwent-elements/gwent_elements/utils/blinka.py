#!/usr/bin/env python3

"""
CircuitPython/Blinka testing utilities
"""

import board
import digitalio
import busio


class BlinkaTest:
    """
    CircuitPython/Blinka testing utilities
    """
    
    @staticmethod
    def test_digital_io(pin=board.D4):
        """
        Test digital I/O
        
        Args:
            pin: Digital pin to test (default: board.D4)
            
        Returns:
            bool: True if successful
        """
        try:
            # Try to create a Digital input
            digital_pin = digitalio.DigitalInOut(pin)
            print("Digital IO ok!")
            digital_pin.deinit()
            return True
        except Exception as e:
            print(f"Digital IO failed: {e}")
            return False
            
    @staticmethod
    def test_i2c():
        """
        Test I2C
        
        Returns:
            bool: True if successful
        """
        try:
            # Try to create an I2C device
            i2c = busio.I2C(board.SCL, board.SDA)
            print("I2C ok!")
            i2c.deinit()
            return True
        except Exception as e:
            print(f"I2C failed: {e}")
            return False
            
    @staticmethod
    def test_spi():
        """
        Test SPI
        
        Returns:
            bool: True if successful
        """
        try:
            # Try to create an SPI device
            spi = busio.SPI(board.SCLK, board.MOSI, board.MISO)
            print("SPI ok!")
            spi.deinit()
            return True
        except Exception as e:
            print(f"SPI failed: {e}")
            return False
            
    @classmethod
    def test_all(cls):
        """
        Test all interfaces
        
        Returns:
            bool: True if all tests passed
        """
        print("Testing CircuitPython/Blinka interfaces...")
        
        digital_io_ok = cls.test_digital_io()
        i2c_ok = cls.test_i2c()
        spi_ok = cls.test_spi()
        
        all_ok = digital_io_ok and i2c_ok and spi_ok
        
        if all_ok:
            print("All tests passed!")
        else:
            print("Some tests failed.")
            
        return all_ok