# MQTT Commands for Game Control

## Connection

All commands use: `mosquitto_pub -h localhost -p 1883 -u geralt -P gwent`

Abbreviated as `MQPUB` below.

## Card scan (play a card, leader, or provide a follow-up scan)

**Topic:** `gwent/cards/raw/read`

```bash
MQPUB -t gwent/cards/raw/read -m '<full card JSON>'
```

The card JSON must include at minimum `kind`, `name`, `rfid`, and `faction`. Use the exact JSON from the game state — the `hands`, `decks`, `discard`, or `leaders` arrays contain the full card objects.

**Example:**
```bash
mosquitto_pub -h localhost -p 1883 -u geralt -P gwent \
  -t gwent/cards/raw/read \
  -m '{"kind":"card","rfid":482376306092,"name":"Biting Frost: 2","faction":"Neutral","specialty":"weather","ranges":["close"],"strength":0}'
```

## Choice (pass, row selection)

**Topic:** `gwent/mfd/choose`

```bash
MQPUB -t gwent/mfd/choose -m '{"kind":"choice","id":"<ID>","text":"<LABEL>"}'
```

### Pass
```bash
mosquitto_pub -h localhost -p 1883 -u geralt -P gwent \
  -t gwent/mfd/choose \
  -m '{"kind":"choice","id":"p","text":"Pass"}'
```

### Row selection (agile cards)
After publishing an agile card, the game prompts for a row. Choice ID is the zero-based index into the card's `ranges` array:

```bash
# If card.ranges = ["close", "ranged"], pick close (index 0):
mosquitto_pub -h localhost -p 1883 -u geralt -P gwent \
  -t gwent/mfd/choose \
  -m '{"kind":"choice","id":"0","text":"close"}'

# Pick ranged (index 1):
mosquitto_pub -h localhost -p 1883 -u geralt -P gwent \
  -t gwent/mfd/choose \
  -m '{"kind":"choice","id":"1","text":"ranged"}'
```

## Multi-step action sequences

**IMPORTANT:** Wait 0.6 seconds (`sleep 0.6`) between each publish to let the game server process the previous message.

### Agile card
1. Publish card scan
2. Sleep 0.6s
3. Publish row choice (index into card's ranges)

### Spy card
1. Publish card scan (game places it on opponent's board)
2. Sleep 0.6s
3. Publish 1st deck card scan (game draws it to hand)
4. Sleep 0.6s
5. Publish 2nd deck card scan (game draws it to hand)

Use the top 2 cards from the current player's `decks` array.

### Medic card
1. Publish card scan (game places it and enters medic mode)
2. Sleep 0.6s
3. Publish target card scan from player's `discard` array (game resurrects it)

If medic_random flag is active, the game auto-picks — skip step 3.

### Decoy card
1. Publish decoy card scan
2. Sleep 0.6s
3. Publish target card scan from player's board rows (game swaps them)

Target must be a non-hero card currently on the player's board.

### Leader abilities requiring follow-up

After publishing the leader card scan, wait 0.6s then:

| Ability | Follow-up |
|---------|-----------|
| `draw_opponent_discard` | Publish chosen card from opponent's discard |
| `draw_own_discard` | Publish chosen card from player's discard (non-hero only) |
| `weather_ranges` | Publish chosen weather card from player's deck |
| `discard_and_draw` | Publish N cards from hand (discarded), then M cards from deck (drawn) |
| `commander_ranges` | None (auto-resolves) |
| `clear_weather` | None (auto-resolves) |
| `reshuffle_graveyards` | None (auto-resolves) |
| `spy_doubling` | None (auto-resolves) |
| `medic_random` | None (auto-resolves) |
| `optimize_agile` | None (auto-resolves) |
| `view_opponent_hand` | None (auto-resolves, but note revealed cards) |
| `cancel_leader` | None (auto-resolves) |
| `extra_draw` | None (already applied at game start) |

## Card types that auto-resolve (single publish)

These only need the card scan — no follow-up:
- Weather cards (Biting Frost, Impenetrable Fog, Torrential Rain, Clear Weather)
- Scorch (specialty)
- Mardroeme
- Commander's Horn (specialty)
- Normal unit cards (non-agile, no spy/medic/muster abilities)
- Muster cards (game auto-summons matching cards)
- Bond/morale/scorch-ability cards (abilities calculated in scoring or triggered automatically)
