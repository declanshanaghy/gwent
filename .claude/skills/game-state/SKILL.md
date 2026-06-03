---
description: Dump and display the current gwent game state (scores, lives, hands, board, status)
user_invocable: true
---

Dump the current game state by reading the retained `gwent/server/state` MQTT
topic, then display it as formatted tables.

## Steps

1. Verify gwent is running:
   ```bash
   pgrep -f '/home/dshanaghy/gwent-venv/bin/gwent'
   ```
   If not running, tell the user "No gwent process running." and stop.

2. Read the retained state snapshot from MQTT into a temp file:
   ```bash
   mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1 -W 4 \
     > /tmp/gwent-game-state.json
   ```

3. Read `/tmp/gwent-game-state.json` using the Read tool.

4. Clean up the temp file:
   ```bash
   rm -f /tmp/gwent-game-state.json
   ```

5. Display the game state using markdown tables with emoji theming.

## Rendering Rules

### Use standard markdown tables ONLY
Use `| col1 | col2 |` style markdown tables. NEVER use box-drawing characters (`┌─┬─┐`, `│`, etc.) or code blocks for tables — they misalign with emoji.
Do NOT use ANSI escape codes — they render as raw text in markdown.

## Emoji Reference

### Faction Emojis
- **Northern Realms** 🦁⚜️
- **Nilfgaardian** 🌑☀️
- **Scoia'tael** 🌿🏹
- **Monsters** 👹🔥
- **Skellige** ⚓🪓

### Card Type Emojis
Prefix EVERY card with its type emoji:
- ⚔️ Close combat unit
- 🏹 Ranged combat unit
- 🏰 Siege unit
- 🌨️ Biting Frost (weather)
- 🌫️ Impenetrable Fog (weather)
- 🌧️ Torrential Rain (weather)
- ☀️ Clear Weather
- 🔥 Scorch
- 🎭 Decoy
- 📯 Commander's Horn
- 🛡️ Hero (add alongside range emoji, e.g. ⚔️🛡️)
- 🩺 Medic ability
- 👥 Muster ability
- 🤝 Tight Bond ability
- 🕵️ Spy ability
- 💪 Morale boost ability
- 🐻 Berserker/Mardroeme

### Row Emojis
- ⚔️ Close row
- 🏹 Ranged row
- 🏰 Siege row

## Sections to Display

### ⚔️ Status
Single bold line: **⚔️ Round X | 📊 P1=X P2=X | 🎯 Turn: Player N | 📍 Stage**

### 💎 Lives
Markdown table. Use 💎 per life, 💀 per lost gem. Faction emoji in header.

| Player 1 🌿🏹 | Player 2 ⚓🪓 |
|---|---|
| 💎💎 | 💎💀 |

### ⚔️ Board
Markdown table with 2 columns. Three rows for close/ranged/siege.
Each row shows cards with type emoji and strength, row total with ⚡.
Weather on row: append 🌨️❄️ / 🌫️👁️ / 🌧️💧 to row header.
Commander horn on row: append 📯🔊.

| 🌿🏹 P1 (Scoia'tael) | ⚓🪓 P2 (Skellige) |
|---|---|
| **⚔️ Close:** ⚔️🛡️ Ciri (15) ⚡15 | **⚔️ Close:** ⚔️ Ghoul (4) ⚡4 |
| **🏹 Ranged:** — ⚡0 | **🏹 Ranged:** 🏹 Archer (6) ⚡6 |
| **🏰 Siege:** — ⚡0 | **🏰 Siege:** — ⚡0 |
| **TOTAL: 15** | **TOTAL: 10** |

### 🃏 Hands
Markdown table. Leader first with 👑. Cards with type + ability emojis.
Ownership suffix: owner initials or ⭐ for starter.

| 🌿🏹 P1 - Scoia'tael (N cards) | ⚓🪓 P2 - Skellige (N cards) |
|---|---|
| 👑 Leader Name ⭐ | 👑 Leader Name DS |
| 🔥 Scorch DS | 🎭 Decoy: 1 DS |

### 🗑️ Discard Piles
Markdown table. Only show if discards exist. Card type emojis.

### 📦 Deck Remaining
Markdown table. Card count in header. List cards with type emojis.
Do NOT show leaders here (they are in board.leaders, shown in Hands).

### 🌦️ Weather & Effects
Only show if active. Bullet list with weather emojis.

### ✋ Passed
🏳️ prefix for passed players. "Neither player has passed." if none.

## Important Notes
- Leaders are stored in `board.leaders`, NOT in `board.decks` or `board.hands`. Show them as the first entry in the Hands section with 👑.
- Cards with `specialty: "hero"` are immune to weather — don't mark them as affected.
- Agile cards (multiple ranges) show combined range emojis: ⚔️🏹
- NEVER use box-drawing characters or code blocks for tables. Only use markdown `| |` tables.
