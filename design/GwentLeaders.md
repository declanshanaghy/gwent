# Leader Abilities

Leaders have a **one-time ability** usable once per game. The player scans their leader card during their turn to activate it. Once used, `leader_used` is set and the ability cannot be triggered again.

## Ability Types

Leader abilities are dispatched by JSON keys in the `leader` object on the card data. The game checks for these keys in order:

1. `weather_ranges` → Pick weather from deck
2. `commander_ranges` → Apply commander horn
3. `draw_opponent_discard` → Steal from opponent's discard
4. `reshuffle_graveyards` → Shuffle all discards back to decks

If none of these keys are present, the ability is **unimplemented** — the game shows an error and does not consume the ability.

---

## Implemented Abilities

### Pick Weather from Deck (`weather_ranges`)

Search the player's deck for weather cards matching the specified ranges and play one instantly.

- If `weather_ranges` covers all 3 rows, Clear Weather is also offered as an option
- If exactly 1 matching weather card exists, it's auto-played
- If multiple exist, the player chooses from a menu
- If none exist, announces "No weather cards in deck!"

**Leaders with this ability:**

| Leader | Faction | Ranges | Description |
|---|---|---|---|
| Eredin - King of the Wild Hunt | Monsters | close, ranged, siege | Pick any weather card |
| Emhyr var Emreis - His Imperial Majesty | Nilfgaardian | siege | Pick a Torrential Rain card |
| Foltest - King of Temeria | Northern Realms | ranged | Pick an Impenetrable Fog card |
| Francesca Findabair - Pureblood Elf | Scoia'tael | close | Pick a Biting Frost card |

### Apply Commander Horn (`commander_ranges`)

Immediately apply Commander's Horn effect to the specified rows, doubling all non-hero unit strengths.

**Leaders with this ability:**

| Leader | Faction | Ranges | Description |
|---|---|---|---|
| Francesca Findabair - The Beautiful | Scoia'tael | ranged | Doubles ranged combat units |

### Draw from Opponent's Discard (`draw_opponent_discard`)

Pick one card from the opponent's discard pile and add it to the player's hand.

- Player scans the desired card from the opponent's discard
- If opponent's discard is empty, announces "Opponent's discard pile is empty"

**Leaders with this ability:**

| Leader | Faction | Description |
|---|---|---|
| Emhyr var Emreis - The Relentless | Nilfgaardian | Draw a card from opponent's discard |

### Reshuffle Graveyards (`reshuffle_graveyards`)

Shuffle all discard piles (BOTH players) back into their respective decks.

**Leaders with this ability:**

| Leader | Faction | Description |
|---|---|---|
| Crach an Craite | Skellige | Shuffle all graveyards back into decks |

---

## Unimplemented Leaders

These leaders have `instructions` text but no implementation key. Playing them shows an error and does not consume the ability.

| Leader | Faction | Instructions |
|---|---|---|
| Eredin Breacc Glas: the Treacherous | Monsters | Doubles the strength of all spy cards (both players) |
| Eredin: Bringer of Death | Monsters | Restore a card from your discard pile to your hand |
| Eredin: Commander of the Red Riders | Monsters | Double close combat units (unless horn present) |
| Eredin: Destroyer of Worlds | Monsters | Discard 2 cards, draw 1 card of choice from deck |
| Emhyr var Emreis: Emperor of Nilfgaard | Nilfgaardian | Look at 3 random cards from opponent's hand |
| Emhyr var Emreis: Invader of the North | Nilfgaardian | Restore abilities affect random unit (both players) |
| Emhyr var Emreis: The White Flame | Nilfgaardian | Cancel opponent's leader abilities |
| Foltest: Lord Commander of the North | Northern Realms | Clear all weather effects |
| Foltest: Son of Medell | Northern Realms | Destroy enemy's strongest ranged unit(s) if total >= 10 |
| Foltest: the Siegemaster | Northern Realms | Double siege units (unless horn present) |
| Foltest: The Steel-Forged | Northern Realms | Destroy enemy's strongest siege unit(s) if total >= 10 |
| Francesca Findabair: Daisy of the Valley | Scoia'tael | Draw an extra card at battle start |
| Francesca Findabair: Hope of the aen Seidhe | Scoia'tael | Move agile units to optimal row |
| Francesca Findabair: Queen of Dol Blathanna | Scoia'tael | Destroy enemy's strongest close unit(s) if total >= 10 |
