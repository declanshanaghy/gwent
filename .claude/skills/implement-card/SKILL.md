---
name: implement-card
description: Implement a card ability or game mechanic from a GitHub issue — fix code, write integration test, close the issue.
user_invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, TaskCreate, TaskUpdate, TaskGet, Skill
---

Implement and test a card ability or game mechanic from a GitHub issue.

## Usage

`/implement-card <issue-number>`

- Takes a single GitHub issue number
- Reads the issue to understand what needs implementing
- Implements the fix, writes an integration test, and closes the issue

## Procedure

### 1. Read the issue

```bash
gh issue view <N> --json title,body,labels,state
```

Parse the issue to identify:
- **What's broken or missing** — the card ability, mechanic, or bug
- **Affected code** — file paths mentioned in the issue body
- **Acceptance criteria** — the expected behavior

### 2. Create task list

Use **TaskCreate** to track all work:
1. Explore affected code
2. Implement the fix
3. Reinstall package
4. Generate/reuse test recording
5. Write integration test
6. Run test — fix loop (up to 3 iterations)
7. Close GitHub issue

### 3. Explore and implement

Read the affected files. Understand the current behavior. Implement the fix following existing patterns in the codebase.

**Key files:**
- `software/gwent/gwent/game/stages/play_round.py` — card play logic, leader handlers
- `software/gwent/gwent/game/board.py` — board state, scoring, card placement
- `software/gwent/gwent/messaging/card.py` — Card message class and properties
- `software/gwent/gwent/cards/util.py` — card loading utilities
- `software/data/cards/{Faction}/*.json` — card data

### 4. Reinstall package

```bash
cd software/gwent && pip install -e . -q
```

### 5. Generate or reuse test recording

**Recordings dir**: `software/gwent/gwent/game/recordings/`

Check if an existing recording has the right cards for testing. If not, use `/build-decks` to create one.

The recording must have the relevant cards (the card being implemented + any cards it interacts with) in the player's hand.

### 6. Write integration test

**Directory**: `software/gwent/integration-tests/`
**Naming**: `test_{mechanic}_validator.py`

Follow the pattern from existing tests (see `conftest.py` for fixtures: `game`, `recording`, `mqtt_client`).

Test structure:
1. `test_initial_state` — verify game loaded correctly
2. `test_{mechanic}_flow` — play the cards, verify the outcome

### 7. Run test loop

```bash
bash scripts/dev-server.sh gwent stop 2>/dev/null
GWENT_STATE=<recording-path> bash scripts/dev-server.sh gwent start
sleep 4
pytest software/gwent/integration-tests/test_{mechanic}_validator.py \
    --recording <recording-path> -v
```

If test fails (up to 3 iterations):
1. Read error + game log (`/tmp/logs/gwent.log`)
2. Fix the code
3. Reinstall + restart + rerun

### 8. Close issue

Only after tests pass:
```bash
gh issue close <N> --comment "Implemented and validated.

Recording: NNN-faction1-vs-faction2.json
Validator: software/gwent/integration-tests/test_{mechanic}_validator.py

Test: pytest software/gwent/integration-tests/test_{mechanic}_validator.py --recording <recording> -v"
```
