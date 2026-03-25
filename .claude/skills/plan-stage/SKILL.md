---
name: plan-stage
description: Plan or evaluate a game stage implementation from the GwentGameStages.md state diagram. Pass a screenshot path with green-boxed nodes as the argument. Use --evaluate to compare existing code against the diagram.
allowed-tools: Read, Glob, Grep, Bash, Agent, Write, Edit, TaskCreate, TaskUpdate
---

# Plan Stage Skill

You are helping implement game stages for the Gwent Companion project. The user will provide a screenshot of the state diagram from `design/GwentGameStages.md` with a **green box/highlight** drawn around the specific nodes and logic they want implemented as a game stage.

## Parsing Arguments

The argument string may contain:
- A file path to a screenshot (e.g., `/tmp/screenshot.png`, `~/Desktop/stage.png`)
- The `--evaluate` flag (can appear before or after the path)

If `--evaluate` is present, run in **evaluate mode**. Otherwise run in **plan mode** (default).

## Step 1: Read the Screenshot

Use the Read tool to view the screenshot file provided as the argument. Look for nodes/boxes enclosed in or highlighted by a **green rectangle or border**. These are the nodes the user wants implemented in this stage.

## Step 2: Read the Mermaid Source

Read `design/GwentGameStages.md` to get the full mermaid flowchart source. Map the visually highlighted nodes from the screenshot to their mermaid node IDs, labels, edge connections, and class types (hardware, software, data, process, decision, etc.).

List the identified nodes in a summary like:
```
## Identified Nodes
- `DealCards` [software] — "Deal Cards"
- `ScanCardDeal` [hardware] — "Scan Card"
- `WhichPlayerDeal` [decision] — "Which Player"
- `AddPlr1Hand` [data] — "Add to Plr1 Hand"
- `AddPlr2Hand` [data] — "Add to Plr2 Hand"
- `FinishedDeal` [decision] — "Finished?"
```

Also list the edges (connections) between these nodes and any edges leading in/out of this stage boundary.

## Step 3: Read Reference Implementations

Read ALL of the following files to understand the existing patterns:

- `software/gwent/gwent/game/stages/base.py` — GameStage base class
- `software/gwent/gwent/game/stages/register_leaders.py` — reference stage implementation
- `software/gwent/gwent/game/stages/register_decks.py` — reference stage implementation
- `software/gwent/gwent/game/stages/all.py` — stage exports
- `software/gwent/gwent/game/controller.py` — stage wiring and flow
- `software/gwent/gwent/messaging/ctrl.py` — stage constants
- `software/gwent/gwent/game/constants.py` — PLAYER enum
- `software/gwent/gwent/game/__init__.py` — PubSubComponent, channels, publish helpers

## Step 4: Check for Existing Implementation

Search for any existing implementation of the identified stage:
- Glob for `software/gwent/gwent/game/stages/*.py`
- Grep for the stage name in `controller.py` and `ctrl.py`

## Step 5A: Plan Mode (default)

If `--evaluate` is NOT present, produce an implementation plan:

### Output Format

```
## Stage: <StageName>

### Summary
<1-2 sentence description of what this stage does in the game flow>

### Node-to-Method Mapping
| Mermaid Node | Type | Maps To |
|---|---|---|
| `NodeId` | decision | `process_card()` conditional |
| `NodeId` | data | `_add_to_hand()` helper |
| ... | ... | ... |

### State Variables
- `_variable`: type — description

### Activate Contract
- **Receives**: description of args from previous stage
- **Complete returns**: description of args passed to next stage

### Files to Create/Modify
1. `software/gwent/gwent/game/stages/<stage_name>.py` — new stage class
2. `software/gwent/gwent/game/stages/<next_stage_name>.py` — **placeholder** for the next stage in the flow (accepts args from complete, shows "not yet implemented" prompt, OK returns to menu)
3. `software/gwent/gwent/game/stages/all.py` — add exports for both stages
4. `software/gwent/gwent/messaging/ctrl.py` — add STAGE_<NAME> constants for both stages
5. `software/gwent/gwent/messaging/ctrl_schema.json` — add both stage names to the enum
6. `software/gwent/gwent/game/controller.py` — add start_<stage>() and start_<next_stage>() methods, wire into flow

**IMPORTANT:** Always create a placeholder for the next stage in the diagram flow. This ensures the controller's complete callback has somewhere to go. The placeholder should:
- Accept the args that the current stage passes via `complete()`
- Show a prompt like "<StageName> — not yet implemented. Press OK to return to menu."
- OK → complete (returns to main menu)
- Cancel → cancel (returns to main menu)
- Reject card scans with an error

### Implementation Details
<detailed description of each method, validation logic, error handling>

### Error Handling
<what validations and error cases to handle, following patterns from register_decks.py>

### Controller Integration
<how start_<stage>() wires in: what calls it, what its complete/cancel callbacks do>
```

Then create tasks using TaskCreate for each implementation step:
- One task per file to create/modify
- Include the file path and a brief description of what to do
- Order them logically (stage class first, then exports, then controller wiring)

## Step 5B: Evaluate Mode (--evaluate)

If `--evaluate` IS present, compare the diagram against existing code:

### Output Format

```
## Evaluation: <StageName>

### Implementation Status
- [ ] Stage class file exists
- [x] Stage constant in ctrl.py
- [ ] Export in all.py
- ...

### What's Implemented
<bullet list of what exists and works>

### What's Missing
<bullet list of gaps between diagram and code>

### Recommended Steps
<ordered list of what to implement next>
```

Then create tasks using TaskCreate for each missing piece, ordered by implementation priority.

## Important Notes

- Always follow the patterns established in `register_leaders.py` and `register_decks.py`
- Use `self.publish_prompt()` for OLED display, `self.publish_error()` for errors
- Use `self.publish_effect()` for sound effects
- Card identification is by RFID (`card.rfid`)
- Faction matching determines which player a card belongs to
- The PLAYER enum is in `gwent.game.constants`
- MQTT channel helpers are in `gwent.game.__init__`
- Always validate: duplicates, wrong card types, wrong factions, blank cards
