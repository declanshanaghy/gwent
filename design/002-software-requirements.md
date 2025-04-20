# Software Requirements Specification

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for the Gwent Companion system, a physical-digital hybrid gaming system that enhances the traditional Gwent card game experience by combining physical RFID-enabled cards with a digital companion device.

### 1.2 Scope
This specification covers all software components required to operate the Gwent Companion system, including the hardware abstraction layer, game logic, user interfaces, and communication protocols.

### 1.3 System Overview
The Gwent Companion system consists of a Raspberry Pi 3 Model B (2GB RAM minimum) based device that reads RFID-enabled Gwent cards, tracks game state, calculates scores, and provides player guidance through physical displays and a web interface.

## 2. System Architecture

### 2.1 Overview
- Microservices architecture
- Event-driven design
- RESTful API
- Real-time updates
- Persistent storage

### 2.2 Components
- Game Server (gwent)
- Front-end Application (glory-gate)
- Hardware Abstraction Layer (HAL)
- Database
- Message Queue
- Authentication Service

### 2.3 Interfaces
- Hardware interfaces (GPIO, SPI, I2C)
- Web interface (HTTP/WebSocket)
- User interface (physical controls, displays)
- API interfaces (REST, WebSocket)

## 3. Hardware Abstraction Layer (HAL)

### 3.1 RFID System Software Requirements

#### 3.1.1 RFID Reader Interface
- Model: RFID-RC522
- Library: mfrc522-python
- Implementation: Python module for interfacing with RFID-RC522 reader
- GPIO Connections:
  - SDA: Pin 24 / GPIO8 (CE0)
  - SCK: Pin 23 / GPIO11 (SCKL)
  - MOSI: Pin 19 / GPIO10 (MOSI)
  - MISO: Pin 21 / GPIO9 (MISO)
  - IRQ: Not connected
  - GND: Ground
  - RST: Pin 22 / GPIO25
  - 3.3V: 3.3V power
- Features:
  - Card detection
  - Data reading/writing
  - Error handling
  - Multiple sector support
  - Asynchronous operation

#### 3.1.2 Card Data Management
- Data format: JSON
- Storage: Card sectors
- Features:
  - Card identification
  - Card data validation
  - Data integrity checking
  - Error recovery

### 3.2 Display System Software Requirements

#### 3.2.1 OLED Display Interface
- Model: Monochrome 2.42" 128x64 OLED Graphic Display Module (SSD1306)
- Library: luma.oled
- Implementation: Python module for SSD1306 OLED display
- GPIO Connections (SPI Configuration):
  - Ground: Pin #1
  - 3.3V Power: Pin #2
  - DC (Data/Command): GPIO24 (Pin #4)
  - CLK (Data0): GPIO11 (Pin #7, SPI0 SCLK)
  - MOSI (Data1): GPIO10 (Pin #8, SPI0 MOSI)
  - CS: GPIO8 (Pin #15, SPI0 CE0)
  - RESET: GPIO25 (Pin #16)
- Features:
  - Text rendering
  - Menu display
  - Status indicators
  - Error messages
  - Graphics support

#### 3.2.2 LED Matrix Display Interface
- Model: LED Charlieplexed Matrix - 9x16 LEDs (IS31FL3731)
- Protocol: I2C (Address: 0x74)
- Library: adafruit-circuitpython-is31fl3731
- Implementation: Python module for IS31FL3731 LED driver
- Display Configuration:
  - Game Score Display: 1 (Red) - Multiplexer Channel 0
  - Player 1 Displays: 4 (Blue) - Multiplexer Channels 1-4
  - Player 2 Displays: 4 (Yellow) - Multiplexer Channels 5-7
- Features:
  - Score display
  - Animation support
  - Brightness control
  - Multiple display coordination via I2C multiplexer

#### 3.2.3 I2C Multiplexer Control
- Model: SparkFun Qwiic Mux Breakout - 8 Channel (TCA9548A)
- Protocol: I2C (Address: 0x70)
- Library: qwiic_tca9548a or adafruit-circuitpython-tca9548a
- Implementation: Python module for TCA9548A I2C multiplexer
- GPIO Connections:
  - SDA: GPIO2 (I2C1 SDA, Pin 3)
  - SCL: GPIO3 (I2C1 SCL, Pin 5)
  - VCC: 3.3V
  - GND: Ground
- Features:
  - Channel selection
  - Multiple device management
  - Error handling

### 3.3 Input System Software Requirements

#### 3.3.1 Rotary Encoder Interface
- Model: PEC11 Series Rotary Encoder
- Library: py-gaugette
- Implementation: Python module for rotary encoder
- GPIO Connections:
  - Common (C): Ground
  - A: GPIO7 (Pin 26) with pull-up resistor
  - B: GPIO9 (Pin 21) with pull-up resistor
  - SW: GPIO2 (Pin 3) for push button
- Features:
  - Rotation detection (24 pulses per rotation, 4 steps per detent)
  - Button press detection
  - Debouncing
  - Event-based callbacks
  - Asynchronous operation

#### 3.3.2 Input System Notes
- The system relies primarily on the rotary encoder for user input
- The encoder's push button serves as the primary selection mechanism
- Note: There are GPIO pin conflicts that must be managed:
  - GPIO9 is shared between RFID-RC522 MISO and Rotary Encoder B
  - GPIO2 is shared between Rotary Encoder SW and I2C SDA
  - GPIO3 is shared between Power Button and I2C SCL
  - SPI bus is shared between RFID reader and OLED display

### 3.4 Audio System Software Requirements

#### 3.4.1 Audio Playback
- Hardware: Raspberry Pi's built-in audio output
- Library: pygame.mixer
- Implementation: Python module for audio playback
- Features:
  - Sound effect playback
  - Background music
  - Volume control
  - Multiple channel support

#### 3.4.2 Text-to-Speech
- Hardware: Raspberry Pi's built-in audio output
- Library: gTTS (Google Text-to-Speech)
- Implementation: Python module for text-to-speech conversion
- Features:
  - Announcement generation
  - Language support
  - Caching for performance

### 3.5 Power Management Software Requirements

#### 3.5.1 Power State Control
- Implementation: System calls and GPIO control
- Features:
  - Sleep mode management
  - Shutdown handling
  - Power state monitoring
  - Low power detection

## 4. Game Logic

### 4.1 Game State Management
- Implementation: State machine pattern
- Features:
  - Game initialization
  - Round management
  - Turn tracking
  - Card placement tracking
  - Score calculation
  - Game termination

### 4.2 Rule Enforcement
- Implementation: Rule engine pattern
- Features:
  - Card placement validation
  - Special ability resolution
  - Weather effect application
  - Turn sequence enforcement

### 4.3 Score Calculation
- Implementation: Observer pattern
- Features:
  - Real-time score updates
  - Special ability effects
  - Weather effects
  - Round winner determination
  - Game winner determination

### 4.4 Player Interaction
- Implementation: Command pattern
- Features:
  - Turn prompts
  - Action validation
  - Guidance suggestions
  - Error feedback

## 5. User Interface

### 5.1 Physical Interface

#### 5.1.1 Menu System
- Implementation: State-based menu navigation
- Features:
  - Hierarchical menu structure
  - Rotary encoder navigation
  - Selection confirmation
  - Back/cancel functionality

#### 5.1.2 Display Output
- Implementation: Template-based display rendering
- Features:
  - Score display
  - Status indicators
  - Menu rendering
  - Error messages
  - Game state visualization

#### 5.1.3 Input Handling
- Implementation: Event-driven input processing
- Features:
  - Rotary encoder events
  - Button press events
  - Long-press detection
  - Input debouncing

### 5.2 Web Interface (Glory Gate)

#### 5.2.1 Game State Visualization
- Implementation: React components
- Features:
  - Real-time game board display
  - Card visualization
  - Score tracking
  - Player information
  - Game history

#### 5.2.2 Deck Management
- Implementation: CRUD operations
- Features:
  - Deck creation
  - Card addition/removal
  - Deck statistics
  - Deck sharing
  - Import/export functionality

#### 5.2.3 Player Interaction
- Implementation: WebSocket communication
- Features:
  - Real-time updates
  - Action confirmation
  - Error feedback
  - Game control

## 6. Data Management

### 6.1 Card Data
- Storage: SQLite database and JSON files
- Features:
  - Card definitions
  - Ability descriptions
  - Card images
  - Card statistics

### 6.2 Game State
- Storage: In-memory with persistence
- Features:
  - Current board state
  - Player hands
  - Played cards
  - Score tracking
  - Round status

### 6.3 Player Data
- Storage: SQLite database
- Features:
  - Player profiles
  - Deck collections
  - Game history
  - Statistics

### 6.4 Statistics
- Storage: SQLite database
- Features:
  - Game outcomes
  - Card usage statistics
  - Win rates
  - Player rankings

## 7. Communication

### 7.1 Protocols
- HTTP/HTTPS for REST API
- WebSocket for real-time updates
- SPI for display communication
- I2C for LED matrix and multiplexer
- GPIO for buttons and rotary encoder

### 7.2 APIs
- RESTful API for game state management
- WebSocket API for real-time updates
- Hardware abstraction APIs for device control

### 7.3 Event System
- Implementation: Publisher-subscriber pattern
- Features:
  - Card played events
  - Score update events
  - Round state events
  - Game state events
  - Hardware events

## 8. Performance Requirements

### 8.1 Response Times
- Card detection: < 100ms
- Display updates: < 50ms
- Input processing: < 20ms
- Score calculation: < 10ms
- Web interface updates: < 200ms

### 8.2 Resource Usage
- CPU: < 50% average
- Memory: < 1GB
- Storage: < 10GB
- Network: < 1Mbps

## 9. Security Requirements

### 9.1 Authentication
- Local device: Physical access only
- Web interface: JWT-based authentication
- API access: API key authentication

### 9.2 Authorization
- Role-based access control
- Feature-based permissions
- Administrative functions protection

### 9.3 Data Protection
- Secure storage of player data
- Encrypted communication for web interface
- Input validation and sanitization

## 10. Testing Requirements

### 10.1 Unit Testing
- Hardware abstraction layer tests
- Game logic tests
- API endpoint tests
- UI component tests

### 10.2 Integration Testing
- Hardware-software integration tests
- Component interaction tests
- API integration tests

### 10.3 System Testing
- End-to-end game flow tests
- Performance tests
- Reliability tests
- Edge case handling

## 11. Deployment Requirements

### 11.1 Environment
- Hardware: Raspberry Pi 3 Model B (2GB RAM minimum)
- OS: Raspberry Pi OS (64-bit)
- Python: 3.9+
- Node.js: 16+
- Database: SQLite 3

### 11.2 Configuration
- Environment variables for sensitive settings
- Configuration files for system parameters
- Command-line options for runtime configuration

### 11.3 Updates
- Over-the-air software updates
- Database schema migrations
- Configuration updates
- Rollback capability

## 12. Dependencies

### 12.1 Python Libraries
- RPi.GPIO: GPIO control
- mfrc522-python: RFID reader interface
- luma.oled: OLED display control
- adafruit-circuitpython-is31fl3731: LED matrix control
- adafruit-circuitpython-tca9548a: I2C multiplexer control
- py-gaugette: Rotary encoder interface
- pygame: Audio playback
- gtts: Text-to-speech
- aiohttp: Async HTTP server
- websockets: WebSocket support
- sqlalchemy: Database ORM
- pydantic: Data validation

### 12.2 JavaScript Libraries
- React: UI framework
- Redux: State management
- Socket.io: WebSocket client
- Axios: HTTP client
- Chart.js: Data visualization
- Material-UI: UI components

## 13. GPIO Pin Assignment Reference Table

| Component | GPIO Pin | Pin Number | Function |
|-----------|---------|------------|----------|
| RFID-RC522 SDA | GPIO8 | Pin 24 | SPI CE0 |
| RFID-RC522 SCK | GPIO11 | Pin 23 | SPI SCLK |
| RFID-RC522 MOSI | GPIO10 | Pin 19 | SPI MOSI |
| RFID-RC522 MISO | GPIO9 | Pin 21 | SPI MISO |
| RFID-RC522 RST | GPIO25 | Pin 22 | Reset |
| Rotary Encoder A | GPIO7 | Pin 26 | Encoder A input |
| Rotary Encoder B | GPIO9 | Pin 21 | Encoder B input |
| Rotary Encoder SW | GPIO2 | Pin 3 | Encoder push button |
| I2C SDA | GPIO2 | Pin 3 | I2C data |
| I2C SCL | GPIO3 | Pin 5 | I2C clock |
| OLED DC | GPIO24 | Pin 18 | OLED data/command |
| OLED CLK | GPIO11 | Pin 23 | SPI clock |
| OLED MOSI | GPIO10 | Pin 19 | SPI MOSI |
| OLED CS | GPIO8 | Pin 24 | SPI chip select |
| OLED RESET | GPIO25 | Pin 22 | OLED reset |

### 13.1 GPIO Pin Conflict Management

The hardware design has several GPIO pin conflicts that must be managed in software:

1. **GPIO9 Conflict**: Shared between RFID-RC522 MISO and Rotary Encoder B
   - Solution: Careful timing of operations to avoid simultaneous access

2. **GPIO2 Conflict**: Shared between Rotary Encoder SW and I2C SDA
   - Solution: Software must manage I2C transactions to avoid interference with button presses

3. **GPIO3 Conflict**: Shared between Power Button and I2C SCL
   - Solution: Power management must be aware of I2C bus activity

4. **SPI Bus Sharing**: Between RFID reader and OLED display
   - Solution: Implement proper chip select management and bus arbitration