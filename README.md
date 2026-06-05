# Gwent Companion

<div align="center">
  <img src="design/logo/gwent_logo_v9.png" alt="Gwent Companion Logo" width="800">
</div>

A Raspberry Pi-based digital companion for the physical card game Gwent from The Witcher III. Players use RFID-tagged physical cards; the companion tracks scores, manages game state, and guides players through the game.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#333',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px'
  }
}}%%

flowchart LR
    subgraph physical["🃏 Physical Layer"]
        cards["💳 RFID Cards"]
        mat["🧵 Game Mat"]
    end

    subgraph hw["🔧 Hardware"]
        rfid["📡 RFID Reader"]
        matrix["🔢 LED Matrices"]
        touch["🖐️ 7\" Touchscreen"]
        camhw["📷 NoIR Camera"]
    end

    subgraph server["💻 Game Server"]
        gwent["🎮 gwent service"]
        mqtt_pub["📨 MQTT Publisher"]
    end

    camsvc["📷 gwent-camera\n+ nginx :80"]
    broker["📡 MQTT Broker\nMosquitto"]

    subgraph clients["👁️ Kiosk & Drivers"]
        tui["📊 gwent-tui\n(touchscreen kiosk)"]
        loop["🤖 game-loop.py"]
    end

    cards -.- rfid
    rfid --- gwent
    matrix --- gwent
    gwent --- mqtt_pub
    mqtt_pub --> broker
    broker <--> tui
    broker <--> loop
    tui --- touch
    camsvc --> camhw
    tui -.->|"/camera/*"| camsvc

    classDef hardware fill:#A1887F,stroke:#5D4037,stroke-width:2px,color:#fff,font-family:'Courier New',font-weight:bold
    classDef software fill:#BCAAA4,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-weight:bold
    classDef data fill:#D7CCC8,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-style:italic

    class cards,mat data
    class rfid,matrix,touch,camhw hardware
    class gwent,mqtt_pub,broker,tui,loop,camsvc software
```

## How It Works

1. The `gwent` system service runs on a Raspberry Pi, managing game state and driving all hardware. It always has a game in progress — a fresh random game is dealt at startup and after every Game Over
2. Players scan RFID-tagged cards on the reader to play cards; the 7" touchscreen runs the `gwent-tui` kiosk for assignment, menus, and live view
3. The server publishes every game state change over MQTT, including a retained full-state snapshot on `gwent/server/state`
4. Clients consume that retained snapshot — there is no HTTP API on the game server; all command and control is over MQTT (`gwent/ctrl/*` in)
5. The **gwent-tui** terminal dashboard subscribes to MQTT and renders a live view of the game on the touchscreen
6. The **game-loop.py** orchestrator pits two LLM models against each other by reading the retained snapshot and publishing moves over MQTT
7. A separate **gwent-camera** service drives a Pi NoIR camera and serves stills, an MJPEG stream, and game recordings over HTTP (nginx `/camera/*`)

## Components

### Game Server (`software/gwent/`)

The core Python service. Runs as a systemd unit (`gwent`).

- **Game stages state machine** -- DealCards, PlayRound, RoundEnd, GameOver (auto-dealt; there is no main menu)
- **MQTT command & control** -- all events and full game state are published to `gwent/` topics via a Mosquitto broker. State is a retained snapshot on `gwent/server/state`; commands (players, client-tts) come in on `gwent/ctrl/*`. No HTTP.
- **Hardware abstraction layer** -- SPI (RFID RC522), I2C (TCA9548A mux, IS31FL3731 LED matrices). The legacy SSD1306 OLED + rotary-encoder MFD drivers remain in the tree but are disabled (`GWENT_DISABLE_MFD=true`) and physically removed
- **Audio system** -- sound effects and TTS announcements (multiple providers: gTTS, ElevenLabs, OpenAI, Piper, macOS `say`)

### Terminal Dashboard (`software/gwent-tui/`)

A [Textual](https://textual.textualize.io/)-based Rich terminal app that renders a live game dashboard, running as the touchscreen kiosk (greetd → cage → kitty → gwent-tui, with a `gwent-touch` evdev bridge). Subscribes to MQTT — including the retained `gwent/server/state` snapshot — and provides hamburger-menu controls (player assignment, camera on/off, live view) plus a floating camera live-view panel. Stage-specific widgets mirror the server's state machine.

### LLM-vs-LLM Orchestrator (`.claude/skills/llm-vs/scripts/game-loop.py`)

Drives fully automated games between two LLM models. Supports multiple providers (Anthropic, OpenAI, Google Gemini, Ollama) with model aliases. Reads game state from the retained `gwent/server/state` MQTT snapshot, constructs prompts with full board context, and submits moves via MQTT.

### Camera Service (`scripts/camera-server.py`)

A standalone `gwent-camera` systemd service (system Python + picamera2) owns the Pi NoIR camera and exposes stills, an MJPEG stream, and game recordings via nginx on port 80 (`/camera/{still,stream,recordings/}`). It is also an MQTT client (`gwent/camera/ctrl` in, retained `gwent/camera/state` out) and records each game to H.264 with a 10 GiB disk budget.

### Shared Utilities (`software/gwent-shared/`)

TTS provider abstractions shared between server and TUI. No hardware dependencies.

## Hardware

| Bus | Device | Purpose |
|-----|--------|---------|
| SPI CE0 | MFRC522 | RFID card reader |
| I2C (via TCA9548A mux) | IS31FL3731 Ch 0 | Gem display (lives) |
| I2C (via TCA9548A mux) | IS31FL3731 Ch 1 | Player 1 score |
| I2C (via TCA9548A mux) | IS31FL3731 Ch 2 | Player 2 score |
| DSI / USB | 7" Touchscreen | Kiosk UI (gwent-tui) + speakers |
| CSI | Pi NoIR Camera (IMX219) | Table view, stills/stream, game recordings |

## Card Data

Each card is a JSON file in `software/data/cards/{Faction}/CardName.json`:

```json
{
  "faction": "Monsters",
  "name": "Arachas: 1",
  "strength": 4,
  "ranges": ["close"],
  "abilities": ["muster"],
  "starter": true,
  "rfid": 622264733154
}
```

Five factions: **Monsters**, **Nilfgaardian**, **Northern Realms**, **Scoiatael**, **Skellige**, plus **Neutral** cards.

## Development

```bash
# Start the dev server
bash scripts/dev-server.sh gwent start

# Dump current game state (retained snapshot)
mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1

# Run the TUI
gwent-tui

# Run an LLM vs LLM game
python3 .claude/skills/llm-vs/scripts/game-loop.py \
  --model-p1 anthropic/sonnet --model-p2 gemini/flash
```

Always use `SIGTERM` for graceful shutdown (never `SIGKILL`) -- hardware cleanup is required.

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](design/GwentArchitecture.md) | Full system architecture reference |
| [Game Rules](design/GwentRules.md) | Canonical Gwent rules as implemented |
| [Game Stages](design/GwentGameStages.md) | State machine and flow diagrams |
| [PubSub Architecture](design/GwentPubSub.md) | MQTT messaging system design |
| [Product Requirements](design/000-product-requirements.md) | Original PRD |
| [Mermaid Style Guide](design/MermaidStyleGuide.md) | Diagram styling conventions |
