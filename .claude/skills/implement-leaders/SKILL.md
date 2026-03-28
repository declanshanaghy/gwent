---
name: implement-leaders
description: Pick two opposing faction leaders from open GH issues, implement their abilities, generate test recordings, and playtest
user_invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, TaskCreate, TaskUpdate, TaskGet, Skill
---

Implement and test leader abilities for two opposing factions.

## Usage

`/implement-leaders [faction1] [faction2] [--generate-decks]`

- **faction1/faction2**: Optional. If omitted, auto-detect from open GitHub issues (see below).
- **--generate-decks**: Skip reuse of existing recordings/templates and force a fresh call to `/build-decks` to generate new decks.

Faction names: `monsters`, `northern-realms`, `nilfgaardian`, `scoiatael`, `skellige`

## Procedure

### 1. Auto-select leaders from open GitHub issues

First, fetch **all** open leader issues:

```bash
gh issue list --state open --search "Leader" --json number,title --jq '.[] | "#\(.number) \(.title)"'
```

**Leader name → faction mapping:**
- `Eredin` → Monsters (`software/data/cards/Monsters/Eredin*.json`)
- `Foltest` → Northern Realms (`software/data/cards/NorthernRealms/Foltest*.json`)
- `Emhyr` → Nilfgaardian (`software/data/cards/Nilfgaardian/Emhyr*.json`)
- `Francesca` → Scoia'tael (`software/data/cards/Scoiatael/Francesca*.json`)
- `Crachan` → Skellige (`software/data/cards/Skellige/Crachan*.json`)

#### If no factions were given

Auto-detect factions from open issues:
1. Group open leader issues by faction using the name mapping above.
2. If **two or more factions** have open issues: pick the **two factions with the most open issues** (break ties by lowest issue number). This creates the most productive matchup.
3. If **only one faction** has open issues: use that faction paired with any other faction (prefer one that has already-implemented leaders for interesting gameplay).
4. If **no open issues** exist: tell the user all leaders are implemented and stop.

#### If factions were given

Filter open issues to those matching the two requested factions.

#### Leader selection rules (apply in both cases)

1. If **both factions** have open issues: pick the **first open issue from each faction** (lowest issue number).
2. If **only one faction** has open issues: pick that faction's first open issue. For the other faction (all leaders already implemented), pick any already-implemented leader — prefer one whose ability creates interesting gameplay with the unimplemented leader (e.g., pick a leader with weather if the opponent has clear_weather).
3. If **neither faction** has open issues: tell the user all leaders for these factions are implemented and stop.

Present the auto-selected matchup to the user for confirmation: show the two leaders, their abilities, and the associated issue numbers. Only use **AskUserQuestion** if something is ambiguous (e.g., multiple open issues for the same faction and you want the user to prioritize).

### 2. Create task list

Use **TaskCreate** to track all work:
1. Generate test recording file
2. Implement leader handler(s) in `play_round.py` (one task per handler needed)
3. Reinstall package
4. Write integration test validator(s)
5. Run validator — fix loop (up to 3 iterations)
6. Close GitHub issue(s)

Mark each task as `in_progress` when starting and `completed` when done.

### 3. Generate test recording

**Recordings dir**: `software/gwent/gwent/game/recordings/`
**Naming convention**: `NNN-faction1-vs-faction2.json` (3-digit zero-padded index)

#### If `--generate-decks` was passed

Skip all reuse checks below and jump straight to calling `/build-decks <faction1> vs <faction2>` to generate fresh decks, then save the output as a recording JSON.

#### Check for exact match first

Before creating anything, check if a recording already exists with these exact two leaders. Run a Python snippet that loads every matching recording and compares the leader names:

```bash
python3 -c "
import json, glob
leader1_name = '<LEADER1 NAME>'
leader2_name = '<LEADER2 NAME>'
for f in sorted(glob.glob('software/gwent/gwent/game/recordings/*faction*faction*.json')):
    s = json.load(open(f))
    l1 = s.get('state',{}).get('board',{}).get('leaders',{}).get('PLAYER.ONE',{}).get('name','')
    l2 = s.get('state',{}).get('board',{}).get('leaders',{}).get('PLAYER.TWO',{}).get('name','')
    if (l1 == leader1_name and l2 == leader2_name) or (l1 == leader2_name and l2 == leader1_name):
        print(f'EXACT MATCH: {f}')
"
```

**If an exact match exists**: Reuse it — skip recording generation entirely. Tell the user which file matched.

#### Find existing template (no exact match)

Look for existing recordings with index > 011 matching both factions:
```bash
ls software/gwent/gwent/game/recordings/*faction1*faction2*.json 2>/dev/null
ls software/gwent/gwent/game/recordings/*faction2*faction1*.json 2>/dev/null
```

**If a template exists**: Copy it, replace both leaders with the new ones (in `state.leader1`, `state.leader2`, `state.board.leaders.PLAYER.ONE`, `state.board.leaders.PLAYER.TWO`), save with the next sequential index number.

**If no template exists**: Use `/build-decks <faction1> vs <faction2>` to build new decks, then save the output as a recording JSON.

#### Determine next index number
```bash
ls software/gwent/gwent/game/recordings/*.json | sort | tail -1
```
Increment the prefix number by 1.

### 4. Check and implement leader handlers

Read `software/gwent/gwent/game/stages/play_round.py`, specifically `_play_leader()` dispatch.

For each leader's ability key from the JSON:
- Check if `_play_leader()` already dispatches to a handler for that key
- If YES: no code change needed, mark as already implemented
- If NO: implement the handler

**Implementation pattern** — add to `_play_leader()` dispatch chain:
```python
elif leader_data.get("new_key"):
    self._leader_new_handler(leader_data)
```

Then add the handler method near the other `_leader_*` methods.

**Common handler patterns:**
- `commander_ranges`: Already handled — just needs the JSON key (data fix only)
- `clear_weather`: `self._board.weather_rows.clear()`
- `draw_own_discard`: Like `_leader_draw_opponent_discard()` but from own discard
- `conditional_scorch`: Sum opponent's non-hero strength in target row, destroy strongest if ≥ threshold
- `spy_doubling`: Set flag on board, modify scoring
- `discard_and_draw`: Multi-step: scan N cards from hand to discard, then scan M from deck to draw
- `cancel_leader`: Set `opponent.leader_used = True`
- `view_opponent_hand`: Display N random cards from opponent's hand
- `medic_random`: Set flag so medic auto-picks random
- `extra_draw`: Draw N extra cards (triggers during deal, not play round)
- `optimize_agile`: Move agile units to optimal rows

### 5. Reinstall package

```bash
cd software/gwent && pip install -e . -q
```

### 6. Write integration tests (pytest)

**Directory**: `software/gwent/integration-tests/`
**Shared fixtures**: `software/gwent/integration-tests/conftest.py` (already exists — provides `game`, `recording`, `mqtt_client` fixtures and `GameAPI` helper)
**Naming**: `test_{leader_ability_key}_validator.py` (e.g., `test_discard_and_draw_validator.py`)

**IMPORTANT**: Write tests for **BOTH** leaders in the matchup, not just the newly implemented one. Already-implemented leaders that lack a test file still need one.

Before writing a new test, check if one already exists for each leader's ability key:
```bash
ls software/gwent/integration-tests/test_*_validator.py 2>/dev/null
```
If a matching validator already exists, reuse it. Only write a new one for abilities that lack a test.

#### Test structure

Each validator is a **pytest** test module that uses shared fixtures from `conftest.py`:
- `game` — `GameAPI` instance with helpers: `inject_card_and_wait()`, `wait_for_current_player()`, `get_board()`, `get_state()`
- `recording` — parsed recording JSON dict
- `mqtt_client` — connected paho MQTT client

Recording path is passed via `--recording` CLI flag.

**Template** — write validators following this pattern:

```python
"""Integration test for {leader_name} — {ability_description}.

Run:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start
    pytest software/gwent/integration-tests/test_{ability_key}_validator.py \
        --recording <recording.json> -v
"""

from conftest import card_names


class TestAbilityName:

    def test_initial_state(self, game, recording):
        """Verify the game loaded correctly."""
        state = game.get_state()
        board = state["state"]["board"]
        assert state["active_stage"] == "PlayRound"
        # ...more initial state checks...

    def test_ability_full_flow(self, game, recording):
        """Exercise the leader ability and assert outcomes."""
        rec = recording["state"]
        leader = rec["leader1"]  # or leader2

        # Inject card and wait for state change
        state = game.inject_card_and_wait(leader)
        board = state["state"]["board"]

        # Assert outcomes
        assert board["players"]["PLAYER.ONE"]["leader_used"] is True

        # Wait for turn advancement (deferred after TTS)
        board = game.wait_for_current_player("PLAYER.TWO")
        assert board["current_player"] == "PLAYER.TWO"
```

**Key `GameAPI` methods:**
- `game.inject_card_and_wait(card_json)` — inject card via MQTT, wait for state change, return new state
- `game.wait_for_current_player(player)` — poll until `current_player` matches (handles TTS delay)
- `game.get_state()` / `game.get_board()` — fetch current state from HTTP API
- `game.inject_choice(choice_id)` — send MFD choice via MQTT

**Key assertions by ability type:**
- `spy_doubling`: After activating, play a spy card → assert score = 2× spy strength on opponent's board
- `discard_and_draw`: After activating, scan 2 hand cards + 1 deck card → assert hand size = original - 2 + 1, discarded cards in discard pile
- `conditional_scorch`: Play units to exceed threshold → activate → assert strongest destroyed
- `commander_ranges`: Activate → assert horn applied to correct row, score doubled
- `clear_weather`: Play weather first, then activate → assert weather_rows empty
- `draw_own_discard`: Put card in discard first → activate + scan discard card → assert card back in hand

### 7. Run integration test loop

After writing the tests, execute them in a fix loop. **Both** leader tests must pass.

**Step 1 — Launch game with recording:**
```bash
bash scripts/dev-server.sh gwent stop 2>/dev/null
GWENT_STATE=<absolute-recording-path> bash scripts/dev-server.sh gwent start
sleep 4
```

**Step 2 — Run ALL validators for this matchup:**
```bash
pytest software/gwent/integration-tests/test_{ability1}_validator.py \
       software/gwent/integration-tests/test_{ability2}_validator.py \
       --recording <absolute-recording-path> -v
```

Note: tests that modify game state (playing cards, using leader abilities) affect each other. If both leaders need testing in the same game session, **order matters** — run the PLAYER.ONE leader test first, then the PLAYER.TWO leader test. If tests cannot coexist in one session, restart the game between them.

**Step 3 — If ALL tests PASS:** proceed to step 8 (close issues).

**Step 4 — If any test FAILS (iteration ≤ 3):**
1. Create a task: "Fix: {failure description}"
2. Read the game log (`/tmp/logs/gwent.log`) for error context — grep for ERROR, the ability key, and the leader name
3. Diagnose the root cause from the pytest output + logs
4. Fix the code (in `play_round.py`, `board.py`, or the leader JSON)
5. Reinstall: `cd software/gwent && pip install -e . -q`
6. Restart game with recording and re-run ALL validators
7. Mark the fix task as completed

**Step 5 — If 3 fix iterations exhausted without passing:**
1. Stop and present a summary to the user:
   - What the test expected vs. what it got
   - Relevant log excerpts
   - What was tried in each fix iteration
   - Suggested next steps
2. Do NOT close the GitHub issue

### 8. Close issues

Only after ALL validators pass:
```bash
gh issue close NN --comment "Implemented and validated via integration test.

Recording: NNN-faction1-vs-faction2.json
Validator: software/gwent/integration-tests/test_{ability_key}_validator.py

Load: /playback-trace NNN-faction1-vs-faction2
Test: pytest software/gwent/integration-tests/test_{ability_key}_validator.py --recording <recording> -v"
```
