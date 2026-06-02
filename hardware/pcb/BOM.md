# Gwent HAT — Bill of Materials

For the v1 carrier-PCB design. Assumes the existing Adafruit/SparkFun breakouts (RC522, OLED, mux, IS31FL3731 matrices, PEC11 encoder) are already in hand and plug into headers/connectors on this board.

## Board

| Item | Spec | Source | Notes |
|---|---|---|---|
| PCB | 65 × 56.5 mm, 2-layer, 1.6 mm FR4, 1 oz Cu, ENIG (or HASL economy) | JLCPCB | ~$5 for 5 boards (HASL), ~$15 (ENIG); add $2 for thicker silk |

## Active components on the HAT itself

(All breakouts are external — they plug into this board via headers. Only passives + connectors live on this PCB.)

| Ref | Description | Qty | Footprint | KiCad symbol | Manufacturer / part | LCSC | Source / cost (approx) |
|---|---|---|---|---|---|---|---|
| J1 | 2×20 stacking pin header, 0.1″ pitch, female | 1 | `Connector_Generic:Conn_02x20_Odd_Even` (long pins through-hole) | `Connector_Generic:Conn_02x20_Odd_Even` | Samtec ESQT-120 / Adafruit 2223 | C49258 (header) | $3 (Adafruit "extra-tall" stacking header) |
| J2 | 1×8 male pin header, 0.1″ pitch | 1 | `Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical` | `Connector:Conn_01x08_Pin` | Generic 2.54 mm | C124378 | RC522 plugs in here |
| J3 | 1×16 male pin header, 0.1″ pitch | 1 | `Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical` | `Connector:Conn_01x16_Pin` | Generic 2.54 mm | C124380 | OLED plugs in here |
| J4 | JST-SH 4-pin Qwiic — to TCA9548A mux | 1 | `Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` | `Connector_JST:JST_SH_BM04B-SRSS-TB-1x04-1MP_P1.00mm_Horizontal` | JST BM04B-SRSS-TB | C160403 | $0.20 |
| J5 | JST-SH 4-pin Qwiic — to gem matrix (mux ch 0) | 1 | (same) | (same) | (same) | (same) |  |
| J6 | JST-SH 4-pin Qwiic — to P1 score matrix (mux ch 1) | 1 | (same) | (same) | (same) | (same) |  |
| J7 | JST-SH 4-pin Qwiic — to P2 score matrix (mux ch 2) | 1 | (same) | (same) | (same) | (same) |  |
| J5 | 1×5 male pin header, 0.1″ pitch — wires off-board to PEC11 encoder | 1 | `Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical` | `Connector_Generic:Conn_01x05` | Generic 2.54 mm | C124379 | Pinout: 1=A, 2=B, 3=C, 4=S1, 5=S2 |
| C1–C5 | 100 nF X7R 0805 ceramic, 16V — decoupling | 5 | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Yageo CC0805KRX7R9BB104 | C49678 | $0.01 each |
| C6 | 10 µF X5R 0805 ceramic, 10V — bulk decoupling | 1 | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | Samsung CL21A106KAFNNNE | C15850 | $0.05 |
| C7, C8 | 100 nF 0805 (optional) — encoder hardware debounce | 2 | `Capacitor_SMD:C_0805_2012Metric` | `Device:C` | (same as C1) | (same) | optional |
| H1–H4 | M2.5 mounting holes, 2.7 mm dia, plated | 4 | `MountingHole:MountingHole_2.7mm_M2.5_DIN965_Pad` | `Mechanical:MountingHole` | — | — | — |

**Total active BOM cost on the HAT itself: < $5** (plus PCB).

## External modules (plug in via headers/Qwiic)

These are NOT on the HAT — they're the existing breakouts the project already uses. Listed for reference / total system BOM.

| Module | Source | Approx cost |
|---|---|---|
| MFRC522 RFID breakout | generic / Amazon | $3 |
| Adafruit 2.42″ 128×64 OLED (SSD1306) — Adafruit 2719 | Adafruit / DigiKey | $40 |
| SparkFun Qwiic Mux Breakout 8-channel (TCA9548A) — SparkFun BOB-16784 | SparkFun / DigiKey | $11 |
| Adafruit IS31FL3731 9×16 charlieplex matrix breakout — red, blue, yellow — Adafruit 2944 / 2945 / 2948 (etc.) | Adafruit / DigiKey | $25 × 3 = $75 |
| PEC11 rotary encoder (panel-mount, off-board) — Bourns PEC11R-4220F-S0024 | DigiKey / LCSC | $2 |
| 5-conductor flexible cable, 100–200 mm — HAT J5 to encoder | various | $1 |
| Raspberry Pi 4 Model B (2GB+) | various | $45–80 |
| 4× M2.5 brass standoffs, 11–15 mm length, with screws | DigiKey / Amazon | $5 |
| 4× Qwiic JST-SH 4-pin cables, 100–200 mm | SparkFun / Amazon | $1.50 × 4 = $6 |

**Total system cost (excluding Pi): ~$150**

## JLCPCB-specific notes

- **Tier**: "Standard PCB", 2 layers, 1.6 mm thickness, HASL (lead-free) finish — cheapest option.
- **Min trace/space**: 6 mil / 6 mil — easy for this design.
- **Min hole**: 0.3 mm — no problem; mounting holes are 2.7 mm and via holes are typically 0.3 mm.
- **Surface finish**: HASL is fine; ENIG is nicer-looking and slightly better solderability for ~$10 extra.
- **Assembly (PCBA)**: Skip for v1 — every BOM item is through-hole or trivial 0805. Hand-assembly is faster than configuring JLC's CPL/BOM upload for ten parts.
- **If you do want PCBA**: use the [JLCPCB plugin for KiCad](https://github.com/Bouni/kicad-jlcpcb-tools) to generate the BOM CSV and CPL file in the format JLC expects. The LCSC part numbers above are the right values for the `LCSC Part #` column.

## Cost summary

| Line item | Cost |
|---|---|
| PCB (5 boards, HASL) | $5 |
| BOM components on HAT (per board) | $5 |
| Shipping (Standard) | $15 |
| **Total for first run of 5 unassembled HATs** | **~$45** |

If you also order PCBA for the 0805 caps + JST connectors: add ~$30–50 for setup + per-board cost. Not worth it for a 5-board run unless you really hate hand-soldering.
