# Gwent Companion — Enclosure Concept Brief & Image-Gen Meta-Prompt

**Purpose.** Brainstorm the *look and feel* of the physical enclosure **before any CAD**.
Fill the `[KNOBS]` below, assemble a prompt from the template, run it through Gemini image
generation (the `imagen` skill), drop the output in `concepts/`, and log the settings in
the iteration log. Iterate widely first (contrast), then converge.

> **Concepts first, tech design later.** This file is purely about aesthetics + spatial
> composition. Functional dimensions, print rules, and the parametric Fusion model live in
> the engineering plan and `reference/` — *not here*. Keep these prompts evocative, not
> dimensioned.

---

## What this device is

A tabletop, all-in-one **companion console for playing Gwent** (the card game from *The
Witcher 3*). It sits on a table between two players, runs the game, keeps score, and reads
the players' **physical RFID cards**. It should read as a premium, themed game object — a
relic you'd find on a war-table in the Northern Realms — not a generic gadget.

It must support three ways to play at once: **old school** (physical LED scoreboard + tap
cards), **newschool** (the touchscreen UI), and **new-new-school** (AI opponents on the
screen). So every concept carries the same set of elements — but *how they're arranged is
wide open*.

---

## Required ELEMENTS — must all appear, arrangement is OPEN

Every concept must include all of these. **Do not fix where they sit** — let each concept
explore a genuinely different composition.

1. A **~7-inch screen, tilted ~65° upward** toward a seated player (steep, near-upright),
   showing a stylized fantasy game UI.
2. A glowing **three-panel scoreboard** — two large numeric score panels and a row of
   "life" gems/diamonds between them (player 1 · gems · player 2).
3. A **small secondary status display** (a little glowing readout).
4. A **card-tap pad** — a flat spot where a player rests/taps a physical card to scan it.
5. **One rotary knob** (a tactile control).
6. **Speaker grilles** somewhere on the body.
7. A **single power cord** leaving the back.
8. One **cohesive sculpted shell** — premium, themed, no seams-as-afterthought.

---

## KNOBS

### LAYOUT / ARRANGEMENT — *iterate this hardest; it's the primary variable*
`[ screen-up with a flat front control deck
 | screen flanked by two side towers that hold the score panels
 | scoreboard mounted above the screen like an illuminated marquee
 | wrap-around cockpit/dashboard curving toward the player
 | tiered altar with elements stepped on different levels
 | fold-open campaign/war chest (lid = screen, base = deck)
 | radial composition around a central card-tap pad
 | asymmetric — controls clustered to one side ]`

### MATERIAL
`[ aged bronze | blackened wrought iron | carved dark oak | bone & ivory
 | weathered leather & brass | Nilfgaardian black steel | Skellige timber & rope
 | arcane carved stone | gunmetal with verdigris ]`

### MOTIF
`[ Witcher wolf-school medallion | Northern Realms heraldry | engraved elder runes
 | dark-fantasy filigree | battlefield-map etchings | carved beast claws/fangs ]`

### STYLE / ERA
`[ medieval rustic | ornate baroque | grimdark war-worn | arcane-steampunk
 | clean stylized game-prop | brutalist stone monument ]`

### PALETTE
`[ e.g. charcoal + ember-orange + brass | bone-white + blood-red + iron
 | deep forest green + gold | midnight blue + silver + frost ]`

### MOOD / LIGHTING
`[ candle-lit tavern | cold moonlit | forge-glow from within | neutral studio softbox ]`

### WEAR
`[ pristine museum piece ←→ scratched, battle-worn, patinated, road-weathered ]`

### SILHOUETTE
`[ war-room podium | reading lectern | shrine/altar | traveling campaign case
 | carved gameboard slab | obelisk ]`

### SCREEN FRAMING
`[ iron-bound window | carved stone frame | leather-wrapped bezel | banner-flanked
 | brass porthole | runed arch ]`

### RENDER STYLE
`[ loose graphite concept sketch | painted concept art | photoreal product render
 | orthographic 3-view turnaround | matte-painting hero shot ]`

### VIEW
`[ hero 3/4 front | seated player POV | top-down on the deck/controls
 | exploded/cutaway | side profile showing the 65° tilt ]`

### BACKGROUND
`[ tavern table with scattered Gwent cards | neutral seamless | parchment & candlelight
 | war-table map | dark void with rim light ]`

---

## Prompt template (assemble from the knobs)

> **[RENDER STYLE]** of a **[SILHOUETTE]** Gwent game companion console for the world of
> The Witcher, **[MATERIAL]** with **[MOTIF]** and **[WEAR]**. A ~7-inch screen tilted ~65°
> upward on the upper body shows a stylized fantasy game UI. Using a **[LAYOUT]**
> composition, it carries a glowing three-panel scoreboard (two score numbers with a row of
> life-gems between), a small secondary status readout, a flat card-tap pad, and a single
> rotary knob; speaker grilles sit on the body and one power cord trails from the back.
> **[STYLE/ERA]** aesthetic, **[PALETTE]** palette, **[MOOD/LIGHTING]**, screen set in a
> **[SCREEN FRAMING]**. **[VIEW]**, **[BACKGROUND]**. Dark-fantasy, premium tabletop relic.
> **No branding or logos, no visible screws or fasteners, no readable text on the screen,
> no human hands, single cohesive object.**

Tip: keep the *required elements* sentence intact every time; only swap the bracketed
knobs. Generate distinct knob combinations per batch so the set spans a wide design space
before narrowing.

---

## Batch plan

- **Batch 1 (wide net):** 4–6 variants spanning very different LAYOUT × MATERIAL × STYLE
  combos (e.g. iron podium / oak campaign-case / stone altar / bronze cockpit) so the
  contrast is obvious.
- **Batch 2+:** take the 1–2 favorites and vary the *softer* knobs (palette, wear, screen
  framing, view) to refine.
- Stop when one direction clearly wins; that becomes the reference for the Fusion model.

---

## Iteration log

| # | File | LAYOUT | MATERIAL | STYLE | other knobs | verdict |
|---|------|--------|----------|-------|-------------|---------|
| _ | _    | _      | _        | _     | _           | _       |
