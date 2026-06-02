#!/usr/bin/env python3
"""
Reposition footprints in gwent-hat.kicad_pcb and add the Pi HAT board outline.

Reads the .kicad_pcb that KiCad created via "Update PCB from Schematic" (which
places all footprints at default origin coordinates), and:

  1. Repositions each footprint by reference designator according to the LAYOUT table.
  2. Adds the Pi HAT mechanical board outline on Edge.Cuts:
       - 65 × 56.5 mm rectangle, board top-left at WORLD_ORIGIN
       - 4 corner fillets (3 mm radius)
  3. Replaces any existing graphic items on Edge.Cuts (so re-running is idempotent).

Run after every "Update PCB from Schematic" if you want to re-snap to the canonical layout.
"""
from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

PCB_PATH = Path("/sessions/happy-hopeful-einstein/mnt/gwent/hardware/pcb/gwent-hat.kicad_pcb")

# Board top-left corner in KiCad world coordinates.
# Choose 100,100 so the board sits comfortably on the default A4 sheet.
WORLD_X = 100.0
WORLD_Y = 100.0
BOARD_W = 65.0
BOARD_H = 56.5
CORNER_R = 3.0   # 3 mm corner fillet (Pi HAT mechanical spec)

# Mounting hole positions relative to board top-left
MOUNT_OFFSETS = [
    (3.5, 3.5),   # top-left      → H1
    (61.5, 3.5),  # top-right     → H2
    (3.5, 53.0),  # bottom-left   → H3
    (61.5, 53.0), # bottom-right  → H4
]

# Footprint placements: ref → (x_offset, y_offset, rotation°)
# Offsets are relative to board top-left (WORLD_X, WORLD_Y).
# All angles are CCW positive degrees per KiCad convention.
LAYOUT = {
    # Mounting holes — match Pi HAT spec corner positions
    "H1": (3.5,  3.5,  0),
    "H2": (61.5, 3.5,  0),
    "H3": (3.5,  53.0, 0),
    "H4": (61.5, 53.0, 0),

    # GPIO header — vertical orientation along the left side of the board.
    # Footprint pin 1 is at footprint origin; with angle 0, pins extend in +Y.
    # Centered in the 50mm gap between the two left mounting holes (3.5 → 53.0).
    "J1": (8.5, 4.62, 0),

    # RC522 — 1x8 header, top-center, vertical
    "J2": (24.0, 8.0, 0),

    # OLED — 1x16 header, top-right, vertical (longest peripheral on the board)
    "J3": (45.0, 9.0, 0),

    # Qwiic to mux — JST-SH 4-pin horizontal SMD, bottom-left area
    "J4": (15.0, 49.0, 0),

    # Encoder header — 1x5, vertical, bottom-center.
    # Pinout 1..5 = A, B, C, S1, S2. Wire to off-board PEC11.
    "J5": (35.0, 38.0, 0),

    # Decoupling caps — small 0805, scatter near consumers
    "C1": (35.0, 8.0,  0),    # near RC522
    "C2": (52.0, 13.0, 0),    # near OLED
    "C3": (10.0, 49.0, 0),    # near Qwiic
    "C4": (45.0, 49.0, 0),    # near GPIO bottom region
    "C5": (15.0, 14.0, 0),    # near GPIO 3V3/GND pins
}

# ---------- IO helpers -----------------------------------------------------

def new_uuid() -> str:
    return str(uuid.uuid4())

def read_pcb() -> str:
    return PCB_PATH.read_text()

def write_pcb(text: str) -> None:
    PCB_PATH.write_text(text)

# ---------- footprint repositioning ---------------------------------------

def find_footprint_blocks(text: str):
    """Yield (start_index, end_index, footprint_block) for each (footprint ...) block."""
    i = 0
    while True:
        m = re.search(r'\(footprint\s+"', text[i:])
        if not m:
            return
        start = i + m.start()
        # Find matching close paren
        depth = 0
        in_string = False
        j = start
        while j < len(text):
            c = text[j]
            if c == '"' and (j == 0 or text[j-1] != '\\'):
                in_string = not in_string
            elif not in_string:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        yield start, j + 1, text[start:j+1]
                        i = j + 1
                        break
            j += 1
        else:
            return

def get_reference(block: str) -> str | None:
    m = re.search(r'\(property "Reference"\s+"([^"]+)"', block)
    return m.group(1) if m else None

def replace_at(block: str, new_x: float, new_y: float, new_rot: float) -> str:
    """Replace the footprint's top-level (at X Y [rot]) with the new values."""
    # The first (at X Y [rot]) after (footprint "...") is the placement.
    # Property `at`s come later inside (property ...) and (pad ...) — those we leave alone.
    pattern = re.compile(
        r'(\(footprint\s+"[^"]+"[^()]*?(?:\([^)]*\)[^()]*?)*?\(at\s+)([\d.-]+)(\s+)([\d.-]+)((?:\s+[\d.-]+)?)(\s*\))',
        re.DOTALL,
    )
    # Simpler: just find the FIRST (at ...) after the footprint name and replace it.
    m = re.search(r'\(footprint\s+"[^"]+"', block)
    if not m:
        return block
    after = m.end()
    at_match = re.search(r'\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\s*\)', block[after:])
    if not at_match:
        return block
    abs_start = after + at_match.start()
    abs_end = after + at_match.end()
    new_at = f'(at {new_x} {new_y} {new_rot})'
    return block[:abs_start] + new_at + block[abs_end:]

# ---------- board outline -------------------------------------------------

def emit_edge_cuts() -> str:
    """Emit gr_line + gr_arc shapes describing a 65×56.5 mm rounded rectangle
    at WORLD_X, WORLD_Y on the Edge.Cuts layer."""
    x0 = WORLD_X
    y0 = WORLD_Y
    x1 = WORLD_X + BOARD_W
    y1 = WORLD_Y + BOARD_H
    r = CORNER_R
    out = []

    # Four straight edges (between corner arcs)
    edges = [
        # top edge: (x0+r, y0) → (x1-r, y0)
        (x0 + r, y0, x1 - r, y0),
        # right edge: (x1, y0+r) → (x1, y1-r)
        (x1, y0 + r, x1, y1 - r),
        # bottom edge: (x1-r, y1) → (x0+r, y1)
        (x1 - r, y1, x0 + r, y1),
        # left edge: (x0, y1-r) → (x0, y0+r)
        (x0, y1 - r, x0, y0 + r),
    ]
    for sx, sy, ex, ey in edges:
        out.append(
            f'\t(gr_line\n'
            f'\t\t(start {sx} {sy})\n'
            f'\t\t(end {ex} {ey})\n'
            f'\t\t(stroke (width 0.1) (type solid))\n'
            f'\t\t(layer "Edge.Cuts")\n'
            f'\t\t(uuid "{new_uuid()}")\n'
            f'\t)\n'
        )

    # Four corner arcs — each quarter circle with start/mid/end
    # KiCad arcs go counter-clockwise from start through mid to end
    arcs = [
        # top-left: from (x0, y0+r) curving up to (x0+r, y0), centered at (x0+r, y0+r)
        ((x0,     y0 + r),  (x0 + r - r * 0.7071, y0 + r - r * 0.7071), (x0 + r, y0)),
        # top-right: from (x1-r, y0) → (x1, y0+r), centered at (x1-r, y0+r)
        ((x1 - r, y0),      (x1 - r + r * 0.7071, y0 + r - r * 0.7071), (x1,     y0 + r)),
        # bottom-right: from (x1, y1-r) → (x1-r, y1), centered at (x1-r, y1-r)
        ((x1,     y1 - r),  (x1 - r + r * 0.7071, y1 - r + r * 0.7071), (x1 - r, y1)),
        # bottom-left: from (x0+r, y1) → (x0, y1-r), centered at (x0+r, y1-r)
        ((x0 + r, y1),      (x0 + r - r * 0.7071, y1 - r + r * 0.7071), (x0,     y1 - r)),
    ]
    for (sx, sy), (mx, my), (ex, ey) in arcs:
        out.append(
            f'\t(gr_arc\n'
            f'\t\t(start {sx:.4f} {sy:.4f})\n'
            f'\t\t(mid {mx:.4f} {my:.4f})\n'
            f'\t\t(end {ex:.4f} {ey:.4f})\n'
            f'\t\t(stroke (width 0.1) (type solid))\n'
            f'\t\t(layer "Edge.Cuts")\n'
            f'\t\t(uuid "{new_uuid()}")\n'
            f'\t)\n'
        )
    return "".join(out)

# ---------- main -----------------------------------------------------------

def main():
    text = read_pcb()
    original_len = len(text)

    # 1. Strip any pre-existing Edge.Cuts graphic items so re-running is idempotent.
    #    Match (gr_line ...) (gr_arc ...) (gr_circle ...) where (layer "Edge.Cuts") appears.
    def strip_edge_cuts(s: str) -> str:
        result = []
        i = 0
        while i < len(s):
            m = re.search(r'\((gr_line|gr_arc|gr_circle|gr_rect|gr_poly)\b', s[i:])
            if not m:
                result.append(s[i:])
                break
            result.append(s[i : i + m.start()])
            block_start = i + m.start()
            # find matching close paren
            depth = 0
            in_string = False
            j = block_start
            while j < len(s):
                c = s[j]
                if c == '"' and (j == 0 or s[j-1] != '\\'):
                    in_string = not in_string
                elif not in_string:
                    if c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                        if depth == 0:
                            block_end = j + 1
                            break
                j += 1
            else:
                # unterminated — bail
                result.append(s[block_start:])
                break
            block = s[block_start:block_end]
            if '(layer "Edge.Cuts")' in block:
                # Skip this block; also skip preceding tab/newline
                tail = result[-1].rstrip("\t")
                result[-1] = tail.rstrip("\n")
                if not result[-1]:
                    result.pop()
                # add a single newline for cleanliness
                if not (result and result[-1].endswith("\n")):
                    pass
            else:
                result.append(block)
            i = block_end
        return "".join(result)

    text = strip_edge_cuts(text)
    after_strip_len = len(text)

    # 2. Reposition each footprint
    blocks = list(find_footprint_blocks(text))
    repositioned = 0
    new_pieces = []
    last_end = 0
    for start, end, block in blocks:
        ref = get_reference(block)
        if ref and ref in LAYOUT:
            dx, dy, drot = LAYOUT[ref]
            new_block = replace_at(block, WORLD_X + dx, WORLD_Y + dy, drot)
            new_pieces.append(text[last_end:start])
            new_pieces.append(new_block)
            last_end = end
            repositioned += 1
        else:
            # leave as-is (or report)
            if ref:
                print(f"WARN: no LAYOUT entry for {ref}", file=sys.stderr)
    new_pieces.append(text[last_end:])
    text = "".join(new_pieces)

    # 3. Insert Edge.Cuts shapes just before the closing ')' of the kicad_pcb.
    edge_cuts = emit_edge_cuts()
    # Insert before the final closing paren on its own
    if text.rstrip().endswith(')'):
        # find last close paren
        idx = text.rfind(')')
        text = text[:idx] + edge_cuts + text[idx:]
    else:
        text += edge_cuts

    write_pcb(text)
    print(f"wrote {PCB_PATH}")
    print(f"  size: {original_len} → {len(text)} bytes")
    print(f"  footprints repositioned: {repositioned} / {len(blocks)}")
    print(f"  Edge.Cuts: 4 lines + 4 arcs (rounded rectangle 65×56.5 mm)")

if __name__ == "__main__":
    main()
