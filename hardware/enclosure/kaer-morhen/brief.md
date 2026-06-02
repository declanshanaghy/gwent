# Kaer Morhen — official physical reference (FINAL design)

The keep with twin towers. This is the **FINAL, locked physical design reference** for the
Fusion 360 model — **no further iteration** (evolved: side-towers → iso-f → var-f →
**shelf-d2-b** = the final form). `_ref.png` is the locked reference image.

All views are generated **image-to-image from `_ref.png`** so they stay consistent:

```
npx tsx .claude/skills/imagen/generate.ts --no-base \
  --ref hardware/enclosure/kaer-morhen/_ref.png \
  --brief hardware/enclosure/kaer-morhen/brief.md \
  --size 4:3 --output .../ortho-front.png "VIEW=strict orthographic front elevation ..."
```

## Locked form spec (source of truth for Fusion 360)

- **One continuous connected faceted single body** — a keep with twin towers. Footprint
  **≤ 250 × 250 mm** (fits the Bambu X1C 256 mm plate; final part prints in sections, faked
  later as embellishments).
- **Central base** built around the **power brick (~112 × 76 × 35 mm)**, sitting behind the
  screen; houses Pi 4 + HAT, amplifier, isolator.
- **Central 7″ landscape screen (~194 mm wide) tilted ~65°** rising from the body.
- **Two TALL faceted "castle-keep" player towers** rising from the body, flanking the
  screen, tapering with flat caps. Each tower:
  - a **score LED matrix display on its upper FRONT face**, facing forward (≈ 50 × 25 mm
    display + cover; aperture ≈ 60 × 35 mm);
  - a **round speaker on its FRONT face**, below the display, facing forward.
- **Gems LED panel** centered **above the screen** on a raised **centerpiece crest**.
- **Front-center card shelf** protruding forward onto the desk: a flat card pad whose front
  edge is **lip-free and ramps smoothly down to the desk** with rounded contours, so cards
  slide on/off.
- **Power cord exits the rear.** No OLED, no knob.

<!-- imagen:brief:start -->
Render the tabletop Gwent game console shown in the reference image as a clean CAD-style
study — neutral matte grey clay model, no color, materials, text, branding or ornament,
soft even lighting, plain white seamless background, centered with generous margins.

KEEP the form exactly as the reference: ONE continuous faceted single body (a keep with twin
towers) fitting within about 250 by 250 mm. A central faceted base sits behind the screen. A
central 7-inch landscape screen tilts about 65 degrees up out of the body. Two TALL faceted
angular "castle-keep" player towers rise from the body flanking the screen, tapering with
flat caps. Each tower has a square score display on its upper FRONT face facing forward and a
round speaker on its FRONT face below the display. A small gems panel sits on a raised
centerpiece crest centered above the screen. A flat card shelf protrudes from the front
center, its front edge lip-free and ramping smoothly down to the desk with rounded contours.
The power cord exits the rear. No secondary screen, no knob. One connected body, clean
readable geometry. No text, no logos, no human hands.
<!-- imagen:brief:end -->
