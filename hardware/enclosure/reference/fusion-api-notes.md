# Fusion (Autodesk MCP) — parametric modeling notes

Verified working notes for building the enclosure through the **official Autodesk Fusion
MCP** (`http://localhost:27182/mcp`). Captured 2026-06-01 from the live Fusion API docs
(`fusion_mcp_read` `apiDocumentation`) and Autodesk/3rd-party sources. This is the build
methodology of record.

## The MCP surface (3 tools)

- `fusion_mcp_execute` — `featureType:"script"` runs a Fusion Python API script; the
  script must define `def run(_context)`. **All geometry is built this way.**
  `featureType:"document"` does open/save/close.
- `fusion_mcp_read` — `apiDocumentation` (search classes/members), `screenshot` (PNG from
  any camera `direction`: front/top/iso-*/…), `document`, `projects`.
- `fusion_mcp_update` — `undo` / `redo`.

> Note: these `mcp__fusion__*` tools register in a Claude session only if the server was
> up at session start. If they're missing, drive the same JSON-RPC over `curl` (helper
> pattern saved during planning) or reload the session.

## MANDATORY methodology — parametric sketches, never hardcoded

Two ways to make solids exist; **we use feature-based parametric only**:

- ✅ `rootComp.sketches.add(plane)` → draw curves → add **geometric constraints**
  (`geometricConstraints.addHorizontal/addPerpendicular/addCoincident/addSymmetry`) → add
  **driving** dimensions `sketch.sketchDimensions.addDistanceDimension(p1, p2, orientation,
  textPoint, isDriving=True)`. Each returned `SketchDimension.parameter` is a
  `ModelParameter` — set `.expression = "<param name or formula>"`. Extrude with
  `extrudeFeatures` using `ValueInput.createByString("<param>")` for distances.
  - API confirms: `isDriving=True` → *"the dimension controls the geometry."*
- ❌ Do **not** use `TemporaryBRepManager.createBox()`/direct bodies, and **no hardcoded
  numeric literals** as final dimensions. Numbers live only inside `UserParameters.add(...)`.
  A model with zero user parameters or zero sketches is a failed build.

### User parameters

`design.userParameters.add(name, ValueInput.createByString(expr), units, comment)`.
- `ValueInput.createByString("0.8 mm")` keeps units explicit. The Fusion API **internal
  length unit is centimeters** — if you ever pass a bare real it's interpreted as cm. So
  **always pass explicit-unit strings**, never bare reals, to avoid the 10× trap.
- Build the full parameter table (print rules + every module dim + clearances) *before*
  any geometry.

## Spatial gotchas (3rd-party rules, verified against official docs)

- **cm internal units** — above; pass `"… mm"` strings.
- **Z-negation on XZ / YZ planes** — sketching on a non-XY base plane flips an axis vs.
  intuition. The console has a **65° tilted screen face** and front/rear walls on
  non-XY planes, so: after the first sketch on each new plane/face, take a
  `fusion_mcp_read screenshot` and verify orientation before extruding further.
- **Pre/post verification** — screenshot (iso + relevant ortho) after every feature; catch
  mistakes immediately rather than at the end.

## Sourcing / scrutiny

- **Official:** Autodesk Fusion MCP (Claude for Creative Work, Fusion subscribers) —
  aps.autodesk.com/blog/bringing-fusion-claude-creative-work. API reference:
  autodeskfusion360.github.io and help.autodesk.com Fusion-360-API (also live via
  `apiDocumentation`).
- **Third-party "skill" repos** (e.g. github.com/rahayesj/ClaudeFusion360MCP, MIT) are
  custom servers we do **not** run; we only borrowed the cm-units / Z-negation rules and
  verified them against the official API. Don't execute their server code.

## Build order (parametric, screenshot-verified) — for Phase 1

1. New doc → full User Parameters table.
2. Per part as its own Component, one `execute` script each, screenshot after each:
   display cradle + 65° tilt → Pi + HAT placeholder + DSI/port cutouts → control/display
   group (per chosen concept) → RFID pad → encoder boss → power-brick bay + vents + cord
   grommet → amp/isolator/speaker pockets + grilles → styling (chamfers + medallion) →
   split lips + M3 bosses → knob/diffuser.
3. Validate (visual + interference). Export `.f3d` / `.step` / per-part `.stl`/`.3mf`.
