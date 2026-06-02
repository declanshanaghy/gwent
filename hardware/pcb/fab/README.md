# Fabrication outputs

Generated artifacts for fab houses live here. Only finalized, versioned `.zip` files are committed; intermediate Gerber/drill files are gitignored.

Naming convention: `gwent-hat-vN.M-{fab}.zip`, e.g. `gwent-hat-v1.0-jlcpcb.zip`.

JLCPCB submission expects a flat zip containing:

- `*.gtl` `*.gbl` — copper, top/bottom
- `*.gts` `*.gbs` — soldermask, top/bottom
- `*.gto` `*.gbo` — silkscreen, top/bottom
- `*.gko` (or `*.gm1`) — board outline
- `*.drl` — Excellon drill (plated)
- `*.drl` — Excellon drill (non-plated)
- `*.csv` — pick-and-place (CPL) — one for top, one for bottom
- `*.csv` — BOM — references, values, footprints, LCSC part numbers

All of these are produced by `kicad-cli` invoked from `hardware/pcb/scripts/build-fab.sh` (TBD).
