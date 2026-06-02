# Gwent HAT — schematic and PCB build guide

Step-by-step recipe to take this from an empty KiCad project to ordered Gerbers. Plan to spend 3–5 hours total, mostly on PCB placement and routing.

> Single source of truth for nets and pin assignments: [`docs/netlist.md`](docs/netlist.md). Component values and part numbers: [`BOM.md`](BOM.md). Hardware spec being implemented: [`../../design/tasks/011-hardware-specification.md`](../../design/tasks/011-hardware-specification.md).

---

## 1. Open the project

```bash
cd hardware/pcb
open gwent-hat.kicad_pro          # macOS
```

KiCad opens the project pane. Double-click **Schematic Editor** — KiCad will create `gwent-hat.kicad_sch` if it doesn't exist yet.

## 2. Configure the schematic page

- File → Page Settings: **A4** landscape, title **"Gwent HAT"**, revision **v1.0**, date **today**.
- Add the project info block in the title area; KiCad fills it from the project metadata.

## 3. Place the symbols

In schematic editor, press **A** to open Add Symbol. Place each of the following at sensible positions on the sheet (left-to-right pictured here corresponds to "Pi side → peripherals side"):

| Ref | Symbol | Library | Where on sheet |
|---|---|---|---|
| J1 | `Conn_02x20_Odd_Even` | Connector_Generic | Far left — this is the Pi GPIO header |
| J2 | `Conn_01x08_Pin` | Connector | Top-right — RC522 |
| J3 | `Conn_01x16_Pin` | Connector | Middle-right — OLED |
| J4 | `JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` | Connector_JST | Right-center — Qwiic to mux |
| J5, J6, J7 | (same as J4) | (same) | Bottom-right — Qwiic to 3 matrices |
| SW1 | `RotaryEncoder_Switch` | Switch | Bottom-left |
| C1–C8 | `C` | Device | Sprinkle near each connector that needs decoupling |
| H1–H4 | `MountingHole` | Mechanical | Off to the side; placement happens on the PCB |

Set values per `BOM.md` (capacitor values, encoder part number, etc.).

## 4. Wire the nets

Use the **W** key for wire mode. Reference `docs/netlist.md` for every connection. The high-level structure:

**Power.** Place `+3V3`, `+5V`, and `GND` power flags (Add Power Symbol, **P** key). Wire them to the Pi GPIO header pins per the netlist. Wire `+3V3` and `GND` to every breakout connector. Drop a 100 nF cap between `+3V3` and `GND` near each breakout connector.

**SPI0 to RC522 + OLED.** Daisy SCLK/MOSI/MISO from J1 to J2 (RC522) and J3 (OLED). RC522 takes `SPI0_CE0_RFID` (J1 pin 24, GPIO8); OLED takes `SPI0_CE1_OLED` (J1 pin 26, GPIO7). Both reset pins go to the same `RFID_OLED_RST` net (J1 pin 22, GPIO25). OLED also needs `OLED_DC` from J1 pin 18 (GPIO24).

**I²C1 to mux.** SDA (J1 pin 3, GPIO2) and SCL (J1 pin 5, GPIO3) go to J4 (Qwiic to mux). The mux has its own pull-ups; no external pull-ups needed.

**Mux fanout.** J5/J6/J7 connect to the same +3V3 / GND, but their SDA/SCL come from the *downstream* side of the TCA9548A mux. Since the mux IS NOT on this PCB (it's an external breakout via J4), the downstream-side I²C nets *are not on this schematic at all*. J5/J6/J7 only carry power to the matrices through their Qwiic cables; the data is daisy-chained from the mux's own Qwiic outputs to each matrix. **You may end up not needing J5/J6/J7 at all** if the matrices are wired directly off the SparkFun mux's outputs and the HAT only provides the mux's input Qwiic. Decision point — see "Topology decision" below.

**Rotary encoder.** SW1 pin A → J1 pin 11 (GPIO17), pin B → J1 pin 15 (GPIO22), pin SW → J1 pin 13 (GPIO27). Common (C) and switch ground both go to GND.

**Unused Pi pins.** Place "no-connect" flags (Add No-Connect Flag, **Q** key) on every Pi header pin you don't use, per the table in `docs/netlist.md`.

### Topology decision: 3 vs 1 Qwiic connectors

The TCA9548A breakout has its own Qwiic outputs. Two valid topologies:

1. **HAT only provides J4 (input to mux).** The 3 matrices daisy-chain off the mux's own Qwiic outputs via Qwiic cables. Simplest HAT, looks cleanest, recommended for v1. **In this case, drop J5/J6/J7 from the schematic.**
2. **HAT provides J4 + J5/J6/J7.** The mux's downstream I²C is brought back to the HAT via cables, then routed back out. More wires, but lets you label the matrices on silkscreen and gives strain relief if the matrices are panel-mounted. Heavier.

Pick option 1 unless you have a specific reason for option 2. The schematic + netlist are written assuming option 1; if you go with option 2, you need to add 3 nets per matrix (downstream SDA/SCL pairs) which means the mux IC would have to be on this HAT — defeating the carrier-PCB simplicity.

## 5. Run ERC

Inspect → Electrical Rules Checker. Fix everything. Common issues:
- "Pin not connected" on Pi GPIO header pins you don't use → add NoConnect flags (**Q**).
- "Power input pin not driven" → make sure `+3V3` and `+5V` flags are present and wired to actual pins.
- "Conflicting names" on shared nets — fine, don't worry about names like `+3V3` showing up many places.

ERC clean = ready to lay out the PCB.

## 6. Assign footprints

Tools → Assign Footprints. For each schematic symbol, pick the footprint listed in `BOM.md`. KiCad's footprint chooser has a search box; the libraries are all built-in (Connector_Generic, Connector_PinHeader_2.54mm, Connector_JST, RotaryEncoder_Switch, Capacitor_SMD, MountingHole).

## 7. Update PCB from schematic

Tools → Update PCB from Schematic (**F8**). Footprints appear as a stack — drag them onto the canvas.

## 8. Draw the board outline (Pi HAT spec)

Switch to the `Edge.Cuts` layer. Draw a rectangle 65 mm wide × 56.5 mm tall. Add 4 mounting holes (M2.5, 2.7 mm drill diameter, plated) at:

```
(3.5, 3.5)    (61.5, 3.5)
(3.5, 53)     (61.5, 53)
```

(coordinates from the bottom-left corner of the board, in mm — this matches Pi 4 mounting holes when the GPIO header is at the right edge).

Round the four outer corners with a 3 mm fillet (Edit → Special Tools → Fillet Edges → 3 mm).

The detailed mechanical drawing is in `libs/pi-hat/hat-board-mechanical.pdf` if you cloned that submodule (optional). Otherwise the Pi HAT mechanical spec is at https://github.com/raspberrypi/hats.

## 9. Place the GPIO header

J1 (the 2×40 GPIO header) goes at the **right edge** of the board, with pin 1 in the bottom-right. The header should sit so that when the HAT is placed on top of a Pi 4, pin 1 of the header aligns with pin 1 of the Pi's GPIO header.

Position J1 such that its pin 1 center is at (`board_width - 3.5 mm`, `3.5 mm + 14 × 2.54 mm/2 = 3.5 + 17.78`) = (61.5, 21.28) mm — but verify against the Pi HAT mechanical PDF before committing.

## 10. Place everything else

Rough placement guidance:

- **J2 (RC522)** — top-left, with pin 1 close to where Pi GPIO pin 24 lands so the SPI traces stay short
- **J3 (OLED)** — top-center, similar logic for SPI0
- **J4 (Qwiic to mux)** — left side, centered vertically
- **SW1 (rotary encoder)** — bottom-left, at least 5 mm from the board edge so the knob clears
- **C1–C6** — sprinkle near each connector

## 11. Route

Two-layer board, ground pour on bottom layer. Trace widths:
- Power (`+3V3`, `+5V`, `GND` connections to ground pour stitching): **0.5 mm**
- Signals: **0.25 mm**
- Vias: **0.6 mm OD / 0.3 mm drill**

These are conservative for JLCPCB's standard tier (which can do 0.15 mm / 0.15 mm trace/space).

## 12. Run DRC

Inspect → Design Rules Checker. Fix all errors. Match the design rules to JLCPCB's capability:
- File → Board Setup → Design Rules → Constraints
- Min clearance: 0.15 mm
- Min track width: 0.15 mm
- Min hole: 0.3 mm
- Min via diameter: 0.45 mm

Then re-run DRC with the tightened rules.

## 13. Generate fab outputs

```bash
# From hardware/pcb/, with kicad-cli on PATH:
kicad-cli pcb export gerbers --output fab/intermediate/ gwent-hat.kicad_pcb
kicad-cli pcb export drill --output fab/intermediate/ --excellon-zeros-format suppressleading gwent-hat.kicad_pcb
```

Or via the GUI: File → Plot (Gerbers) → use defaults, output to `fab/intermediate/`. Then File → Fabrication Outputs → Drill Files.

For the BOM and pick-and-place files, install the JLCPCB plugin for KiCad (https://github.com/Bouni/kicad-jlcpcb-tools) and run it from the PCB editor's plugin menu.

## 14. Zip and upload

```bash
cd fab/intermediate
zip ../gwent-hat-v1.0-jlcpcb.zip *.gbr *.drl *.csv
cd ..
```

Upload `gwent-hat-v1.0-jlcpcb.zip` to https://jlcpcb.com → New Order. Pick:
- 2 layers, 1.6 mm thickness
- HASL (lead-free) finish — or ENIG if you want pretty
- Quantity: 5
- Surface finish: matte black silkscreen looks great with the Witcher theme; cost about the same as standard green

Pay (~$15 with shipping). Boards arrive in 5–10 days.

## 15. Commit the as-fabbed artifact

```bash
git add fab/gwent-hat-v1.0-jlcpcb.zip
git commit -m "hardware: fab v1.0 — first-run JLCPCB upload"
```

## Sanity checks before ordering

- [ ] ERC clean (zero errors, warnings reviewed)
- [ ] DRC clean
- [ ] All footprints on the right side of the board (J1 must be on the **bottom** copper layer if you want it to mate with the Pi underneath, OR on the top with a stacking header — pick one and be consistent)
- [ ] Mounting holes match Pi 4 positions (verify by overlaying the Pi mechanical drawing in `libs/pi-hat/hat-board-mechanical.pdf` if available)
- [ ] J1 (GPIO header) pin 1 location is correct (check 3D viewer with a Pi 4 model imported)
- [ ] No traces under the GPIO header (pins will fight ground pour)
- [ ] Silkscreen labels every connector (`RC522`, `OLED`, `MUX`, `ENC`, `+3V3`, `GND`)
- [ ] Pi HAT spec board outline rounded corners present
- [ ] Board fits Pi HAT mechanical PDF dimensions exactly

When in doubt, export the board as STEP and import it into Fusion 360 alongside a Pi 4 STEP model — collisions become obvious.
