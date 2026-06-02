#!/usr/bin/env npx tsx
/**
 * Imagen — generic, brief-fed image generator (Google Gemini API)
 *
 * A "meta skill": instead of hardcoding the creative direction, it is *fed* a
 * brief file (the embedded image-content prompt) and a per-image variant. The
 * final prompt is composed as:
 *
 *     [optional base style]  +  [BRIEF block from --brief file]  +  [variant]
 *
 * The brief is the reusable scaffold (e.g. hardware/enclosure/design-outline.md);
 * the variant is the knob string you feed on the CLI for each concept.
 *
 * Usage:
 *     npx tsx generate.ts --brief hardware/enclosure/design-outline.md "<variant>"
 *     npx tsx generate.ts "<full prompt>"            # brief auto-detected if present
 *     npx tsx generate.ts --preset fenrir-logo
 *     npx tsx generate.ts --brief brief.md "<variant>" --size 4:3 --output out.png --count 2
 *     GEMINI_IMAGE_MODEL=gemini-2.5-flash-image npx tsx generate.ts ...
 *
 * Requires GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
 */

import { writeFileSync, mkdirSync, readFileSync, existsSync } from "fs";
import { resolve, dirname, basename, extname, join } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Model is configurable so the skill survives free-tier/billing/model changes.
// Override with --model <name> or the GEMINI_IMAGE_MODEL env var.
// gemini-2.5-flash-image reliably returns image bytes; 3.1-flash-image often
// returns a 200 with no image for terse prompts.
const DEFAULT_MODEL = "gemini-2.5-flash-image";

function endpointFor(model: string): string {
  return (
    "https://generativelanguage.googleapis.com/v1beta/models/" +
    `${model}:generateContent`
  );
}

const REQUEST_TIMEOUT_MS = 120_000;

// Default brief locations tried (relative to cwd) when --brief is omitted.
const DEFAULT_BRIEF_CANDIDATES = [
  "hardware/enclosure/design-outline.md",
];

const PRESETS: Record<string, string> = {
  "fenrir-logo":
    "A fierce Norse wolf head in a circular medallion frame with runic " +
    "inscriptions around the border, metallic silver and ice-blue tones, " +
    "dark moody lighting",
  "fenrir-icon":
    "A compact wolf head icon suitable for favicon use, clean lines, " +
    "Nordic style, metallic finish",
  "norse-badge":
    "An ornate Norse shield badge with intertwined wolf and serpent " +
    "knotwork, aged metal texture",
  "fenrir-medallion":
    "A heavy iron medallion with Fenrir the wolf breaking chains, " +
    "Elder Futhark runes inscribed around the edge, moonlit atmosphere",
};

const VALID_ASPECT_RATIOS = new Set(["1:1", "16:9", "9:16", "4:3", "3:4"]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiKey(): string | undefined {
  const fromEnv = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  if (fromEnv) return fromEnv;
  // Fall back to .secrets (preferred) then .env at the cwd (repo root).
  for (const file of [".secrets", ".env"]) {
    try {
      const p = resolve(process.cwd(), file);
      if (!existsSync(p)) continue;
      for (const raw of readFileSync(p, "utf-8").split("\n")) {
        let line = raw.trim();
        if (!line || line.startsWith("#")) continue;
        if (line.startsWith("export ")) line = line.slice(7).trim();
        const m = line.match(/^(?:GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*(.+)$/);
        if (m) return m[1].trim().replace(/^['"]|['"]$/g, "");
      }
    } catch {
      /* ignore unreadable file */
    }
  }
  return undefined;
}

function getModel(cliModel?: string): string {
  return cliModel || process.env.GEMINI_IMAGE_MODEL || DEFAULT_MODEL;
}

/** Extract the fenced ``` block from a "## Base Prompt"-style style file. */
function loadBasePrompt(): string {
  const basePromptPath = join(__dirname, "base-prompt.md");
  if (!existsSync(basePromptPath)) return "";
  const content = readFileSync(basePromptPath, "utf-8");
  const match = content.match(/```\n([\s\S]*?)```/);
  return match ? match[1].trim() : "";
}

/**
 * Load the embedded image-content prompt from a brief file. Resolution order:
 *   1. Text between <!-- imagen:brief:start --> and <!-- imagen:brief:end -->
 *   2. The first fenced ``` code block in the file
 *   3. The whole file, trimmed
 * This is what makes the skill generic: the creative scaffold lives in the
 * brief, not in this script.
 */
function loadBrief(path: string): string {
  if (!existsSync(path)) {
    console.error(`[imagen] Error: brief file not found: ${path}`);
    process.exit(1);
  }
  const content = readFileSync(path, "utf-8");
  const marked = content.match(
    /<!--\s*imagen:brief:start\s*-->([\s\S]*?)<!--\s*imagen:brief:end\s*-->/
  );
  if (marked) return marked[1].trim();
  const fenced = content.match(/```[a-zA-Z0-9-]*\n([\s\S]*?)```/);
  if (fenced) return fenced[1].trim();
  return content.trim();
}

/** When --brief is omitted, auto-detect a default brief in the project. */
function detectDefaultBrief(): string | undefined {
  for (const cand of DEFAULT_BRIEF_CANDIDATES) {
    if (existsSync(cand)) return cand;
  }
  return undefined;
}

type RefImage = { mimeType: string; data: string };

function buildRequestBody(prompt: string, aspectRatio: string, ref?: RefImage) {
  const parts: Array<Record<string, unknown>> = [];
  if (ref) parts.push({ inlineData: { mimeType: ref.mimeType, data: ref.data } });
  parts.push({ text: prompt });
  return {
    contents: [{ parts }],
    generationConfig: {
      responseModalities: ["IMAGE"],
      imageConfig: { aspectRatio },
    },
  };
}

function loadRefImage(path: string): RefImage {
  if (!existsSync(path)) {
    console.error(`[imagen] Error: reference image not found: ${path}`);
    process.exit(1);
  }
  const ext = extname(path).toLowerCase();
  const mimeType =
    ext === ".jpg" || ext === ".jpeg"
      ? "image/jpeg"
      : ext === ".webp"
        ? "image/webp"
        : "image/png";
  return { mimeType, data: readFileSync(path).toString("base64") };
}

async function generateImage(
  apiKey: string,
  model: string,
  prompt: string,
  aspectRatio: string,
  ref?: RefImage
): Promise<Buffer[]> {
  const url = `${endpointFor(model)}?key=${apiKey}`;
  const body = JSON.stringify(buildRequestBody(prompt, aspectRatio, ref));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      console.error(`[imagen] Request timed out after ${REQUEST_TIMEOUT_MS / 1000}s`);
      process.exit(1);
    }
    console.error(`[imagen] Network error: ${err}`);
    process.exit(1);
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    console.error(`[imagen] API error: HTTP ${response.status} (model ${model})\n${errorBody}`);
    process.exit(1);
  }

  const responseBody = await response.json();

  const images: Buffer[] = [];
  const candidates = responseBody.candidates ?? [];
  for (const candidate of candidates) {
    const parts = candidate.content?.parts ?? [];
    for (const part of parts) {
      const inlineData = part.inlineData ?? part.inline_data;
      if (
        inlineData &&
        ((inlineData.mimeType ?? "").startsWith("image/") ||
          (inlineData.mime_type ?? "").startsWith("image/"))
      ) {
        const raw = inlineData.data;
        if (raw) {
          images.push(Buffer.from(raw, "base64"));
        }
      }
    }
  }

  if (images.length === 0) {
    console.error(
      "[imagen] No image data found in API response. Response structure:\n" +
        JSON.stringify(responseBody, null, 2).slice(0, 2000)
    );
    process.exit(1);
  }

  return images;
}

function outputPath(base: string, index: number, count: number): string {
  if (count === 1) return base;
  const ext = extname(base) || ".png";
  const stem = basename(base, ext);
  const dir = dirname(base);
  return join(dir, `${stem}-${index + 1}${ext}`);
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(argv: string[]) {
  const args: {
    prompt?: string;
    preset?: string;
    brief?: string;
    model?: string;
    ref?: string;
    size: string;
    output?: string;
    count: number;
    noBase: boolean;
  } = { size: "1:1", count: 1, noBase: false };

  let i = 0;
  while (i < argv.length) {
    const arg = argv[i];
    if (arg === "--preset" && i + 1 < argv.length) {
      args.preset = argv[++i];
    } else if (arg === "--brief" && i + 1 < argv.length) {
      args.brief = argv[++i];
    } else if (arg === "--model" && i + 1 < argv.length) {
      args.model = argv[++i];
    } else if (arg === "--ref" && i + 1 < argv.length) {
      args.ref = argv[++i];
    } else if (arg === "--size" && i + 1 < argv.length) {
      args.size = argv[++i];
    } else if (arg === "--output" && i + 1 < argv.length) {
      args.output = argv[++i];
    } else if (arg === "--count" && i + 1 < argv.length) {
      args.count = parseInt(argv[++i], 10);
    } else if (arg === "--no-base") {
      args.noBase = true;
    } else if (arg === "--help" || arg === "-h") {
      console.log(
        "Usage: npx tsx generate.ts \"<variant>\" [--brief <file>] [--model <name>] " +
          "[--preset <name>] [--size <ratio>] [--output <path>] [--count <n>]\n\n" +
          "The --brief file supplies the embedded image-content prompt (the reusable\n" +
          "scaffold); the positional <variant> supplies the per-image knob string.\n\n" +
          "Presets: " + Object.keys(PRESETS).join(", ") + "\n" +
          "Sizes: " + [...VALID_ASPECT_RATIOS].join(", ") + "\n" +
          "Model: --model or GEMINI_IMAGE_MODEL (default " + DEFAULT_MODEL + ")"
      );
      process.exit(0);
    } else if (!arg.startsWith("--")) {
      args.prompt = arg;
    }
    i++;
  }

  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  // Resolve the brief (explicit --brief, else auto-detect a project default).
  const briefPath = args.brief ?? detectDefaultBrief();
  const brief = briefPath ? loadBrief(briefPath) : "";

  // A run must have *something* to say: a brief, a variant, or a preset.
  if (!brief && !args.prompt && !args.preset) {
    console.error(
      "[imagen] Error: nothing to generate. Provide a --brief file, a positional\n" +
        "<variant> prompt, or a --preset. The meta-skill must be fed content."
    );
    process.exit(1);
  }

  if (args.preset && !PRESETS[args.preset]) {
    console.error(
      `[imagen] Error: unknown preset '${args.preset}'. ` +
        `Valid options: ${Object.keys(PRESETS).join(", ")}`
    );
    process.exit(1);
  }

  if (!VALID_ASPECT_RATIOS.has(args.size)) {
    console.error(
      `[imagen] Error: invalid aspect ratio '${args.size}'. ` +
        `Valid options: ${[...VALID_ASPECT_RATIOS].sort().join(", ")}`
    );
    process.exit(1);
  }

  if (args.count < 1 || args.count > 4) {
    console.error("[imagen] Error: --count must be between 1 and 4.");
    process.exit(1);
  }

  const apiKey = getApiKey();
  if (!apiKey) {
    console.error(
      "[imagen] Error: no API key found.\n\n" +
        "Set one of the following environment variables:\n" +
        "  export GOOGLE_API_KEY=your-key-here\n" +
        "  export GEMINI_API_KEY=your-key-here\n\n" +
        "Get a key at: https://aistudio.google.com/apikey"
    );
    process.exit(1);
  }

  const model = getModel(args.model);

  // Compose: [base style] + [brief scaffold] + [variant/preset].
  const variant = args.preset ? PRESETS[args.preset] : args.prompt;
  const layers: string[] = [];
  const baseStyle = args.noBase ? "" : loadBasePrompt();
  if (baseStyle) {
    layers.push(baseStyle);
    console.error("[imagen] Base style loaded from base-prompt.md");
  }
  if (brief) {
    layers.push(brief);
    console.error(`[imagen] Brief loaded from ${briefPath}`);
  }
  if (variant) layers.push(variant);
  const prompt = layers.join("\n\n");

  console.error(`[imagen] Model: ${model}`);

  const ref = args.ref ? loadRefImage(args.ref) : undefined;
  if (ref) console.error(`[imagen] Reference image: ${args.ref}`);

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const baseOutput = args.output ?? `generated-${timestamp}.png`;

  const savedPaths: string[] = [];

  for (let i = 0; i < args.count; i++) {
    if (args.count > 1) {
      console.error(`[imagen] Generating image ${i + 1} of ${args.count}...`);
    }

    const images = await generateImage(apiKey, model, prompt, args.size, ref);
    const imageData = images[0];

    const dest = outputPath(baseOutput, i, args.count);
    mkdirSync(dirname(resolve(dest)), { recursive: true });
    writeFileSync(dest, imageData);

    const absPath = resolve(dest);
    savedPaths.push(absPath);
    console.log(absPath);
  }

  console.error(`\n[imagen] Done. ${savedPaths.length} image(s) saved.`);
}

main();
