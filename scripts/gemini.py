#!/usr/bin/env python3
"""Raw Gemini API smoke test / capability explorer.

Loads GEMINI_API_KEY (or GOOGLE_API_KEY) from the environment or the repo-root
`.secrets` file and talks to the Generative Language API with nothing but the
standard library, so it has no third-party dependencies.

Subcommands:
    list                     List every model the key can see + its methods.
    probe                    For each image-capable model, send one tiny
                             generateContent request and report SUCCESS / the
                             quota or error status (does not save images).
    test [model] [prompt]    Generate one image and save it to scripts/gemini-test.png.
    (no args)                Runs `list` then `probe` — "what is this key allowed to do".

Examples:
    python scripts/gemini.py
    python scripts/gemini.py list
    python scripts/gemini.py test gemini-2.5-flash-image "a wolf medallion"
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image-preview"


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    secrets = REPO_ROOT / ".secrets"
    if secrets.exists():
        for raw in secrets.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                if line.startswith(name + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    sys.exit("[gemini] no GEMINI_API_KEY / GOOGLE_API_KEY in env or .secrets")


def _get(path: str, key: str) -> dict:
    url = f"{BASE}/{path}{'&' if '?' in path else '?'}key={key}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _post(path: str, key: str, body: dict, timeout: int = 120) -> tuple[int, dict | str]:
    url = f"{BASE}/{path}?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(detail)
        except json.JSONDecodeError:
            return e.code, detail


def list_models(key: str) -> list[dict]:
    models: list[dict] = []
    page = ""
    while True:
        path = f"models?pageSize=200{page}"
        data = _get(path, key)
        models.extend(data.get("models", []))
        token = data.get("nextPageToken")
        if not token:
            break
        page = f"&pageToken={token}"
    return models


def cmd_list(key: str) -> int:
    models = list_models(key)
    print(f"[gemini] {len(models)} models visible to this key\n")
    img, other = [], []
    for m in models:
        name = m.get("name", "").replace("models/", "")
        methods = m.get("supportedGenerationMethods", [])
        (img if ("image" in name.lower() or "imagen" in name.lower()) else other).append(
            (name, methods)
        )
    print("== IMAGE / IMAGEN models ==")
    for name, methods in sorted(img):
        print(f"  {name:48s} {methods}")
    print("\n== other models ==")
    for name, methods in sorted(other):
        print(f"  {name:48s} {methods}")
    return 0


def _status_of(payload: dict | str) -> str:
    if isinstance(payload, str):
        return payload[:160]
    err = payload.get("error")
    if err:
        msg = err.get("message", "")
        limit = "limit: 0" if "limit: 0" in msg else ""
        return f"{err.get('code')} {err.get('status')} {limit}".strip()
    parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    has_img = any(
        (p.get("inlineData") or p.get("inline_data")) for p in parts
    )
    return "image returned" if has_img else "no image in 200 response"


def cmd_probe(key: str) -> int:
    models = list_models(key)
    targets = [
        m.get("name", "").replace("models/", "")
        for m in models
        if "image" in m.get("name", "").lower()
        and "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    if not targets:
        print("[gemini] no generateContent image models visible")
        return 1
    print(f"[gemini] probing {len(targets)} image model(s) with a 1-token request:\n")
    ok = 0
    body = {
        "contents": [{"parts": [{"text": "test"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
    }
    for model in sorted(targets):
        status, payload = _post(f"models/{model}:generateContent", key, body, timeout=90)
        verdict = _status_of(payload)
        flag = "OK  " if "image returned" in verdict else "----"
        if "image returned" in verdict:
            ok += 1
        print(f"  {flag} {model:48s} HTTP {status}  {verdict}")
    print(f"\n[gemini] {ok}/{len(targets)} image models actually generated.")
    return 0 if ok else 2


def cmd_test(key: str, model: str, prompt: str) -> int:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
    }
    print(f"[gemini] test model={model} prompt={prompt!r}")
    status, payload = _post(f"models/{model}:generateContent", key, body)
    if isinstance(payload, dict):
        parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            mime = (inline or {}).get("mimeType") or (inline or {}).get("mime_type", "")
            if inline and mime.startswith("image/"):
                out = REPO_ROOT / "scripts" / "gemini-test.png"
                out.write_bytes(base64.b64decode(inline["data"]))
                print(f"[gemini] HTTP {status} SUCCESS — saved {out} ({out.stat().st_size} bytes)")
                return 0
    print(f"[gemini] HTTP {status} — {_status_of(payload)}")
    return 1


def main(argv: list[str]) -> int:
    key = load_key()
    cmd = argv[0] if argv else "explore"
    if cmd == "list":
        return cmd_list(key)
    if cmd == "probe":
        return cmd_probe(key)
    if cmd == "test":
        model = argv[1] if len(argv) > 1 else DEFAULT_IMAGE_MODEL
        prompt = argv[2] if len(argv) > 2 else "an aged iron wolf medallion, dark fantasy, centered"
        return cmd_test(key, model, prompt)
    # default: explore
    cmd_list(key)
    print()
    return cmd_probe(key)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
