# Gwent Publish-Subscribe Architecture

This diagram represents the publish-subscribe architecture used for communication between components in the Gwent Companion system.

```mermaid
flowchart TB
    %% Hardware Components
    subgraph Hardware
        rfidReader["RFID Reader\n(MFRC522)"]
        rfidWriter["RFID Writer"]
        display["Display"]
        rotaryBtn["Rotary Button"]
    end

    %% Software Components
    subgraph Software
        mfd["MFD"]
        pubsub["Pub/Sub System"]
        gameControl["Game Control"]
        sfx["SFX\n(pygame)"]
        menus["Menus"]
    end

    %% Game States
    subgraph GameStates
        registerLeaders["Register Leaders"]
        registerDecks["Register Decks"]
        dealCards["Deal Cards"]
        playRound["Play Round"]
        playLeader["Play Leader"]
        roundEnd["Round End"]
        gameEnd["Game End"]
    end

    %% Display Components
    subgraph DisplayComponents
        boardHand["Board/Hand"]
        grave["Grave"]
        deck["Deck"]
        player["Player"]
        close["Close"]
        range["Range"]
        siegeTot["Siege Total"]
    end

    %% Message Topics
    mfdTopic["mfd"]
    choosepresentTopic["choosepresent"]
    cardsTopic["cards"]
    rawTopic["raw"]
    readwriteTopic["readwrite"]
    playTopic["play"]
    sfxctrlTopic["sfxctrl"]

    %% Connections
    rfidReader --> rawTopic
    rawTopic --> mfd
    mfd --> mfdTopic
    mfdTopic --> pubsub
    
    rotaryBtn --> choosepresentTopic
    choosepresentTopic --> pubsub
    
    pubsub --> cardsTopic
    cardsTopic --> gameControl
    
    gameControl --> playTopic
    playTopic --> pubsub
    
    pubsub --> sfxctrlTopic
    sfxctrlTopic --> sfx
    
    gameControl --> menus
    menus --> display
    
    pubsub --> readwriteTopic
    readwriteTopic --> rfidWriter
    
    gameControl --> registerLeaders
    gameControl --> registerDecks
    gameControl --> dealCards
    gameControl --> playRound
    gameControl --> playLeader
    gameControl --> roundEnd
    gameControl --> gameEnd
    
    display --> DisplayComponents
    
    %% Styling
    classDef hardware fill:#f9d5e5,stroke:#333,stroke-width:1px
    classDef software fill:#eeeeee,stroke:#333,stroke-width:1px
    classDef topic fill:#d5f9e5,stroke:#333,stroke-width:1px
    classDef gameState fill:#e5d5f9,stroke:#333,stroke-width:1px
    classDef display fill:#f9e5d5,stroke:#333,stroke-width:1px
    
    class rfidReader,rfidWriter,display,rotaryBtn hardware
    class mfd,pubsub,gameControl,sfx,menus software
    class mfdTopic,choosepresentTopic,cardsTopic,rawTopic,readwriteTopic,playTopic,sfxctrlTopic topic
    class registerLeaders,registerDecks,dealCards,playRound,playLeader,roundEnd,gameEnd gameState
    class boardHand,grave,deck,player,close,range,siegeTot display
```

## Component Descriptions

### Hardware Components
- **RFID Reader (MFRC522)**: Reads RFID tags from cards
- **RFID Writer**: Writes data to RFID tags
- **Display**: Shows game information and menus
- **Rotary Button**: User input device for navigation and selection

### Software Components
- **MFD**: Multi-Function Display controller
- **Pub/Sub System**: Central message broker for component communication
- **Game Control**: Main game logic controller
- **SFX (pygame)**: Sound effects and audio system
- **Menus**: Menu system for user interaction

### Message Topics
- **mfd**: Display control messages
- **choosepresent**: User input selection messages
- **cards**: Card data messages
- **raw**: Raw RFID data
- **readwrite**: RFID write commands
- **play**: Game play actions
- **sfxctrl**: Sound effect control messages

### Game States
- **Register Leaders**: Leader card registration phase
- **Register Decks**: Deck registration phase
- **Deal Cards**: Card dealing phase
- **Play Round**: Round gameplay phase
- **Play Leader**: Leader card play phase
- **Round End**: End of round processing
- **Game End**: End of game processing

### Display Components
- **Board/Hand**: Card display areas
- **Grave**: Graveyard display
- **Deck**: Deck display
- **Player**: Player information display
- **Close**: Close combat row display
- **Range**: Ranged combat row display
- **Siege Tot**: Siege total display