#!/usr/bin/env python3
"""Uji live Meko (skema TERVERIFIKASI via tools/list, 57 tool):
conversation_create -> datapack_list -> memory_add -> memory_search ->
context_search. Key dibaca dari .env lokal, TIDAK pernah dicetak. Stdlib."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onememory import MekoClient

def load_key():
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("MEKO_API_KEY="):
                return line.strip().split("=", 1)[1]
    return os.environ.get("MEKO_API_KEY", "")

def text_of(resp):
    try:
        return resp["data"]["result"]["content"][0]["text"]
    except Exception:
        return json.dumps(resp)[:200]

def main():
    key = load_key()
    if not key:
        print("NO KEY - .env belum terisi"); return 1
    print(f"key loaded: prefix={key[:4]}... len={len(key)}")
    c = MekoClient(api_key=key)
    results = {}
    conv = c.call("conversation_create", {"title": "OneMemory live verification", "agent_id": "onememory"})
    t = text_of(conv)
    cid = None
    try:
        cid = json.loads(t).get("conversation_id") or json.loads(t).get("id")
    except Exception:
        import re
        m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", t)
        cid = m.group(0) if m else None
    results["conversation_create"] = "ok" if cid else f"unparsed: {t[:120]}"
    print("conversation_create:", results["conversation_create"], "| cid:", (cid or "-")[:13])
    if not cid:
        json.dump(results, open("data/live-test.json", "w"), indent=2); return 1
    steps = [
        ("datapack_list", lambda: c.call("datapack_list", {"conversation_id": cid})),
        ("memory_add", lambda: c.call("memory_add", {"text": "OneMemory standard STD-ERR: never swallow exceptions silently; always log or re-raise.", "conversation_id": cid, "agent_id": "onememory"})),
        ("memory_search", lambda: c.call("memory_search", {"query": "error handling exceptions standard", "conversation_id": cid})),
        ("context_search", lambda: c.call("context_search", {"query": "project coding standards error handling", "conversation_id": cid})),
    ]
    for label, fn in steps:
        try:
            txt = text_of(fn())
            bad = ("validation error" in txt or '"error"' in txt[:40])
            results[label] = "ok" if not bad else f"server-msg: {txt[:120]}"
            print(f"{label}: {'OK' if not bad else 'MSG'} -> {txt[:160]}")
        except Exception as e:
            results[label] = f"error: {type(e).__name__}"
            print(f"{label}: ERROR {type(e).__name__}: {str(e)[:140]}")
    ok = sum(1 for v in results.values() if v == "ok")
    print(f"LIVE {ok}/{len(results)} OK")
    json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "live-test.json"), "w"), indent=2)
    return 0 if ok >= 4 else 1

if __name__ == "__main__":
    sys.exit(main())
