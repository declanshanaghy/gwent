#!/usr/bin/env python3
"""Minimal driver for the Autodesk Fusion MCP over HTTP (stdlib only).

Usage:
  fusion.py exec <script.py>          # run a Fusion API script (def run(_context))
  fusion.py screenshot <dir> <out>    # capture view (front/top/iso-top-left/...)
  fusion.py read '<json-args>'        # arbitrary fusion_mcp_read call
"""
import sys, json, base64, urllib.request

URL = "http://localhost:27182/mcp"
HDR = {"Content-Type": "application/json",
       "Accept": "application/json, text/event-stream"}


def _post(payload, sid=None):
    h = dict(HDR)
    if sid:
        h["mcp-session-id"] = sid
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        sidout = r.headers.get("mcp-session-id")
        body = r.read().decode()
    obj = None
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
    return sidout, obj


def session():
    sid, _ = _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "drv", "version": "0"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    return sid


def call(name, args, sid):
    _, obj = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": name, "arguments": args}}, sid)
    return obj


def content_items(obj):
    if not obj:
        return []
    r = obj.get("result", obj)
    if isinstance(r, dict) and isinstance(r.get("content"), list):
        return r["content"]
    return []


def result_text(obj):
    items = content_items(obj)
    texts = [it.get("text", "") for it in items if it.get("type") == "text"]
    if texts:
        return "\n".join(texts)
    return json.dumps(obj.get("result", obj))[:2000] if obj else "(no response)"


def main():
    cmd = sys.argv[1]
    sid = session()
    if cmd == "exec":
        script = open(sys.argv[2]).read()
        obj = call("fusion_mcp_execute", {"featureType": "script", "object": {"script": script}}, sid)
        print(result_text(obj))
    elif cmd == "screenshot":
        direction, out = sys.argv[2], sys.argv[3]
        obj = call("fusion_mcp_read", {"queryType": "screenshot", "direction": direction,
                                       "width": 1100, "height": 825, "transparentBackground": False}, sid)
        data = None
        for it in content_items(obj):
            if it.get("type") == "image":
                data = it.get("data")
        if not data:
            try:
                data = json.loads(result_text(obj)).get("data")
            except Exception:
                pass
        if data:
            open(out, "wb").write(base64.b64decode(data))
            print("saved", out)
        else:
            print("NO IMAGE:", result_text(obj)[:400])
    elif cmd == "read":
        obj = call("fusion_mcp_read", json.loads(sys.argv[2]), sid)
        print(result_text(obj))


main()
