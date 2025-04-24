import abc
from typing import Optional, Callable


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