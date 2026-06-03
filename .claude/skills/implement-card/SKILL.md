---
name: implement-card
description: Implement a card ability or game mechanic from a GitHub issue — fix code, verify live, close the issue.
user_invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, TaskCreate, TaskUpdate, TaskGet, Skill
---

Implement and test a card ability or game mechanic from a GitHub issue.

## Usage

`/implement-card <issue-number>`

- Takes a single GitHub issue number
- Reads the issue to understand what needs implementing
- Implements the fix, verifies it live over MQTT, and closes the issue

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
3. Reinstall package + restart server
4. Verify live over MQTT — fix loop (up to 3 iterations)
5. Close GitHub issue

### 3. Explore and implement

Read the affected files. Understand the current behavior. Implement the fix following existing patterns in the codebase.

**Key files:**
- `software/gwent/gwent/game/stages/play_round.py` — card play logic, leader handlers
- `software/gwent/gwent/game/board.py` — board state, scoring, card placement
- `software/gwent/gwent/messaging/card.py` — Card message class and properties
- `software/gwent/gwent/cards/util.py` — card loading utilities
- `software/data/cards/{Faction}/*.json` — card data

### 4. Reinstall package + restart server

```bash
cd software/gwent && pip install -e . -q
cd - && bash scripts/dev-server.sh gwent restart
sleep 4
```

### 5. Verify live over MQTT

There are no recordings. Drive a real game over MQTT and observe the result on
the retained `gwent/server/state` topic:

1. Start a fresh generated game (the New Game wizard deals one), or deal via the
   main-menu `random` choice:
   ```bash
   mosquitto_pub -h localhost -u geralt -P gwent -t gwent/menu/choose \
     -m '{"kind":"menu","menu_id":"main","id":"random"}'
   ```
2. Inject the card(s) under test as if scanned, by publishing to
   `gwent/cards/raw/read` (one message per card, full card JSON from
   `software/data/cards/{Faction}/<Card>.json`).
3. Read the resulting board from the retained snapshot and assert the expected
   outcome (scores, rows, weather, etc.):
   ```bash
   mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1 -W 4 \
     | python3 -c "import sys,json; b=json.load(sys.stdin)['state']['board']; print(b['scores'])"
   ```

If the behavior is wrong (up to 3 iterations):
1. Read the game log (`/tmp/logs/gwent.log`)
2. Fix the code
3. Reinstall + restart + re-drive

### 6. Close issue

Only after the live behavior matches the acceptance criteria:
```bash
gh issue close <N> --comment "Implemented and verified live over MQTT."
```
