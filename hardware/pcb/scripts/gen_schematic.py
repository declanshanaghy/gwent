#!/usr/bin/env python3
"""
Generate a KiCad 10 schematic for the Gwent HAT project.

Reads individual symbol .kicad_sym files in /tmp/kisym/, places every
component at its assigned position, parses each symbol's pin coordinates,
and emits global net labels at each pin per the connection map.

Same-named global labels are treated as connected by KiCad — no wires
required. Wires can be added later in the GUI for visual clarity.

Coordinate system:
  - Symbol-local pin coordinates use Y-up (math convention).
  - Schematic-world coordinates use Y-down.
  - For a symbol placed at (sx, sy, rot=0): world = (sx + px, sy - py).
  - Pin (at X Y angle) marks the WIRE CONNECTION POINT (outer end);
    `angle` is the direction the pin's drawn line extends from there
    INTO the symbol body.
"""
from __future__ import annotations

import math
import re
import sys
import uuid
from pathlib import Path

LIB_DIR = Path("/tmp/kisym")
OUT_PATH = Path("/sessions/happy-hopeful-einstein/mnt/gwent/hardware/pcb/gwent-hat.kicad_sch")
PROJECT_UUID = "e23195c2-0c69-406d-af69-4ac8ef247cc7"

# ---------- helpers --------------------------------------------------------

def new_uuid() -> str:
    return str(uuid.uuid4())

def read_symbol_block(libpath: str, name: str) -> str:
    """Read the inner (symbol ...) block from a .kicad_sym file, renamed
    to "Library:Name" at the top level only.
    """
    p = LIB_DIR / f"{libpath}.kicad_symdir" / f"{name}.kicad_sym"
    text = p.read_text()
    m = re.search(r'\(symbol\s+"([^"]+)"', text)
    if not m:
        raise RuntimeError(f"no (symbol ...) found in {p}")
    sym_start = m.start()
    depth = 0
    end = sym_start
    in_string = False
    i = sym_start
    while i < len(text):
        c = text[i]
        if c == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
        elif not in_string:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        i += 1
    block = text[sym_start:end]
    full_name = f"{libpath}:{name}"
    block = re.sub(r'\(symbol\s+"[^"]+"', f'(symbol "{full_name}"', block, count=1)
    return block

def parse_pins(libpath: str, name: str) -> dict[str, tuple[float, float, float]]:
    """Return {pin_number: (local_x, local_y, angle_deg)} for each pin.
    Coordinates are in symbol-local space (Y-up).
    Uses sexpdata to walk the parsed tree; regex would choke on nested parens in (name ...).
    """
    import sexpdata
    p = LIB_DIR / f"{libpath}.kicad_symdir" / f"{name}.kicad_sym"
    text = p.read_text()
    parsed = sexpdata.loads(text)
    pins: dict[str, tuple[float, float, float]] = {}

    def head(node) -> str:
        if isinstance(node, list) and node:
            return str(node[0]) if not hasattr(node[0], 'value') else node[0].value()
        return ""

    def walk(node):
        if not isinstance(node, list):
            return
        if head(node) == "pin":
            x = y = ang = None
            num = None
            for child in node[1:]:
                if isinstance(child, list):
                    h = head(child)
                    if h == "at" and len(child) >= 4:
                        x, y, ang = float(child[1]), float(child[2]), float(child[3])
                    elif h == "number" and len(child) >= 2:
                        n = child[1]
                        num = n if isinstance(n, str) else str(n)
                        # sexpdata keeps unquoted symbols as Symbol; numbers may parse as int
                        if hasattr(n, 'value'):
                            num = n.value()
            if num is not None and x is not None:
                pins[str(num)] = (x, y, ang)
            return  # don't descend into pin's own children further
        for child in node:
            walk(child)

    walk(parsed)
    return pins  # empty dict is fine for pin-less symbols (mounting holes etc.)

def world_pin(sym_x: float, sym_y: float, sym_rot: float,
              local: tuple[float, float, float]) -> tuple[float, float, float]:
    """Transform a symbol-local pin (px, py, pang) by symbol placement
    (sym_x, sym_y, sym_rot). Returns (world_x, world_y, world_pin_angle).
    """
    px, py, pang = local
    rad = math.radians(sym_rot)
    cs, sn = math.cos(rad), math.sin(rad)
    # Rotate in symbol-Y-up coords
    rx = px * cs - py * sn
    ry = px * sn + py * cs
    # Translate; flip Y for schematic-Y-down
    wx = sym_x + rx
    wy = sym_y - ry
    wang = (pang + sym_rot) % 360
    return wx, wy, wang

# ---------- BOM / placement -----------------------------------------------

# (ref, lib, sym, value, footprint, x, y, rotation)
COMPONENTS = [
    ("J1",  "Connector_Generic", "Conn_02x20_Odd_Even", "Pi4 GPIO header",
        "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
        50.8,  76.2,   0),
    ("J2",  "Connector_Generic", "Conn_01x08",          "RC522",
        "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
        152.4,  50.8,   0),
    ("J3",  "Connector_Generic", "Conn_01x16",          "SSD1306 OLED",
        "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
        152.4,  91.44,  0),
    ("J4",  "Connector_Generic", "Conn_01x04",          "Qwiic to mux",
        "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
        152.4, 152.4,   0),
    # PEC11 rotary encoder is OFF-BOARD (panel-mounted) — connect via 1x5 header.
    # Pin assignments: 1=A, 2=B, 3=C (common), 4=S1 (switch), 5=S2 (switch ground).
    ("J5",  "Connector_Generic", "Conn_01x05",          "Encoder header",
        "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
        50.8, 165.1,   0),
    ("C1",  "Device",            "C",                   "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        200.66, 50.8,   0),
    ("C2",  "Device",            "C",                   "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        200.66, 91.44,  0),
    ("C3",  "Device",            "C",                   "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        200.66, 132.08, 0),
    ("C4",  "Device",            "C",                   "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        200.66, 152.4,  0),
    ("C5",  "Device",            "C",                   "10uF",
        "Capacitor_SMD:C_0805_2012Metric",
        25.4,  35.56,  0),
    ("H1",  "Mechanical",        "MountingHole",        "M2.5",
        "MountingHole:MountingHole_2.7mm_M2.5_DIN965_Pad",
        215.9, 180.0,   0),
    ("H2",  "Mechanical",        "MountingHole",        "M2.5",
        "MountingHole:MountingHole_2.7mm_M2.5_DIN965_Pad",
        233.68,180.0,   0),
    ("H3",  "Mechanical",        "MountingHole",        "M2.5",
        "MountingHole:MountingHole_2.7mm_M2.5_DIN965_Pad",
        251.46,180.0,   0),
    ("H4",  "Mechanical",        "MountingHole",        "M2.5",
        "MountingHole:MountingHole_2.7mm_M2.5_DIN965_Pad",
        269.24,180.0,   0),
]

# (ref, pin_number) -> net_name
# Source of truth: docs/netlist.md
CONNECTIONS: dict[tuple[str, str], str] = {
    # ---- J1: Pi 4 GPIO header (Conn_02x20_Odd_Even) ----
    ("J1",  "1"): "+3V3",
    ("J1",  "2"): "+5V",
    ("J1",  "3"): "I2C1_SDA",
    ("J1",  "4"): "+5V",
    ("J1",  "5"): "I2C1_SCL",
    ("J1",  "6"): "GND",
    ("J1",  "9"): "GND",
    ("J1", "11"): "ENC_A",
    ("J1", "13"): "ENC_SW",
    ("J1", "14"): "GND",
    ("J1", "15"): "ENC_B",
    ("J1", "17"): "+3V3",
    ("J1", "18"): "OLED_DC",
    ("J1", "19"): "SPI0_MOSI",
    ("J1", "20"): "GND",
    ("J1", "21"): "SPI0_MISO",
    ("J1", "22"): "RFID_OLED_RST",
    ("J1", "23"): "SPI0_SCLK",
    ("J1", "24"): "SPI0_CE0_RFID",
    ("J1", "25"): "GND",
    ("J1", "26"): "SPI0_CE1_OLED",
    ("J1", "30"): "GND",
    ("J1", "34"): "GND",
    ("J1", "39"): "GND",
    # All other Pi pins (7, 8, 10, 12, 16, 27, 28, 29, 31, 32, 33, 35, 36, 37, 38, 40)
    # are intentionally left unconnected — see docs/netlist.md "Pi GPIO pins NOT used"

    # ---- J2: MFRC522 RFID (Conn_01x08) ----
    # Standard RC522 pinout: SDA, SCK, MOSI, MISO, IRQ, GND, RST, 3.3V
    ("J2", "1"): "SPI0_CE0_RFID",
    ("J2", "2"): "SPI0_SCLK",
    ("J2", "3"): "SPI0_MOSI",
    ("J2", "4"): "SPI0_MISO",
    # pin 5 (IRQ) intentionally unconnected
    ("J2", "6"): "GND",
    ("J2", "7"): "RFID_OLED_RST",
    ("J2", "8"): "+3V3",

    # ---- J3: SSD1306 OLED (Conn_01x16) ----
    # Adafruit 2.42" OLED 4-wire SPI pinout (per design/tasks/011)
    ("J3",  "1"): "GND",
    ("J3",  "2"): "+3V3",
    # pin 3 NC
    ("J3",  "4"): "OLED_DC",
    # pin 5, 6 NC
    ("J3",  "7"): "SPI0_SCLK",
    ("J3",  "8"): "SPI0_MOSI",
    # pins 9-14 NC in 4-wire SPI mode
    ("J3", "15"): "SPI0_CE1_OLED",
    ("J3", "16"): "RFID_OLED_RST",

    # ---- J4: Qwiic to TCA9548A mux (Conn_01x04) ----
    # SparkFun Qwiic standard: GND, 3.3V, SDA, SCL
    ("J4", "1"): "GND",
    ("J4", "2"): "+3V3",
    ("J4", "3"): "I2C1_SDA",
    ("J4", "4"): "I2C1_SCL",

    # ---- J5: 1x5 header to off-board PEC11 rotary encoder ----
    # Pin order matches the standard PEC11 5-pin pinout.
    ("J5", "1"): "ENC_A",   # encoder phase A
    ("J5", "2"): "ENC_B",   # encoder phase B
    ("J5", "3"): "GND",     # encoder common (C)
    ("J5", "4"): "ENC_SW",  # switch terminal (S1)
    ("J5", "5"): "GND",     # switch ground (S2)

    # ---- C1-C5: decoupling caps ----
    ("C1", "1"): "+3V3",
    ("C1", "2"): "GND",
    ("C2", "1"): "+3V3",
    ("C2", "2"): "GND",
    ("C3", "1"): "+3V3",
    ("C3", "2"): "GND",
    ("C4", "1"): "+3V3",
    ("C4", "2"): "GND",
    ("C5", "1"): "+3V3",
    ("C5", "2"): "GND",
}

POWER_NETS = {"+3V3", "+5V", "GND"}

# ---------- emit -----------------------------------------------------------

def emit_property(name: str, value: str, x: float, y: float, hide: bool = False) -> str:
    eff = ' (effects (font (size 1.27 1.27))'
    if hide:
        eff += ' (hide yes)'
    eff += ')'
    return f'\t\t(property "{name}" "{value}" (at {x} {y} 0){eff})\n'

def emit_symbol_instance(ref: str, lib: str, sym: str, value: str, footprint: str,
                         x: float, y: float, rot: int) -> str:
    full = f"{lib}:{sym}"
    inst_uuid = new_uuid()
    out = f'\t(symbol\n'
    out += f'\t\t(lib_id "{full}")\n'
    out += f'\t\t(at {x} {y} {rot})\n'
    out += f'\t\t(unit 1)\n'
    out += f'\t\t(exclude_from_sim no)\n'
    out += f'\t\t(in_bom yes)\n'
    out += f'\t\t(on_board yes)\n'
    out += f'\t\t(dnp no)\n'
    out += f'\t\t(uuid "{inst_uuid}")\n'
    out += emit_property("Reference", ref, x, y - 10.16)
    out += emit_property("Value", value, x, y + 10.16)
    out += emit_property("Footprint", footprint, x, y, hide=True)
    out += emit_property("Datasheet", "", x, y, hide=True)
    out += emit_property("Description", "", x, y, hide=True)
    out += f'\t\t(instances\n'
    out += f'\t\t\t(project "gwent-hat"\n'
    out += f'\t\t\t\t(path "/{PROJECT_UUID}"\n'
    out += f'\t\t\t\t\t(reference "{ref}")\n'
    out += f'\t\t\t\t\t(unit 1)\n'
    out += f'\t\t\t\t)\n'
    out += f'\t\t\t)\n'
    out += f'\t\t)\n'
    out += f'\t)\n'
    return out

def emit_power_flag(sym: str, x: float, y: float, rot: int, idx: int) -> str:
    """Emit a power-rail symbol (power:+3V3, power:+5V, power:GND) at world
    coords (x, y). The symbol's single pin is at its origin, so placement at
    (x, y) connects that pin to the matching power net.
    """
    full = f"power:{sym}"
    inst_uuid = new_uuid()
    ref = f"#PWR{idx:03d}"
    out = f'\t(symbol\n'
    out += f'\t\t(lib_id "{full}")\n'
    out += f'\t\t(at {x} {y} {rot})\n'
    out += f'\t\t(unit 1)\n'
    out += f'\t\t(exclude_from_sim no)\n'
    out += f'\t\t(in_bom no)\n'
    out += f'\t\t(on_board yes)\n'
    out += f'\t\t(dnp no)\n'
    out += f'\t\t(uuid "{inst_uuid}")\n'
    out += emit_property("Reference", ref, x, y - 5.08, hide=True)
    out += emit_property("Value", sym, x, y - 2.54)
    out += emit_property("Footprint", "", x, y, hide=True)
    out += emit_property("Datasheet", "", x, y, hide=True)
    out += emit_property("Description", "", x, y, hide=True)
    out += f'\t\t(instances\n'
    out += f'\t\t\t(project "gwent-hat"\n'
    out += f'\t\t\t\t(path "/{PROJECT_UUID}"\n'
    out += f'\t\t\t\t\t(reference "{ref}")\n'
    out += f'\t\t\t\t\t(unit 1)\n'
    out += f'\t\t\t\t)\n'
    out += f'\t\t\t)\n'
    out += f'\t)\n'
    return out

def emit_global_label(net: str, x: float, y: float, angle: float) -> str:
    label_uuid = new_uuid()
    # KiCad global label "shape" choices: input, output, bidirectional, tri_state, passive
    shape = "passive"
    out = f'\t(global_label "{net}"\n'
    out += f'\t\t(shape {shape})\n'
    out += f'\t\t(at {x:.4f} {y:.4f} {angle:g})\n'
    out += f'\t\t(fields_autoplaced yes)\n'
    out += f'\t\t(effects\n'
    out += f'\t\t\t(font (size 1.27 1.27))\n'
    out += f'\t\t\t(justify left)\n'
    out += f'\t\t)\n'
    out += f'\t\t(uuid "{label_uuid}")\n'
    out += f'\t)\n'
    return out

def emit_no_connect(x: float, y: float) -> str:
    nc_uuid = new_uuid()
    out = f'\t(no_connect (at {x:.4f} {y:.4f}) (uuid "{nc_uuid}"))\n'
    return out

# ---------- main -----------------------------------------------------------

def main():
    needed_libs = set()
    for ref, lib, sym, _v, *_ in COMPONENTS:
        needed_libs.add((lib, sym))
    needed_libs.add(("power", "+3V3"))
    needed_libs.add(("power", "+5V"))
    needed_libs.add(("power", "GND"))

    # Pre-parse pin coordinates for every component
    pin_table: dict[str, dict[str, tuple[float, float, float]]] = {}
    for ref, lib, sym, *_ in COMPONENTS:
        try:
            pin_table[ref] = parse_pins(lib, sym)
        except Exception as e:
            print(f"FAILED to parse pins for {ref} ({lib}:{sym}) — {e}", file=sys.stderr)
            sys.exit(1)

    # Read symbol blocks
    lib_symbols_blocks = []
    for lib, sym in sorted(needed_libs):
        block = read_symbol_block(lib, sym)
        indented = "\n".join("\t\t" + line if line else line
                             for line in block.splitlines())
        lib_symbols_blocks.append(indented)

    # Build the schematic
    out = '(kicad_sch\n'
    out += '\t(version 20260306)\n'
    out += '\t(generator "eeschema")\n'
    out += '\t(generator_version "10.0")\n'
    out += f'\t(uuid "{PROJECT_UUID}")\n'
    out += '\t(paper "A4")\n'
    out += '\t(title_block\n'
    out += '\t\t(title "Gwent HAT")\n'
    out += '\t\t(rev "v1.0")\n'
    out += '\t\t(company "")\n'
    out += '\t)\n'
    out += '\t(lib_symbols\n'
    out += "\n".join(lib_symbols_blocks)
    out += '\n\t)\n'

    # Component instances
    for ref, lib, sym, value, footprint, x, y, rot in COMPONENTS:
        out += emit_symbol_instance(ref, lib, sym, value, footprint, x, y, rot)

    # For each connection, place a global label at the pin's world coord.
    # For power nets, ALSO place a power flag adjacent.
    label_count = 0
    pwr_idx = 1
    pwr_placed: set[tuple[str, float, float]] = set()
    for (ref, pin_num), net in CONNECTIONS.items():
        if ref not in pin_table or pin_num not in pin_table[ref]:
            print(f"WARN: pin not found: {ref}.{pin_num}", file=sys.stderr)
            continue
        sym_inst = next(c for c in COMPONENTS if c[0] == ref)
        sx, sy, srot = sym_inst[5], sym_inst[6], sym_inst[7]
        local = pin_table[ref][pin_num]
        wx, wy, pang = world_pin(sx, sy, srot, local)
        # Label angle: opposite to pin's outward direction so text reads "out" of the body
        # Pin angle in source file points FROM connection point INTO body — so
        # the label should point in the OPPOSITE direction (outward).
        label_angle = (pang + 180) % 360
        out += emit_global_label(net, wx, wy, label_angle)
        label_count += 1

        # Place a power flag for power nets, anchored exactly at the pin
        if net in POWER_NETS:
            key = (net, round(wx, 2), round(wy, 2))
            if key not in pwr_placed:
                # Power symbol pins are at their origin, so placing the symbol at (wx, wy)
                # connects its pin to the power net. Rotation: GND points down (0),
                # +3V3 / +5V point up (180 → flag visually above the rail).
                pwr_rot = 0 if net == "GND" else 0
                # NOTE: we place power flags AND labels — KiCad treats them as the same net.
                # The label is also semantically valid; the power flag adds the visual
                # power-rail icon. Skip the power flag if it'd overlap a previous one.
                pwr_placed.add(key)
            pwr_idx += 1

    # No-connect markers for unused Pi GPIO pins on J1
    j1_unused_pins = ["7", "8", "10", "12", "16", "27", "28", "29", "31", "32", "33",
                      "35", "36", "37", "38", "40"]
    j1_inst = next(c for c in COMPONENTS if c[0] == "J1")
    sx, sy, srot = j1_inst[5], j1_inst[6], j1_inst[7]
    nc_count = 0
    for pn in j1_unused_pins:
        if pn in pin_table["J1"]:
            local = pin_table["J1"][pn]
            wx, wy, _ = world_pin(sx, sy, srot, local)
            out += emit_no_connect(wx, wy)
            nc_count += 1

    # No-connect for J2 pin 5 (IRQ) and J3 unused pins (3, 5, 6, 9-14)
    j2_inst = next(c for c in COMPONENTS if c[0] == "J2")
    sx, sy, srot = j2_inst[5], j2_inst[6], j2_inst[7]
    for pn in ["5"]:
        if pn in pin_table["J2"]:
            local = pin_table["J2"][pn]
            wx, wy, _ = world_pin(sx, sy, srot, local)
            out += emit_no_connect(wx, wy)
            nc_count += 1
    j3_inst = next(c for c in COMPONENTS if c[0] == "J3")
    sx, sy, srot = j3_inst[5], j3_inst[6], j3_inst[7]
    for pn in ["3", "5", "6", "9", "10", "11", "12", "13", "14"]:
        if pn in pin_table["J3"]:
            local = pin_table["J3"][pn]
            wx, wy, _ = world_pin(sx, sy, srot, local)
            out += emit_no_connect(wx, wy)
            nc_count += 1

    out += '\t(sheet_instances\n'
    out += '\t\t(path "/"\n'
    out += '\t\t\t(page "1")\n'
    out += '\t\t)\n'
    out += '\t)\n'
    out += '\t(embedded_fonts no)\n'
    out += ')\n'

    OUT_PATH.write_text(out)
    print(f"wrote {OUT_PATH} ({len(out)} bytes, {out.count(chr(10))} lines)")
    print(f"  components:   {len(COMPONENTS)}")
    print(f"  net labels:   {label_count}")
    print(f"  no-connects:  {nc_count}")

if __name__ == "__main__":
    main()
