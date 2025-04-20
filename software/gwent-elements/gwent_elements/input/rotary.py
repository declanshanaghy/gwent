#!/usr/bin/env python3

"""
Rotary encoder interface using gaugette
"""

import time
import asyncio
import functools
import gaugette.gpio
import gaugette.rotary_encoder
import gaugette.switch


class RotaryEncoder:
    """
    Rotary encoder interface using gaugette
    """
    
    def __init__(self, a_pin=1, b_pin=0, sw_pin=2):
        """
        Initialize the rotary encoder
        
        Args:
            a_pin (int): A pin number (default: 1)
            b_pin (int): B pin number (default: 0)
            sw_pin (int): Switch pin number (default: 2)
        """
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.sw_pin = sw_pin
        
        # Initialize GPIO
        self.gpio = gaugette.gpio.GPIO()
        
        # Initialize rotary encoder
        self.encoder = gaugette.rotary_encoder.RotaryEncoder(self.gpio, self.a_pin, self.b_pin)
        self.encoder.start()
        
        # Initialize switch
        self.switch = gaugette.switch.Switch(self.gpio, self.sw_pin)
        self.last_switch_state = self.switch.get_state()
        
        # Initialize counter
        self.counter = 0
        
        # Initialize callbacks
        self.rotation_callback = None
        self.switch_callback = None
        
    def get_counter(self):
        """
        Get the current counter value
        
        Returns:
            int: Counter value
        """
        return self.counter
        
    def set_counter(self, value):
        """
        Set the counter value
        
        Args:
            value (int): Counter value
        """
        self.counter = value
        
    def get_switch_state(self):
        """
        Get the current switch state
        
        Returns:
            int: Switch state (0 or 1)
        """
        return self.switch.get_state()
        
    def set_rotation_callback(self, callback):
        """
        Set the rotation callback function
        
        Args:
            callback (function): Callback function that takes delta as argument
        """
        self.rotation_callback = callback
        
    def set_switch_callback(self, callback):
        """
        Set the switch callback function
        
        Args:
            callback (function): Callback function that takes state as argument
        """
        self.switch_callback = callback
        
    def update(self):
        """
        Update the rotary encoder state
        
        Returns:
            tuple: (delta, switch_changed, switch_state)
        """
        # Get the rotary encoder delta
        delta = self.encoder.get_cycles()
        if delta != 0:
            self.counter += delta
            if self.rotation_callback:
                self.rotation_callback(delta)
                
        # Get the switch state
        switch_state = self.switch.get_state()
        switch_changed = switch_state != self.last_switch_state
        if switch_changed:
            self.last_switch_state = switch_state
            if self.switch_callback:
                self.switch_callback(switch_state)
                
        return (delta, switch_changed, switch_state)
        
    def run_loop(self, sleep_time=0.1):
        """
        Run the update loop
        
        Args:
            sleep_time (float): Sleep time between updates (default: 0.1)
        """
        try:
            while True:
                self.update()
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            pass


class AsyncRotaryEncoder(RotaryEncoder):
    """
    Asynchronous rotary encoder interface
    """
    
    async def async_update(self):
        """
        Update the rotary encoder state asynchronously
        
        Returns:
            tuple: (delta, switch_changed, switch_state)
        """
        # Get the rotary encoder delta
        delta = self.encoder.get_cycles()
        if delta != 0:
            self.counter += delta
            if self.rotation_callback:
                self.rotation_callback(delta)
                
        # Get the switch state
        switch_state = self.switch.get_state()
        switch_changed = switch_state != self.last_switch_state
        if switch_changed:
            self.last_switch_state = switch_state
            if self.switch_callback:
                self.switch_callback(switch_state)
                
        return (delta, switch_changed, switch_state)
        
    async def run_async_loop(self, sleep_time=0.1):
        """
        Run the update loop asynchronously
        
        Args:
            sleep_time (float): Sleep time between updates (default: 0.1)
        """
        try:
            while True:
                await self.async_update()
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass
            
    @classmethod
    async def create(cls, a_pin=1, b_pin=0, sw_pin=2):
        """
        Create an asynchronous rotary encoder
        
        Args:
            a_pin (int): A pin number (default: 1)
            b_pin (int): B pin number (default: 0)
            sw_pin (int): Switch pin number (default: 2)
            
        Returns:
            AsyncRotaryEncoder: Asynchronous rotary encoder
        """
        loop = asyncio.get_running_loop()
        
        # Create the encoder
        encoder = cls(a_pin, b_pin, sw_pin)
        
        # Start the encoder
        await loop.run_in_executor(None, encoder.encoder.start)
        
        return encoder