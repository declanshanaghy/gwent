# Reference sources — Gwent Companion enclosure

Datasheets and dimensional sources for every component the enclosure must house. Files in
this directory are committed so the design is reproducible without re-fetching. Pulled
2026-06-01.

## Files in this directory

| File | Part | What it gives | Source URL |
|---|---|---|---|
| `rpi-7in-display-mechanical-drawing.pdf` | Official RPi 7″ DSI touchscreen | Outline + M2.5 Pi-mount + M3 display hole pattern | datasheets.raspberrypi.com/display/7-inch-display-mechanical-drawing.pdf |
| `rpi-7in-display-product-brief.pdf` | "" | Electrical/overview, resolution | datasheets.raspberrypi.com/display/7-inch-display-product-brief.pdf |
| `rpi4-mechanical-drawing.pdf` | Raspberry Pi 4 B | Board outline + 58×49 M2.5 holes + connector positions | datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf |
| `adafruit-2719-oled-submodule-drawing.pdf` | Adafruit 2719 2.42″ OLED | Glass/active-area + module mechanical | cdn-shop.adafruit.com/product-files/2719/UG-2864ASGPG01Drawing .pdf |
| `adafruit-2719-oled-display-datasheet.pdf` | "" | Full OLED panel datasheet | cdn-shop.adafruit.com/product-files/2719/UG-2864ASWPG14_wisechip.pdf |
| `adafruit-is31fl3731-16x9-guide.pdf` | Adafruit IS31FL3731 9×16 matrix | Board + driver guide | cdn-learn.adafruit.com/downloads/pdf/i31fl3731-16x9-charliplexed-pwm-led-driver.pdf |
| `mfrc522-rc522-handsontec.pdf` | MFRC522 RFID | Board dims + pinout + antenna | handsontec.com/dataspecs/RC522.pdf |
| `bourns-pec11r-datasheet.pdf` | Bourns PEC11R encoder | Bushing/shaft/footprint mechanical | bourns.com/docs/Product-Datasheets/PEC11R.pdf |

## Extracted dimensions (rough; true up against the PDFs / physical parts)

| Component | Outline (mm) | Notes |
|---|---|---|
| RPi 7″ display | 194 × 110 × 20 | Viewable 155 × 86, 800×480. M2.5 Pi-mount + M3 display holes — read drawing for exact X/Y |
| Raspberry Pi 4 B | 85 × 56 | Mount holes 58 × 49 rectangle, M2.5, 3.5 mm from edges |
| HAT carrier PCB | 65 × 56.5 × 1.6 | `hardware/pcb` KiCad project; Pi-HAT 58×49 M2.5; STEP export later |
| IS31FL3731 9×16 matrix | 43.2 × 28.0 × 4.7 | Adafruit 2946 family; need lit-grid offset + mount holes from PCB/STEP |
| OLED Adafruit 2719 | 56 × 29 × 6.8 | 4 mount holes; 22 g; active-glass offset in submodule drawing |
| MFRC522 RFID | 40 × 60 | 8-pin header; tap pad sits over antenna coil |
| PEC11R encoder | 12 mm body | M7×0.5 bushing, 6 mm flatted shaft (15/20/25/30 mm), bushing height 5 mm |
| Anker Prime A2683 brick | 112 × 76 × 35 | 200 W GaN; 4× USB-C 100 W + 2× USB-A 22.5 W; captive mains cord |
| DROK PAM8406 amp | 55.1 × 32.3 × ~15 | 5W+5W Class-D, DC 5 V, 3.5 mm in, terminal out |
| JABINCO isolator | body 60 × 20 × 20 | Pocket 120 × 20 × 20 incl. a 3.5 mm jack each end (measure unit) |
| Speaker ×2 | ~76 dia × ~30 deep | Amazon B07CWMCMQR; "err big, shrink later" placeholder |

## Web-only sources (no local file)

- Anker Prime A2683 user guide — service.anker.com (A2683); brick = 112 × 76 × 35 mm.
- DROK PAM8406 spec — droking.com product page; 55.12 × 32.26 mm, DC 5 V.
- JABINCO ground-loop isolator — Amazon B08BRSQ7JY (no datasheet; dims measured: 60×20×20).
- Speaker — Amazon B07CWMCMQR (no datasheet; size generously, refine on hand).
- IS31FL3731 PCB/STEP — github.com/adafruit/Adafruit-IS31FL3731-CharliePlex-LED-Breakout-PCB.
