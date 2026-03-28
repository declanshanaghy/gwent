---
name: implement-leaders
description: Pick two opposing faction leaders from open GH issues, implement their abilities, generate test recordings, and playtest
user_invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, TaskCreate, TaskUpdate, TaskGet, Skill
---

Implement and test leader abilities for two opposing factions.

## Usage

`/implement-leaders <faction1> <faction2> [--generate-decks]`

- **--generate-decks**: Skip reuse of existing recordings/templates and force a fresh call to `/build-decks` to generate new decks.

Faction names: `monsters`, `northern-realms`, `nilfgaardian`, `scoiatael`, `skellige`

## Procedure

### 1. Find open leader issues for both factions

Search GitHub for **open** leader issues matching both factions:

```bash
gh issue list --state open --search "Leader" --json number,title --jq '.[] | select(.title | test("PATTERN")) | "#\(.number) \(.title)"'
```

Filter to issues whose titles reference leader cards from the two requested factions. Present results and use **AskUserQuestion** to let the user pick which two leaders to face off.

### 2. Create task list

Use **TaskCreate** to track all work:
1. Generate test recording file
2. Implement leader handler(s) in `play_round.py` (one task per handler needed)
3. Write RFID cards for leaders (if missing)
4. Reinstall package
5. Playtest with recording

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

### 5. Reinstall and launch

```bash
cd software/gwent && pip install -e . -q
```

Then use `/playback-trace NNN-faction1-vs-faction2` to load the recording and start testing.

### 6. Close issues

After successful playtest, close the implemented issues:
```bash
gh issue close NN --comment "Implemented and verified in recording NNN-faction1-vs-faction2.json"
```

### 7. Update issues with recording details

For each issue involved, add a comment with the recording file path and load command.
