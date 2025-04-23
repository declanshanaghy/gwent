#!/usr/bin/env python3

import abc
import asyncio
import time
from typing import Any, Callable, List, Optional, Tuple

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice
from gwent.hal.rotary_rawgpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch
from software.gwent.gwent.hal.rotary_chooser import RotaryEncoder, RotaryImplementation


class AbstractRotaryEncoder(abc.ABC):
    """
    Abstract base class for rotary encoders.
    This defines the common interface that all rotary encoder implementations must follow.
    """
    
    @abc.abstractmethod
    def __init__(self, a_pin: int, b_pin: int, callback: Optional[Callable[[int], None]] = None, log=None):
        """
        Initialize the rotary encoder.
        
        Args:
            a_pin: The pin number for the A signal
            b_pin: The pin number for the B signal
            callback: Optional callback function to be called when rotation is detected
            log: Optional logger instance
        """
        pass
    
    @abc.abstractmethod
    def start(self):
        """Start monitoring the rotary encoder"""
        pass
    
    @abc.abstractmethod
    def stop(self):
        """Stop monitoring the rotary encoder"""
        pass
    
    @abc.abstractmethod
    def get_counter(self) -> int:
        """Get the current counter value"""
        pass
    
    @abc.abstractmethod
    def get_direction(self) -> Optional[int]:
        """Get the last direction of rotation (1 for clockwise, -1 for counter-clockwise, None if no rotation)"""
        pass
    
    @abc.abstractmethod
    def reset(self):
        """Reset the counter to 0"""
        pass
    
    @abc.abstractmethod
    def get_cycles(self) -> int:
        """Get the number of cycles since last call and reset the delta"""
        pass


class AbstractSwitch(abc.ABC):
    """
    Abstract base class for switches.
    This defines the common interface that all switch implementations must follow.
    """
    
    @abc.abstractmethod
    def __init__(self, pin: int):
        """
        Initialize the switch.
        
        Args:
            pin: The pin number for the switch
        """
        pass
    
    @abc.abstractmethod
    def get_state(self) -> bool:
        """
        Get the current state of the switch.
        
        Returns:
            bool: True if pressed, False if released
        """
        pass


class RotaryChooser(gwent.hal.mfdi.Chooser):
    def __init__(self, loop: asyncio.AbstractEventLoop,
                 implementation=RotaryImplementation.DIRECT_GPIO,
                 log_verbose: bool = False):
        """
        Initialize the rotary chooser.
        
        Args:
            loop: The asyncio event loop
            implementation: Which rotary encoder implementation to use
            log_verbose: Whether to enable verbose logging
        """
        super().__init__(loop, log_verbose=log_verbose)
        self.rotary = RotaryEncoder(implementation=implementation, log_verbose=log_verbose)

    async def choose(self, choices: List[gwent.messaging.choice.Message],
                     selected_idx: int,
                     select: Callable[
                         [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        await self._loop.run_in_executor(None, self.rotary.start)

        choice = choices[selected_idx]
        while True:
            delta, count, sw_changed, sw_state = await self._loop.run_in_executor(
                None, self.rotary.loop)
            if delta != 0:
                idx = count % len(choices)
                choice = choices[idx]
                self._log.debug({
                    'action': 'select',
                    'delta': delta,
                    'count': count,
                    'len(choices)': len(choices),
                    'idx': idx,
                    'choice.id': choice.id,
                    'choice.text': choice.text,
                })
                await select(delta, choice)

            if sw_changed and not sw_state:  # Release click
                return choice

            await asyncio.sleep(gwent.game.DEFAULT_YIELD_TIME)


# Simple test code when run directly
if __name__ == "__main__":
    # BCM pin numbers (not Wiring pin numbers)
    A_PIN = 23  # GPIO23
    B_PIN = 24  # GPIO24
    SW_PIN = 25  # GPIO25

    encoder = DirectGPIORotaryEncoder(A_PIN, B_PIN)
    encoder.start()

    sw = DirectGPIOSwitch(SW_PIN)
    last_state = sw.get_state()

    counter = 0

    try:
        print("Rotary encoder test running. Press Ctrl+C to exit.")
        while True:
            delta = encoder.get_cycles()
            if delta != 0:
                counter += delta
                print("count is %d" % counter)
            else:
                time.sleep(0.1)

            state = sw.get_state()
            if state != last_state:
                print("switch %d" % state)
                last_state = state
    except KeyboardInterrupt:
        print("\nExiting rotary encoder test...")
