# Kaer Morhen — Fusion 360 CAD (parametric build automation)

The enclosure is modeled in **Autodesk Fusion** (doc `Kaer-Morhen v2`) driven through the
**official Autodesk Fusion MCP** (`http://localhost:27182/mcp`). This folder captures the
**reproducible parametric build** of the initial massing so it can be regenerated or audited.

## Parameters

`../parameters.csv` — the 56 User Parameters (Fusion import format
`Name,Unit,Expression,Value,Comments,Favorite`). Import via Fusion → **Modify → Change
Parameters → Import**, or apply them via `build/01_user_parameters.py`.

## Driver

`fusion_mcp_driver.py` — a stdlib-only HTTP driver for the Fusion MCP:

```bash
python3 fusion_mcp_driver.py exec <script.py>        # run a Fusion API script (def run(_context))
python3 fusion_mcp_driver.py screenshot <dir> <out>  # capture a view (front/right/iso-top-right/…)
python3 fusion_mcp_driver.py read '<json-args>'      # arbitrary fusion_mcp_read call
```

(The `mcp__fusion__*` tools weren't registered in-session, so this drives the same JSON-RPC
over curl/HTTP. Each Fusion script prints its result to stdout, which the driver surfaces.)

## Build scripts (run in order on an empty design)

| Step | Script | Builds |
|---|---|---|
| 01 | `build/01_user_parameters.py` | Upserts all 56 User Parameters (idempotent) |
| 03 | `build/03_towers_and_shelf.py` | `tower_left`, `tower_right` (detachable), `front_shelf` |
| 04 | `build/04_screen_65deg.py` | `screen` on a `screen_tilt` (65°) construction plane |
| 05 | `build/05_central_wedge_backplane.py` | `central_body` — the wedge: 65° screen face + backplane sloping to the back-top, maximizing internal volume |
| 99 | `build/99_save.py` | Saves the document |

> Step 02 (a plain `central_base` box) was **superseded** by step 05's wedge and is omitted;
> step 05 deletes any `central_base` and builds the `central_body` wedge in its place.

## Methodology

Fully parametric: every dimension is a **driving sketch dimension or extrude bound to a named
User Parameter expression** — no hardcoded literals, no temp-BRep boxes. See
`../../reference/fusion-api-notes.md`. Note the YZ-plane sketch axis mapping
(`world_y = sketch_Y`, `world_z = -sketch_X`) handled in step 05.

## Status

Primary massing complete: `central_body` (wedge) + `tower_left/right` + `screen` +
`front_shelf`. Remaining (in Fusion): screen pocket/bezel, gems crest, shelf ramp, speaker
bores + score windows, internal bays, port/cord cutouts, vents, shell walls, tower plug
joints, exports.
