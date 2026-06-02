# Schematic generator

`gen_schematic.py` rebuilds `../gwent-hat.kicad_sch` from scratch by reading the per-component placement table at the top of the script and embedding KiCad's standard symbol definitions.

## Usage

The script needs the KiCad standard symbol library files locally. Easiest way to get them:

```bash
# Clone the KiCad symbol library to a working dir
git clone --depth 1 --filter=blob:none --no-checkout \
    https://gitlab.com/kicad/libraries/kicad-symbols.git /tmp/kisym
cd /tmp/kisym
git checkout HEAD -- \
    Connector_Generic.kicad_symdir/Conn_02x20_Odd_Even.kicad_sym \
    Connector_Generic.kicad_symdir/Conn_01x08.kicad_sym \
    Connector_Generic.kicad_symdir/Conn_01x16.kicad_sym \
    Connector_Generic.kicad_symdir/Conn_01x04.kicad_sym \
    Device.kicad_symdir/RotaryEncoder_Switch.kicad_sym \
    Device.kicad_symdir/C.kicad_sym \
    Mechanical.kicad_symdir/MountingHole.kicad_sym \
    power.kicad_symdir/+3V3.kicad_sym \
    power.kicad_symdir/+5V.kicad_sym \
    power.kicad_symdir/GND.kicad_sym

# Re-run the generator (overwrites gwent-hat.kicad_sch)
python3 hardware/pcb/scripts/gen_schematic.py
```

If you have KiCad already installed locally, you can also point `LIB_DIR` at KiCad's standard library install path (e.g. `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/` on macOS) and skip the clone.

## When to re-run

- You changed a component's position (edit `COMPONENTS` in the script)
- You added or removed a component
- You bumped the KiCad file format version

If you've made manual edits to `gwent-hat.kicad_sch` in the GUI (wires, net labels, custom positions), re-running this script **will overwrite them**. Consider committing your manual edits before re-running, or inline the changes into `COMPONENTS` first.

## What this script does NOT do

- Draw wires between pins
- Place global net labels at pins
- Run ERC

Those are intentionally left for the KiCad GUI — wire placement requires pin-level coordinate math that's far easier to do interactively. See `../BUILD.md` for the wiring guide.
