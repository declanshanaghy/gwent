# 📊 Gwent Publish-Subscribe Architecture: The l33tC0dzr Edition ☕

This artisanal diagram represents the publish-subscribe architecture used for communication between components in the Gwent Companion system, crafted with care by our ivory tower architects.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#fff',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px'
  }
}}%%

flowchart LR
    %% Hardware Components with Hipster Icons
    subgraph Hardware["🔧 Artisanal Hardware Components"]
        rfidReader["📡 RFID Reader\n(MFRC522)"]
        rfidWriter["✍️ RFID Writer\nFair-Trade Data Inscriber"]
        touchscreen["🖐️ 7\" Touchscreen\nReclaimed Glass Canvas"]
    end

    %% Software Components
    subgraph Software["💻 Craft Software"]
        tui["🖥️ gwent-tui\nTouchscreen Kiosk"]
        pubsub["☕ Pub/Sub System\nFair-Trade Message Broker"]
        gameControl["🎮 Game Control\nOrganic Game Logic"]
        sfx["🎵 SFX\n(pygame)"]
        menus["📋 Menus\nHand-Crafted UI"]
    end

    %% Message Topics
    subgraph Topics["📨 Message Topics"]
        mfdTopic["mfd"]
        choosepresentTopic["choosepresent"]
        cardsTopic["cards"]
        rawTopic["raw"]
        readwriteTopic["readwrite"]
        playTopic["play"]
        sfxctrlTopic["sfxctrl"]
    end

    %% Game States as Vinyl Records
    subgraph GameStates["💿 Vinyl Collection Game States"]
        registerLeaders["🎵 Register Leaders"]
        registerDecks["🎵 Register Decks"]
        dealCards["🎵 Deal Cards"]
        playRound["🎵 Play Round"]
        playLeader["🎵 Play Leader"]
        roundEnd["🎵 Round End"]
        gameEnd["🎵 Game End"]
    end

    %% Display Components as Typewriter Keys
    subgraph DisplayComponents["⌨️ Vintage Display Components"]
        boardHand["🃏 Board/Hand\nLetterpress-Printed"]
        grave["⚰️ Grave\nReclaimed Soil"]
        deck["🎴 Deck\nSustainably Harvested"]
        player["👤 Player\nFree-Range"]
        close["⚔️ Close\nArtisanal Combat"]
        range["🏹 Range\nHand-Forged"]
        siegeTot["🏰 Siege Total\nSmall-Batch"]
    end

    %% Connections with Artisanal Flow
    rfidReader ==> rawTopic
    rawTopic ==> pubsub
    
    gameControl ==> mfdTopic
    mfdTopic ==> tui
    
    tui ==> choosepresentTopic
    choosepresentTopic ==> pubsub
    
    pubsub ==> cardsTopic
    cardsTopic ==> gameControl
    
    gameControl ==> playTopic
    playTopic ==> pubsub
    
    pubsub ==> sfxctrlTopic
    sfxctrlTopic ==> sfx
    
    gameControl ==> menus
    menus ==> tui
    
    pubsub ==> readwriteTopic
    readwriteTopic ==> rfidWriter
    
    gameControl ==> GameStates
    
    tui ==> DisplayComponents
    tui --- touchscreen
    
    %% Hipster Styling
    classDef hardware fill:#A1887F,stroke:#5D4037,stroke-width:2px,color:#fff,font-family:'Courier New',font-weight:bold
    classDef software fill:#BCAAA4,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-weight:bold
    classDef topic fill:#D7CCC8,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-style:italic
    classDef gameState fill:#EFEBE9,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
    classDef display fill:#F5F5F5,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
    
    class rfidReader,rfidWriter,touchscreen hardware
    class tui,pubsub,gameControl,sfx,menus software
    class mfdTopic,choosepresentTopic,cardsTopic,rawTopic,readwriteTopic,playTopic,sfxctrlTopic topic
    class registerLeaders,registerDecks,dealCards,playRound,playLeader,roundEnd,gameEnd gameState
    class boardHand,grave,deck,player,close,range,siegeTot display
```

## 📜 Artisanal Component Descriptions

### 🔧 Handcrafted Hardware Components
- **📡 RFID Reader (MFRC522)**: Locally-sourced RFID tag reader for cards, with sustainable power consumption
- **✍️ RFID Writer**: Data reader/writer for RFID tags, crafted with care
- **🖐️ 7" Touchscreen**: Small-batch reclaimed-glass canvas that hosts the `gwent-tui` kiosk — all game info, menus, and the camera live view. (Supersedes the deprecated OLED + rotary encoder, since composted.)

### 💻 Craft Software Components
- **🖥️ gwent-tui**: Touchscreen kiosk (greetd → cage → kitty → gwent-tui), coded in a Brooklyn warehouse. Renders the interactive-pick flow (`mfd/present`) and menus as on-screen popups and replies over MQTT — no OLED, no rotary
- **☕ Pub/Sub System**: Fair-trade message broker for component communication, with zero waste architecture
- **🎮 Game Control**: Organic game logic controller with gluten-free algorithms
- **🎵 SFX (pygame)**: Sound effects and audio system, mixed on vinyl
- **📋 Menus**: Hand-crafted menu system with locally-sourced UI elements

### 📨 Message Topics
- **mfd**: Interactive-pick content (`mfd/present`) — rendered by the TUI as an on-screen popup, no longer an OLED
- **choosepresent**: Pick replies (`mfd/choose`) — sent by the TUI tap (was the rotary)
- **cards**: Card data messages
- **raw**: Raw RFID data
- **readwrite**: RFID write commands
- **play**: Game play actions
- **sfxctrl**: Sound effect control messages

### 💿 Vinyl Collection Game States
> Deep cuts: the server now auto-deals a random game at startup and after every Game Over, so **Register Leaders** and **Register Decks** are rare B-sides — still pressed in code, never on the active turntable.

- **🎵 Register Leaders**: Leader card registration phase, pressed on 180g vinyl (no longer reachable)
- **🎵 Register Decks**: Deck registration phase, limited edition pressing (no longer reachable)
- **🎵 Deal Cards**: Card dealing phase, with analog warmth
- **🎵 Play Round**: Round gameplay phase, remastered from original tapes
- **🎵 Play Leader**: Leader card play phase, collector's edition
- **🎵 Round End**: End of round processing, with bonus tracks
- **🎵 Game End**: End of game processing, includes digital download code

### ⌨️ Vintage Display Components
- **🃏 Board/Hand**: Letterpress-printed card display areas
- **⚰️ Grave**: Reclaimed soil graveyard display
- **🎴 Deck**: Sustainably harvested deck display
- **👤 Player**: Free-range player information display
- **⚔️ Close**: Artisanal close combat row display
- **🏹 Range**: Hand-forged ranged combat row display
- **🏰 Siege Tot**: Small-batch siege total display, aged in oak barrels