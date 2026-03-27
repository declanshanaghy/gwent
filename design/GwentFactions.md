# Faction Passive Abilities

Each faction has a unique passive ability that triggers automatically. These are not activated by the player — the game engine applies them based on game events.

## Monsters 👹🔥

**Trigger:** End of every round

**Effect:** Keep the strongest non-hero card on the board for the next round. All other cards go to discard.

**Details:**
- Scans all rows for the non-hero card with the highest base strength
- That card remains on its row; everything else is discarded
- If only hero cards remain, nothing extra is kept
- The kept card carries its strength into the next round (potentially a strong opening)

## Northern Realms 🦁⚖️

**Trigger:** End of a round the player WON

**Effect:** Draw 1 extra card from deck.

**Details:**
- Only triggers if this player won the round (not on draws or losses)
- If the deck is empty, nothing happens
- Gives card advantage for winning — rewarding aggressive play

## Skellige ⚓🪓

**Trigger:** End of every round

**Effect:** Resurrect up to 2 random non-hero cards from discard pile to hand.

**Details:**
- Selects up to 2 random non-hero cards from the discard pile
- If fewer than 2 non-hero cards in discard, resurrects all available
- Cards return to **hand** (not board) — they can be played in future rounds
- Rewards playing cards early since they come back

## Nilfgaardian 🌑☀️

**Trigger:** Round scoring (tie-breaker)

**Effect:** Win all tied rounds.

**Details:**
- When both players have equal scores, the Nilfgaardian player wins
- The opponent (non-Nilfgaardian) loses a gem on ties instead of both players losing one
- If BOTH players are Nilfgaardian (shouldn't happen in normal play), standard tie rules apply
- This is a scoring rule, not an end-of-round ability

## Scoia'tael 🌿🏹

**Trigger:** Game start

**Effect:** Coin toss to determine who goes first.

**Details:**
- At the start of round 1, a random coin toss determines the starting player
- This overrides the default "Player 1 goes first" rule
- Only applies to round 1 — subsequent rounds use the "loser goes first" rule
- If both players are Scoia'tael, the coin toss still applies

---

## Faction Ability Summary

| Faction | When | Effect | Strategic Advantage |
|---|---|---|---|
| **Monsters** | Every round end | Keep strongest non-hero | Board persistence |
| **Northern Realms** | Winning round end | Draw 1 extra card | Card advantage |
| **Skellige** | Every round end | Resurrect 2 from discard | Card recycling |
| **Nilfgaardian** | Scoring | Win ties | Defensive edge |
| **Scoia'tael** | Game start | Coin toss for first move | Tempo control |
