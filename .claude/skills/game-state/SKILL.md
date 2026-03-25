---
description: Dump and display the current gwent game state (scores, lives, hands, board, status)
user_invocable: true
---

Dump the current game state by sending SIGUSR1 to the gwent process, then display it as formatted tables.

## Steps

1. Verify gwent is running:
   ```bash
   pgrep -f '/home/dshanaghy/gwent-venv/bin/gwent'
   ```
   If not running, tell the user "No gwent process running." and stop.

2. Write a temp path to `/tmp/gwent-save-as` and send SIGUSR1:
   ```bash
   echo "/tmp/gwent-game-state.json" > /tmp/gwent-save-as
   kill -USR1 $(pgrep -f '/home/dshanaghy/gwent-venv/bin/gwent')
   sleep 2
   ```

3. Read `/tmp/gwent-game-state.json` using the Read tool.

4. Clean up the temp file:
   ```bash
   rm -f /tmp/gwent-game-state.json
   ```

5. Display the game state using these tables:

### Status
Show a single-line summary: **Round X | Score: P1=X P2=X | Turn: Player N | Stage: StageName**

### Lives (Gems)
| Player 1 | Player 2 |
|---|---|
| gems value | gems value |

Use a gem emoji per life remaining (e.g. 2 gems = "💎💎").

### Board
One table with 2 columns. Show cards played in each row (close/ranged/siege). Include card strength in parentheses. Show row totals.

| Player 1 (Faction) | Player 2 (Faction) |
|---|---|
| **Close:** card1 (str), card2 (str) | **Close:** card1 (str) |
| **Ranged:** — | **Ranged:** card1 (str) |
| **Siege:** — | **Siege:** — |

If weather is active on a row, note it (e.g. "🌧 Frost" next to close row).
If a commander horn is active on a row, note it (e.g. "📯" next to the row).

### Hands
One table with 2 columns listing cards in each player's hand with strength.

| Player 1 (N cards) | Player 2 (N cards) |
|---|---|
| Card Name (str) | Card Name (str) |

### Weather & Effects
Only show this section if there are active weather effects or commander horns.

### Passed
Note if either player has passed this round.
