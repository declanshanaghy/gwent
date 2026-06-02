# Form 03 / iso-f riff — unified organic body

Variations on the chosen iso-f direction. Neutral grey clay, ISO views, for review. Once a
winner is picked we go to ortho.

> **Note:** image-to-image (`--ref _seed.png`) anchored the outputs too tightly — they came
> out nearly identical. So variation is now driven by **strong distinct textual FORM
> CHARACTER descriptions per variant** (no `--ref`). `_seed.png` is kept only as the visual
> origin of this direction.

**Locked intent:**
- Keep the **soft, unified single-body** form of the seed.
- **RFID card shelf is OPEN at the front** — an open recessed slot/tray, not a closed box.
- Player towers **angled ~5° inward toward the players** (toed-in).
- **Experiment with the tower curve/profile** across variants.
- **ONE fully-connected core body** — every piece merged at its edges so it's a single
  printable/assemblable core. Any apparent "sections" are **faked later with cosmetic
  embellishments** (shallow grooves / applied trim), NOT real separate parts.
- Footprint **≤ 250 × 250 mm**. Landscape 7″ screen at ~65°. No OLED, no knob. Power cord rear.

Run loop (per variant, `--ref _seed.png`):

```
npx tsx .claude/skills/imagen/generate.ts --no-base \
  --ref hardware/enclosure/concepts/form-03-side-towers/form-03-iso-f/_seed.png \
  --brief hardware/enclosure/concepts/form-03-side-towers/form-03-iso-f/brief.md \
  --size 4:3 --output .../form-03-iso-f/var-a.png \
  "CURVE=convex barrel-profile towers; VIEW=isometric three-quarter view"
```

<!-- imagen:brief:start -->
Generate a VARIATION of the tabletop Gwent game console shown in the reference image. Keep
its soft, unified single-body clay form and overall layout. Render as a neutral matte grey
clay / foam model — no color, materials, text, branding or ornament — with soft even studio
lighting, a plain seamless background, isometric three-quarter view.

The device is ONE continuous chunky body with two player pillars rising smoothly out of it,
flanking a central 7-inch landscape screen tilted about 65 degrees upward, with a small
gems panel on a centerpiece crest centered above the screen, and an RFID card shelf
extending forward out of the front onto the desk.

APPLY THESE CHANGES:
1. The front RFID card shelf is OPEN at the front — an open recessed slot / tray, not a
   closed box.
2. The two player pillars are angled about 5 degrees inward toward the players (toed-in).
3. Vary the curvature and profile of the player towers.

HARD CONSTRAINTS: everything must read as ONE fully-connected core body — all parts merged
at their edges, nothing detached or floating. Any apparent panel or section divisions are
only shallow cosmetic surface grooves on the single body, never real separate pieces.
Footprint at most about 250 by 250 mm. No small secondary screen, no knob. No text, no
logos, no human hands.
<!-- imagen:brief:end -->
