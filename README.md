# ☕ Gwent Companion: The Artisanal Card Game Experience 🧙‍♂️

<div align="center">
  <img src="design/logo/gwent_logo.svg" alt="Gwent Companion Logo" width="800">
</div>

A hand-crafted digital companion for the physical card game Gwent from The Witcher III. This project combines locally-sourced physical cards with small-batch digital tracking to enhance the gameplay experience while maintaining the authentic, tactile feel of the original game.

```mermaid
graph TD
    classDef hardware fill:#d9ead3,stroke:#333,stroke-width:1px
    classDef cards fill:#fff2cc,stroke:#333,stroke-width:1px
    classDef digital fill:#cfe2f3,stroke:#333,stroke-width:1px
    
    subgraph companion["🖥️ Digital Companion"]
        rpi["🥧 Raspberry Pi"]:::digital
        rfid["📡 RFID Reader"]:::hardware
        display["📱 OLED Display"]:::hardware
        rotary["🎛️ Rotary Encoder"]:::hardware
        matrix["🔢 LED Matrix"]:::hardware
        
        rpi --- rfid
        rpi --- display
        rpi --- rotary
        rpi --- matrix
    end
    
    subgraph physical["🃏 Physical Components"]
        cards["💳 RFID Cards"]:::cards
        mat["🧵 Game Mat"]:::cards
    end
    
    cards -.- rfid
```

## 🔍 Overview

The Gwent Companion is a digital device that works alongside physical Gwent cards to:
- 🎮 Track game and round scores automatically
- 🃏 Manage player decks
- 💻 Provide a digital interface for game management
- 👐 Maintain the authentic feel of physical card play
- 🧭 Guide players through the entire game process

```mermaid
flowchart TD
    classDef start fill:#d5e8d4,stroke:#82b366,stroke-width:2px
    classDef process fill:#dae8fc,stroke:#6c8ebf,stroke-width:1px
    classDef decision fill:#fff2cc,stroke:#d6b656,stroke-width:1px
    classDef endNode fill:#f8cecc,stroke:#b85450,stroke-width:1px
    
    A[Start Game]:::start --> B[Register Leaders]:::process
    B --> C[Register Decks]:::process
    C --> D[Deal Cards]:::process
    D --> E{Choose First Player}:::decision
    E --> F[Play Round]:::process
    F --> G{Round Winner?}:::decision
    G --> H[Update Score]:::process
    H --> I{Game Over?}:::decision
    I -->|No| F
    I -->|Yes| J[Declare Winner]:::endNode
```

## 🔌 Hardware Components

- **💳 RFID-Enabled Cards**: Each physical Gwent card contains an RFID chip for identification
- **🧵 Cloth Game Mat**: Traditional playing surface
- **🖥️ Digital Companion**:
  - 🥧 Raspberry Pi for hardware interfacing and game management
  - 📡 Integrated RFID card reader
  - 🔢 Round score display
  - 🏆 Game score display
  - 📱 LCD menu system with interactive navigation
  - 🎛️ Rotary dial for menu navigation and selection
  - ⚡ Power management system

```mermaid
graph TD
    classDef rpi fill:#f5f5f5,stroke:#333,stroke-width:2px
    classDef spi fill:#fff2cc,stroke:#333,stroke-width:1px
    classDef i2c fill:#d9ead3,stroke:#333,stroke-width:1px
    classDef gpio fill:#cfe2f3,stroke:#333,stroke-width:1px
    
    rpi["🥧 Raspberry Pi"]:::rpi
    
    subgraph spi_devices["SPI Devices"]
        rfid["📡 RFID-RC522"]:::spi
        oled["📱 SSD1306 OLED"]:::spi
    end
    
    subgraph i2c_devices["I2C Devices"]
        mux["🔌 TCA9548A Multiplexer"]:::i2c
        matrix1["🔢 LED Matrix 1"]:::i2c
        matrix2["🔢 LED Matrix 2"]:::i2c
    end
    
    subgraph gpio_devices["GPIO Devices"]
        rotary["🎛️ Rotary Encoder"]:::gpio
        button["🔘 Push Button"]:::gpio
    end
    
    rpi --> spi_devices
    rpi --> i2c_devices
    rpi --> gpio_devices
    
    mux --> matrix1
    mux --> matrix2
```

## 💾 Software Components

- **🖥️ Game Server**: Runs on the Raspberry Pi
  - `gwent`: System service application for game state management
    - 🎮 Primary service: Game state management and hardware interfacing
    - 🌐 Secondary service: REST API for external interfaces
- **⚔️ Glory Gate**: React-based Single Page Application
  - Application name: `glory-gate`
  - 🌍 Web-based interface for game management
  - 🔌 Connects to the game server via REST API
  - 🏙️ Named after one of the six gates in Novigrad, connecting Farcorners district to Glory Lane

```mermaid
graph TD
    classDef service fill:#d5e8d4,stroke:#82b366,stroke-width:2px
    classDef component fill:#dae8fc,stroke:#6c8ebf,stroke-width:1px
    classDef api fill:#fff2cc,stroke:#d6b656,stroke-width:1px
    classDef ui fill:#f8cecc,stroke:#b85450,stroke-width:1px
    
    subgraph rpi["🥧 Raspberry Pi"]
        gwent["🎮 Gwent Service"]:::service
        
        subgraph components["Core Components"]
            game["Game Logic"]:::component
            hal["Hardware Abstraction Layer"]:::component
            pubsub["Pub/Sub System"]:::component
            audio["Audio System"]:::component
        end
        
        api["🌐 REST API"]:::api
    end
    
    subgraph web["Web Interface"]
        glory["⚔️ Glory Gate React App"]:::ui
    end
    
    gwent --> components
    gwent --> api
    api --> glory
```

## ✨ Features

- **🧮 Automatic Score Tracking**: Eliminates manual score keeping
- **🃏 Deck Management**: Track and manage player decks
- **📜 Game History**: Record and review past games
- **📖 Rule Reference**: Quick access to game rules
- **📊 Statistics**: Track win/loss records and performance metrics
- **🧭 Game Guidance**: Step-by-step assistance through the game process
- **📋 Menu System**: Interactive menu system for device configuration and control
- **🌐 Web Interface**: Access game data and controls through Glory Gate

```mermaid
mindmap
    root((Gwent Companion))
        🧮 Score Tracking
            ::icon(fa fa-calculator)
            Automatic updates
            Round scores
            Game scores
        🃏 Deck Management
            ::icon(fa fa-id-card)
            Card registration
            Deck building
            Card validation
        📜 Game History
            ::icon(fa fa-history)
            Past games
            Statistics
            Performance metrics
        📱 User Interface
            ::icon(fa fa-tablet)
            OLED display
            Rotary navigation
            Web interface
        🔊 Audio System
            ::icon(fa fa-volume-up)
            Sound effects
            Voice prompts
            Background music
```

## ⚙️ How It Works

1. 🥧 The Raspberry Pi runs the `gwent` system service that manages the entire game state
2. 🃏 Players use their physical Gwent cards as normal
3. 📡 The companion reads cards via its integrated RFID reader when cards are placed on the mat
4. 🔄 The `gwent` service processes card data and updates the game state
5. 🎛️ The rotary interface allows for easy menu navigation and configuration
6. 📱 The menu system provides access to audio settings and other configuration options
7. 🧭 The `gwent` service guides players through each phase of the game
8. 💾 Game state is maintained throughout the match
9. 🌐 The `gwent` service exposes a REST API that the `glory-gate` React application uses for additional game management features

```mermaid
sequenceDiagram
    participant Player
    participant Cards as 🃏 RFID Cards
    participant Reader as 📡 RFID Reader
    participant Gwent as 🎮 Gwent Service
    participant Display as 📱 Display
    participant Web as 🌐 Web Interface
    
    Player->>Cards: Places card on mat
    Cards->>Reader: Card detected
    Reader->>Gwent: Send card data
    Gwent->>Gwent: Process game state
    Gwent->>Display: Update display
    Gwent->>Web: Update web interface
    Web-->>Player: Show updated game state
    Display-->>Player: Show updated score
```

## 🚧 Project Status

This project is currently in active development. The following components have been implemented:

- **🔌 Hardware Interface**: Physical interface controls including rotary encoder and OLED display
- **🔊 Audio System**: Multi-channel audio playback with background music and sound effects
- **📱 Menu System**: Interactive menu system with navigation and selection via rotary encoder
- **⚙️ Service Management**: Systemd service for automatic startup and management

```mermaid
%%{init: {'theme': 'default'}}%%
gantt
    title Development Progress
    dateFormat YYYY-MM-DD
    
    section Hardware
    RFID Integration       :done, rfid, 2023-01-01, 2023-03-01
    Display Implementation :done, disp, 2023-02-15, 2023-03-31
    Rotary Encoder         :done, rot, 2023-03-01, 2023-03-30
    LED Matrix Integration :active, led, 2023-04-01, 2023-05-15
    
    section Software
    Core Game Logic        :done, core, 2023-01-15, 2023-04-15
    Hardware Abstraction   :done, hal, 2023-02-01, 2023-04-01
    Menu System            :done, menu, 2023-03-15, 2023-04-30
    Web Interface          :active, web, 2023-04-15, 2023-06-15
    
    section Documentation
    Design Documents       :done, docs, 2023-01-01, 2023-01-30
    API Documentation      :active, api, 2023-04-01, 2023-04-30
    User Manual            :crit, manual, 2023-05-01, 2023-06-15
```

The design documentation starts with the [Product Requirements Document](design/000-product-requirements.md), which outlines the core requirements and features. See the [task-list.mdc](task-list.mdc) file for current progress and upcoming tasks.

For detailed information about architectural decisions, see the Architecture Decision Records (ADRs):
- [ADR-000](design/ADR/000-task-master-roo-code.md): Task Master Integration for AI-Driven Development
- [ADR-001](design/ADR/001-audio-and-menu-subsystems.md): Audio and Menu Subsystems Implementation
- [ADR-002](design/ADR/002-physical-interface-implementation.md): Physical Interface Implementation with Rotary Encoder and OLED Display

For a comprehensive view of all project documentation, see our [📚 Documentation Table of Contents](toc.md).

## 🤔 Why This Project?

Gwent is a complex card game where score tracking can be cumbersome. This companion device:
- 🃏 Maintains the physical card play experience
- 🧮 Automates tedious score keeping
- 💻 Adds digital features without compromising the game's essence
- 🔰 Makes the game more accessible to new players
- 🧭 Provides guidance through the game process
- 🌐 Offers both physical and web-based interfaces

```mermaid
graph LR
    classDef benefit fill:#d5e8d4,stroke:#82b366,stroke-width:2px,color:#333
    classDef problem fill:#f8cecc,stroke:#b85450,stroke-width:2px,color:#333
    
    subgraph problems["❌ Traditional Problems"]
        p1["Manual Score Tracking"]:::problem
        p2["Complex Rules"]:::problem
        p3["Card Organization"]:::problem
        p4["Game History"]:::problem
    end
    
    subgraph benefits["✅ Gwent Companion Benefits"]
        b1["Automatic Scoring"]:::benefit
        b2["Rule Guidance"]:::benefit
        b3["Deck Management"]:::benefit
        b4["Game Statistics"]:::benefit
    end
    
    p1 --> b1
    p2 --> b2
    p3 --> b3
    p4 --> b4
```

## 🚀 Getting Started

The project is organized into several key areas:
- 🔌 Hardware design and implementation
- 💻 Software development
  - `gwent` system service
    - 🎮 Game state management
    - 🔌 Hardware interfacing
    - 🌐 REST API implementation
  - `glory-gate` React front-end development

See the [design documentation](design/README.md) for detailed information about each component.

```mermaid
graph TD
    classDef root fill:#f5f5f5,stroke:#333,stroke-width:2px
    classDef dir fill:#dae8fc,stroke:#6c8ebf,stroke-width:1px
    classDef code fill:#d5e8d4,stroke:#82b366,stroke-width:1px
    classDef docs fill:#fff2cc,stroke:#d6b656,stroke-width:1px
    
    root["📁 gwent/"]:::root
    
    software["📁 software/"]:::dir
    design["📁 design/"]:::docs
    scripts["📁 scripts/"]:::dir
    
    gwent["📁 gwent/"]:::code
    glory["📁 glory-gate/"]:::code
    
    docs["📄 Documentation"]:::docs
    diagrams["📊 Diagrams"]:::docs
    
    game["📁 game/"]:::code
    hal["📁 hal/"]:::code
    utils["📁 utils/"]:::code
    
    root --> software
    root --> design
    root --> scripts
    
    software --> gwent
    software --> glory
    
    design --> docs
    design --> diagrams
    
    gwent --> game
    gwent --> hal
    gwent --> utils
```

## 📚 Documentation

- [Complete Documentation Table of Contents](toc.md): Comprehensive guide to all project documentation
- [Design Documentation](design/README.md): Artisanal design documentation including architecture decisions, tasks, and specifications
- [Menu System](software/gwent/docs/menu_system.md): Documentation for the interactive menu system
- [Technical Design Documents](design/):
  - 📊 Architecture Diagrams:
    - [GwentPubSub.md](design/GwentPubSub.md): Interactive diagram of the publish-subscribe architecture
    - [GwentPubSub.pdf](design/GwentPubSub.pdf): PDF version of the publish-subscribe architecture
    - [GwentGameStages.pdf](design/GwentGameStages.pdf): Game stages and state transitions
  - 🎭 Style Guidelines:
    - [Design Documentation Style Guide](design/DesignDocumentationStyleGuide.md): Guidelines for creating consistent design documentation
- [Software Components](software/):
  - [Gwent Core](software/gwent/README.md): Main game logic and system service
  - [Glory Gate](software/glory-gate/README.md): React-based web interface
- [Development Tools](scripts/README.md): Scripts and utilities for development
