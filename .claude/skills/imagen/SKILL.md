---
name: imagen
description: "Generate images using Google Gemini API. Use this skill when the user says /imagen, asks to generate an image, create artwork, make a logo, or produce visual assets."
attribution: Imported from https://github.com/declanshanaghy/fenrir-ledger — credit to @declanshanaghy
---

# Imagen — Generic, brief-fed Image Generator (meta-skill)

Generates images using Google's Gemini API. This is a **meta-skill**: the creative
direction is not hardcoded — it is **fed in** from a *brief* file (the embedded
image-content prompt) plus a per-image *variant* string. The final prompt is composed as:

```
[ base style (base-prompt.md, optional) ]  +  [ BRIEF block from --brief file ]  +  [ variant ]
```

The brief is the reusable scaffold. For the enclosure work it is
`hardware/enclosure/design-outline.md`, which carries an `<!-- imagen:brief:start -->` …
`<!-- imagen:brief:end -->` block the skill extracts. Point `--brief` at any project's
brief to reuse the skill elsewhere.

---

## How to Run

Brief-fed (the enclosure concept workflow):

```bash
npx tsx .claude/skills/imagen/generate.ts \
  --brief hardware/enclosure/design-outline.md \
  --size 4:3 --output hardware/enclosure/concepts/concept-01.png \
  "RENDER=painted concept art; SILHOUETTE=war-room podium; MATERIAL=blackened iron; LAYOUT=screen-up flat deck; MOOD=forge-glow; VIEW=hero 3/4 front"
```

Plain prompt (brief auto-detected if `hardware/enclosure/design-outline.md` exists):

```bash
npx tsx .claude/skills/imagen/generate.ts "<full prompt>"
```

### Requirements

- Node.js 18+
- `tsx`
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` environment variable
- An **image-capable model your key/plan allows**. Free-tier keys currently return
  `HTTP 429 limit: 0` for all Gemini image models (3.1/2.5/3-pro) — billing must be
  enabled on the Google project, or set `GEMINI_IMAGE_MODEL` to a model your plan permits.

---

## CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `prompt` | positional | *(the per-image variant)* | Knob string appended after the brief |
| `--brief` | path | auto-detect `hardware/enclosure/design-outline.md` | File supplying the embedded image-content prompt |
| `--model` | string | `GEMINI_IMAGE_MODEL` env, else `gemini-3.1-flash-image-preview` | Gemini image model |
| `--preset` | choice | *(none)* | One of: `fenrir-logo`, `fenrir-icon`, `norse-badge`, `fenrir-medallion` |
| `--size` | string | `1:1` | Aspect ratio (`1:1`, `16:9`, `9:16`, `4:3`, `3:4`) |
| `--output` | path | `generated-{timestamp}.png` | Output file path |
| `--count` | int | `1` | Number of images (max 4) |

A run must be fed *something*: a `--brief`, a positional variant, or a `--preset`.

---

## Presets

| Preset | Prompt |
|--------|--------|
| `fenrir-logo` | Norse wolf head in circular medallion, runic border, silver and ice-blue |
| `fenrir-icon` | Compact wolf head icon, favicon-sized, Nordic, metallic |
| `norse-badge` | Norse shield badge, wolf and serpent knotwork, aged metal |
| `fenrir-medallion` | Iron medallion, Fenrir breaking chains, Elder Futhark runes, moonlit |

---

## Output

- PNG files saved to `--output` path or `generated-{timestamp}.png`
- Absolute path printed to stdout
- Exit 0 on success, 1 on error
