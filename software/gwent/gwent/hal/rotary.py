import time
import threading
from typing import Any, Callable, List, Optional, Tuple

import gwent.hal.mfdi
import gwent.game
import gwent.messaging.choice
from gwent.hal.rotary_rpigpio import DirectGPIORotaryEncoder, DirectGPIOSwitch
from gwent.hal.rotary_gpiozero import GwentGPIOZeroRotaryEncoder, GPIOZeroSwitch
from gwent.hal.rotary_pigpio import PiGPIORotaryEncoder, PiGPIOSwitch
from enum import Enum, auto

class RotaryImplementation(Enum):
    """Enum to specify which rotary encoder implementation to use"""
    DIRECT_GPIO = auto()
    GPIOZERO = auto()
    PIGPIO = auto()  # New implementation using pigpio


class RotaryChooser(gwent.hal.mfdi.Chooser):
    def __init__(self, implementation=RotaryImplementation.PIGPIO,
                log_verbose: bool = False):
        """
        Initialize the rotary chooser.
        
        Args:
            implementation: Which rotary encoder implementation to use
            log_verbose: Whether to enable verbose logging
        """
        super().__init__()
        self._log_verbose = log_verbose
        self._log.info(f"Initializing RotaryChooser with implementation: {implementation.name}")
        try:
            self._log.info("Creating RotaryEncoder instance")
            self.rotary = RotaryEncoder(implementation=implementation, log_verbose=log_verbose)
            self._log.info("RotaryEncoder created successfully")
        except Exception as e:
            self._log.error(f"Failed to create RotaryEncoder: {e}", exc_info=True)
            raise
            
        self._stop_event = threading.Event()
        self._choice = None
        self._choices = None
        self._select_callback = None
        self._log.info("RotaryChooser initialized successfully")

    def cancel(self):
        """Cancel the current choose() call so the thread can exit."""
        self._log.info("RotaryChooser cancel requested")
        self._stop_event.set()

    def choose(self, choices: List[gwent.messaging.choice.Message],
                    selected_idx: int,
                    select: Callable[
                        [int, gwent.messaging.choice.Message], Any]) -> \
            gwent.messaging.choice.Message:
        self._log.info(f"choose() called with {len(choices)} choices, selected_idx={selected_idx}")
        
        if not choices:
            self._log.error("No choices provided")
            return None
            
        if selected_idx < 0 or selected_idx >= len(choices):
            self._log.warning(f"Invalid selected_idx {selected_idx}, using 0 instead")
            selected_idx = 0
        
        try:
            self._log.info("Starting rotary encoder")
            self.rotary.start()
            self._log.info("Rotary encoder started successfully")
        except Exception as e:
            self._log.error(f"Failed to start rotary encoder: {e}", exc_info=True)
            raise
        
        self._log.info("Clearing stop event")
        self._stop_event.clear()
        self._choices = choices
        self._select_callback = select
        
        # Start with the selected choice
        choice = choices[selected_idx]
        self._log.info(f"Initial choice: id={choice.id}, text={choice.text}")
        self._choice = choice
        
        # Create a thread to monitor the rotary encoder
        self._log.info("Creating monitor thread")
        monitor_thread = threading.Thread(
            target=self._monitor_rotary,
            args=(choices, selected_idx, select),
            name="RotaryMonitor"
        )
        monitor_thread.daemon = True
        self._log.info("Starting monitor thread")
        monitor_thread.start()
        
        # Wait for a selection to be made
        self._log.info("Waiting for selection to be made")
        wait_count = 0
        while not self._stop_event.is_set():
            time.sleep(gwent.game.DEFAULT_YIELD_TIME)
            wait_count += 1
            if wait_count % (gwent.game.DEFAULT_YIELD_TIME * 50000) == 0:
                self._log.debug(f"Still waiting for selection... ({wait_count} cycles)")
            
        self._log.info("Stop event set, joining monitor thread")
        monitor_thread.join(timeout=1.0)
        if monitor_thread.is_alive():
            self._log.warning("Monitor thread did not terminate within timeout")
        else:
            self._log.info("Monitor thread terminated successfully")
            
        self._log.info(f"Returning choice: id={self._choice.id}, text={self._choice.text}")
        return self._choice

    def _monitor_rotary(self, choices, selected_idx, select):
        thread_id = threading.get_ident()
        self._log.info(f"Monitor thread started (id={thread_id})")

        choice = choices[selected_idx]
        self._choice = choice
        self._log.info(f"Initial choice in monitor: id={choice.id}, text={choice.text}")

        # Wait for the button to be fully released before accepting input.
        # This prevents catching the tail end of the previous button press
        # that triggered a stage transition.
        self._log.debug("Waiting for button to be released before accepting input")
        while not self._stop_event.is_set():
            _, _, _, sw_state = self.rotary.loop()
            if sw_state:  # True = released
                break
            time.sleep(gwent.game.DEFAULT_YIELD_TIME)
        self._log.debug("Button released, accepting input")

        loop_count = 0
        last_delta_time = time.time()
        last_switch_time = time.time()

        while not self._stop_event.is_set():
            loop_count += 1

            try:
                delta, count, sw_changed, sw_state = self.rotary.loop()

                if delta != 0:
                    current_time = time.time()
                    time_since_last = current_time - last_delta_time
                    last_delta_time = current_time

                    idx = count % len(choices)
                    choice = choices[idx]
                    self._choice = choice
                    self._log.info({
                        'action': 'select',
                        'delta': delta,
                        'count': count,
                        'time_since_last_delta': f"{time_since_last:.3f}s",
                        'len(choices)': len(choices),
                        'idx': idx,
                        'choice.id': choice.id,
                        'choice.text': choice.text,
                    })

                    try:
                        self._log.debug("Calling select callback")
                        select(delta, choice)
                        self._log.debug("Select callback completed")
                    except Exception as e:
                        self._log.error(f"Error in select callback: {e}", exc_info=True)

                if sw_changed:
                    current_time = time.time()
                    time_since_last = current_time - last_switch_time
                    last_switch_time = current_time

                    self._log.info({
                        'action': 'switch_change',
                        'sw_state': sw_state,
                        'time_since_last_switch': f"{time_since_last:.3f}s"
                    })

                    if not sw_state:  # Release click
                        self._log.info("Switch released, setting stop event")
                        self._stop_event.set()
                        return
                
                # Log status periodically (every ~5 seconds)
                if loop_count % (gwent.game.DEFAULT_YIELD_TIME * 50000) == 0:
                    self._log.debug({
                        'action': 'monitor_status',
                        'loop_count': loop_count,
                        'current_choice': self._choice.id if self._choice else None,
                        'stop_event': self._stop_event.is_set()
                    })
                    
                time.sleep(gwent.game.DEFAULT_YIELD_TIME)
                
            except Exception as e:
                self._log.error(f"Error in monitor loop: {e}", exc_info=True)
                time.sleep(gwent.game.DEFAULT_YIELD_TIME)  # Sleep to avoid tight error loop
        
        self._log.info(f"Monitor thread exiting (id={thread_id})")


class RotaryEncoder(gwent.game.BaseComponent):
    """
    Rotary encoder implementation.
    This class wraps the rotary encoder implementations to provide a higher-level interface
    for use in the game system.
    """
    # BCM pin numbers (not Wiring pin numbers)
    A_PIN = 17  # GPIO17
    B_PIN = 22  # GPIO22
    SW_PIN = 27  # GPIO27
    
    # Debounce time in seconds
    DEBOUNCE_TIME = 0.05  # 50ms debounce

    _encoder = None
    _sw = None
    _counter = 0
    _delta = 0
    _sw_state = None
    _sw_changed = False
    _last_sw_change_time = 0
    _last_sw_raw_state = None
    
    def __init__(self, implementation=RotaryImplementation.PIGPIO, log_verbose=False):
        """
        Initialize the rotary encoder.
        
        Args:
            implementation: Which implementation to use (DirectGPIO, GPIOZero, or PIGPIO)
            log_verbose: Whether to enable verbose logging
        """
        super().__init__()
        self._log_verbose = log_verbose
        self._log.info(f"Initializing RotaryEncoder with implementation: {implementation.name}")
        self._implementation = implementation
        self._log.info(f"Using pins: A={self.A_PIN}, B={self.B_PIN}, SW={self.SW_PIN}")
        self._log.info("RotaryEncoder instance created (hardware not initialized yet)")

    def start(self):
        self._log.info("start() called")
        if self._encoder is None:
            self._log.info(f"Initializing rotary encoder hardware")
            
            try:
                if self._implementation == RotaryImplementation.DIRECT_GPIO:
                    self._log.info("Creating DirectGPIORotaryEncoder")
                    self._encoder = DirectGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
                    self._log.info("Creating DirectGPIOSwitch")
                    self._sw = DirectGPIOSwitch(self.SW_PIN)
                    self._log.info("Direct GPIO rotary encoder initialized successfully")
                    
                elif self._implementation == RotaryImplementation.GPIOZERO:
                    self._log.info("Creating GwentGPIOZeroRotaryEncoder")
                    self._encoder = GwentGPIOZeroRotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
                    self._log.info("Creating GPIOZeroSwitch")
                    self._sw = GPIOZeroSwitch(self.SW_PIN)
                    self._log.info("GPIOZero rotary encoder initialized successfully")
                    
                elif self._implementation == RotaryImplementation.PIGPIO:
                    self._log.info("Creating PiGPIORotaryEncoder")
                    self._encoder = PiGPIORotaryEncoder(self.A_PIN, self.B_PIN, log=self._log)
                    self._log.info("Creating PiGPIOSwitch")
                    self._sw = PiGPIOSwitch(self.SW_PIN)
                    self._log.info("PiGPIO rotary encoder initialized successfully")
                    
                else:
                    self._log.error(f"Unknown implementation: {self._implementation}")
                    raise ValueError(f"Unknown implementation: {self._implementation}")
                    
                self._log.info("Starting encoder monitoring")
                self._encoder.start()
                self._log.info("Encoder monitoring started successfully")
                
            except Exception as e:
                self._log.error(f"Failed to initialize rotary encoder: {e}", exc_info=True)
                raise

        self._log.info("Resetting encoder state")
        self.reset()
        self._log.info("Encoder started and reset successfully")

    def reset(self):
        self._log.info("reset() called")
        self._counter = 0
        self._delta = 0
        self._last_sw_change_time = time.time()
        self._last_sw_raw_state = None
        
        if self._encoder:
            self._log.debug("Resetting encoder counter")
            try:
                self._encoder.reset()
                self._log.debug("Encoder counter reset successfully")
            except Exception as e:
                self._log.error(f"Error resetting encoder: {e}", exc_info=True)
                
        if self._sw:
            self._log.debug("Reading initial switch state")
            try:
                self._sw_state = self._sw.get_state()
                self._last_sw_raw_state = self._sw_state
                self._log.debug(f"Initial switch state: {self._sw_state}")
            except Exception as e:
                self._log.error(f"Error reading switch state: {e}", exc_info=True)
                self._sw_state = False  # Default to not pressed
                self._last_sw_raw_state = False

    def loop(self) -> (int, int, bool, bool):
        loop_start = time.time()
        should_log = self.should_log()

        # Get encoder delta
        try:
            self._delta = self._encoder.get_cycles() if self._encoder else 0
        except Exception as e:
            self._log.error(f"Error getting encoder cycles: {e}", exc_info=True)
            self._delta = 0
            
        if self._delta != 0:
            self._counter += self._delta
            self._log.debug(f'Encoder count is {self._counter} (delta: {self._delta})')

        # Get switch state with debouncing
        try:
            raw_state = self._sw.get_state() if self._sw else False
        except Exception as e:
            self._log.error(f"Error getting switch state: {e}", exc_info=True)
            raw_state = self._last_sw_raw_state or self._sw_state  # Keep previous state
        
        # Store the raw state for comparison in the next iteration
        self._last_sw_raw_state = raw_state
        
        # Apply debouncing - only accept state changes after DEBOUNCE_TIME has elapsed
        current_time = time.time()
        self._sw_changed = False
        
        if raw_state != self._sw_state:
            # If this is a new state change or if enough time has passed since the last change
            if current_time - self._last_sw_change_time >= self.DEBOUNCE_TIME:
                self._sw_changed = True
                self._log.info(f'Switch changed to {raw_state} (was {self._sw_state}) after {current_time - self._last_sw_change_time:.3f}s debounce')
                self._sw_state = raw_state
                self._last_sw_change_time = current_time
            else:
                self._log.debug(f'Ignoring switch change to {raw_state} - within debounce period ({current_time - self._last_sw_change_time:.3f}s < {self.DEBOUNCE_TIME}s)')

        # Log changes
        if self._delta != 0 or self._sw_changed:
            self._log.info({
                'action': 'loop',
                'delta': self._delta,
                'counter': self._counter,
                'sw_changed': self._sw_changed,
                'sw_state': self._sw_state,
            })

        if should_log:
            self.log_time('loop', loop_start)
            
        return self._delta, self._counter, self._sw_changed, self._sw_state


# No mocks in production code as per development guidelines
