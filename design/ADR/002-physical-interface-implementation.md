# ADR 002: Physical Interface Implementation with Rotary Encoder and OLED Display

## Status

Accepted

## Context

The Gwent Companion project requires a physical interface that allows players to interact with the device directly. This interface needs to provide:

1. Visual feedback through a display
2. Input controls for navigation and selection
3. A consistent and intuitive user experience

The physical interface must be robust, responsive, and integrate well with the existing software components, particularly the menu system and game state management. It needs to operate reliably in a gaming environment and provide clear visual feedback to users.

Previously, the project lacked:
- A reliable rotary encoder implementation with proper debouncing
- An optimized display interface for rendering menus and game information
- Integration between physical controls and the menu system
- Thread-safe operation for concurrent access to hardware resources

## Decision

We have implemented a comprehensive physical interface with the following components:

### 1. Rotary Encoder Implementation

- **RotaryEncoder Class**: A robust implementation using direct GPIO access with RPi.GPIO
  - Implements proper debouncing for reliable input detection
  - Uses an event queue for guaranteed event delivery
  - Provides both callback and queue-based interfaces
  - Handles rotation and button press events
  - Includes fallback to dummy implementation when hardware is unavailable

- **Key Features**:
  - Gray code pattern detection for accurate rotation tracking
  - Configurable debounce times for both rotation and button events
  - Thread-safe operation with background monitoring
  - Comprehensive error handling and logging

### 2. OLED Display Interface

- **OLEDDisplay Class**: An interface to the SSD1306 OLED display using luma.oled
  - Provides methods for displaying text, menus, and images
  - Implements content caching to prevent unnecessary refreshes
  - Includes thread-safe operation with locking mechanisms
  - Supports multiple font sizes and styles

- **Key Features**:
  - Efficient rendering with content caching
  - Support for displaying multiple text items in a single update
  - Menu rendering with highlighting for selected items
  - Datetime display capabilities
  - Automatic font discovery and fallback mechanisms

### 3. Integration with Menu System

- **Direct Integration**: The physical interface components are directly integrated with the menu system
  - Rotary encoder events drive menu navigation and selection
  - Display interface renders the menu structure
  - Thread-safe operation ensures consistent user experience

- **Implementation Details**:
  - Event-driven architecture for responsive user interaction
  - Background threads for continuous monitoring and updates
  - Optimized rendering for smooth visual feedback

## Consequences

### Positive

1. **Improved User Experience**: The physical interface provides an intuitive and responsive way for users to interact with the Gwent Companion device.

2. **Reliable Input Detection**: The debouncing mechanisms in the rotary encoder implementation ensure reliable input detection, preventing false triggers and missed events.

3. **Efficient Display Updates**: Content caching and optimized rendering reduce unnecessary display updates, improving performance and reducing power consumption.

4. **Thread-Safe Operation**: The use of locks and thread-safe design patterns ensures consistent behavior even with concurrent access to hardware resources.

5. **Graceful Degradation**: Fallback mechanisms allow the system to operate even when hardware components are unavailable, facilitating development and testing.

6. **Comprehensive Logging**: Detailed logging throughout the implementation aids in debugging and monitoring system behavior.

7. **Seamless Integration**: The physical interface components integrate seamlessly with the menu system and game logic, providing a cohesive user experience.

### Negative

1. **Hardware Dependencies**: The implementation relies on specific hardware components (SSD1306 OLED display, PEC11 rotary encoder), limiting flexibility in hardware selection.

2. **Increased Complexity**: The use of threading and event queues adds complexity to the codebase, requiring careful management to avoid race conditions and deadlocks.

3. **Resource Usage**: Background threads for monitoring and updating consume system resources, which could be a concern on resource-constrained devices.

4. **GPIO Pin Requirements**: The implementation requires specific GPIO pins, which may conflict with other hardware components in the system.

5. **Learning Curve**: Developers will need to understand the threading model and event-driven architecture to effectively work with the physical interface components.

## References

1. [Rotary Encoder Implementation](../../software/gwent/gwent/hal/rotary.py) - Implementation of the rotary encoder interface
2. [Display Interface Implementation](../../software/gwent/gwent/hal/display.py) - Implementation of the OLED display interface
3. [Menu System Integration](../../software/gwent/gwent/logical/menu.py) - Integration with the menu system
4. [Physical Interface Task](../tasks/005-physical-interface.md) - Detailed task specification for the physical interface