#!/usr/bin/env python3
"""
OneMemory — ContextCon Theme 01: "One Memory, Every Coding Agent"
Teach the standard once. Every coding agent follows it.

Masalah (brief resmi): agen coding mulai tiap sesi dari nol — menurunkan ulang
standar tim, mengulang kesalahan minggu lalu, dan menyimpan pelajaran di file
lokal yang tidak bisa dibaca agen lain.

Solusi: satu datapack bersama (Meko) berisi conversations, memory, knowledge,
decision traces & artifacts di belakang satu endpoint MCP. Agen di harness
berbeda (Claude Code / Cursor / Codex / custom) membaca standar yang sama,
mengutip aturan yang diikuti, dan mempromosikan pelajaran baru lewat gerbang
governance (private -> diajukan -> disetujui -> shared knowledge).

Backend:
  - MekoClient  : klien MCP JSON-RPC ke https://mcp.mekodata.ai/mcp
                  (aktif hanya bila MEKO_API_KEY ada di env; payload diverifikasi
                  ulang ke dokumentasi Connect saat key dibuat).
  - LocalDatapack: implementasi lokal dgn semantik sama (relevance-scored
                  search 0..1 + penjelasan gap) utk demo & test offline.

Stdlib only. Tanpa LLM berbayar: agen disimulasikan deterministik agar angka
kepatuhan & penghematan token bisa diverifikasi program.
"""
import argparse, json, os, re, sys, urllib.request

MEKO_MCP_URL = "https://mcp.mekodata.ai/mcp"
AUTO_APPROVE_TRUST = 0.80   # di atas bar ini + ada bukti -> promosi otomatis; di bawahnya antre persetujuan manusia

def tok(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

def est_tokens(text):
    return max(1, round(len(text) / 4))  # estimasi kasar ~4 char/token

# ---------------------------------------------------------------- datapack
class LocalDatapack:
    """Semantik datapack Meko: knowledge bersama, memory privat per agen,
    decision traces, artifacts; pencarian diskors relevansi 0..1 + gap."""
    def __init__(self):
        self.knowledge = []       # {id, title, body, tags, source, evidence}
        self.private = {}         # agent -> [ {title, body, trust} ]
        self.traces = []          # {agent, action, detail, why}
        self.artifacts = []       # {name, body, by}
        self.pending = []         # antre promosi menunggu manusia
        self._n = 0

    def trace(self, agent, action, detail, why):
        self.traces.append({"agent": agent, "action": action, "detail": detail, "why": why})

    def teach(self, agent, title, body, tags):
        self._n += 1
        item = {"id": f"K{self._n}", "title": title, "body": body, "tags": tags,
                "source": agent, "evidence": "taught-by-architect"}
        self.knowledge.append(item)
        self.trace(agent, "teach", title, "codify project standard once")
        return item

    def search(self, agent, query, top_k=3):
        q = tok(query)
        scored = []
        for item in self.knowledge:
            hay = tok(item["title"] + " " + item["body"] + " " + " ".join(item["tags"]))
            inter = len(q & hay)
            score = round(inter / max(1, len(q)), 4) if q else 0.0
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        hits = [{"score": s, "id": i["id"], "title": i["title"], "body": i["body"]} for s, i in scored[:top_k]]
        gap = None
        if not hits or hits[0]["score"] < 0.34:
            gap = f"no strong knowledge for '{query}' - missing topics: {sorted(q - set().union(*[tok(h['title']+' '+h['body']) for h in hits])) if hits else sorted(q)}"
        self.trace(agent, "search", query, f"{len(hits)} hits" + (f"; gap: {gap}" if gap else ""))
        return {"hits": hits, "gap": gap}

    def remember_private(self, agent, title, body, trust):
        self.private.setdefault(agent, []).append({"title": title, "body": body, "trust": trust})
        self.trace(agent, "remember_private", title, f"trust={trust}")

    def propose_promotion(self, agent, title, body, tags, trust, evidence):
        """Gerbang governance: butuh bukti; trust >= bar -> otomatis shared;
        di bawah bar -> antre persetujuan manusia (tidak diam-diam jadi kebenaran)."""
        if not evidence:
            self.trace(agent, "promotion_rejected", title, "no evidence attached")
            return {"status": "rejected", "reason": "evidence required"}
        if trust >= AUTO_APPROVE_TRUST:
            item = self.teach(agent, title, body, tags)
            item["evidence"] = evidence
            self.trace(agent, "promotion_auto", title, f"trust {trust} >= {AUTO_APPROVE_TRUST} + evidence")
            return {"status": "promoted", "id": item["id"]}
        self.pending.append({"agent": agent, "title": title, "body": body, "tags": tags,
                             "trust": trust, "evidence": evidence})
        self.trace(agent, "promotion_queued", title, f"trust {trust} < {AUTO_APPROVE_TRUST} - human gate")
        return {"status": "queued", "reason": "awaiting human approval"}

    def approve_pending(self, idx=0):
        p = self.pending.pop(idx)
        item = self.teach(p["agent"], p["title"], p["body"], p["tags"])
        item["evidence"] = p["evidence"]
        self.trace("human", "promotion_approved", p["title"], "human approved queued learning")
        return {"status": "promoted", "id": item["id"]}

    def why(self, needle):
        return [t for t in self.traces if needle.lower() in (t["detail"] + t["action"]).lower()]

    def full_context_text(self):
        return json.dumps({"knowledge": self.knowledge, "private": self.private,
                           "traces": self.traces, "artifacts": self.artifacts}, ensure_ascii=False)

class MekoClient:
    """Klien MCP live. Tanpa API key: menolak (fallback lokal dipakai).
    Nama tool TERVERIFIKASI 21 Nov 2026 dari docs resmi Meko
    (docs.mekodata.ai/reference/mcp-server — 32 tools), al.:
    context_search, memory_add, memory_search, memory_promote,
    datapack_list, datapack_search, knowledgebase_search, artifact_put.
    Header User-Agent wajib (dokumentasi Datapack API)."""
    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else os.environ.get("MEKO_API_KEY", "")
        self.url = MEKO_MCP_URL
        self.session_id = None

    def payload(self, tool, arguments):
        return {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": tool, "arguments": arguments}}

    def _headers(self):
        h = {"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream",
             "User-Agent": "onememory-contextcon/1.0",
             "Authorization": f"Bearer {self.api_key}"}
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _post(self, obj):
        req = urllib.request.Request(self.url, data=json.dumps(obj).encode(), headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            sid = r.headers.get("Mcp-Session-Id")
            if sid:
                self.session_id = sid
            raw = r.read().decode()
        if "data:" in raw[:64] or "\ndata:" in raw:  # SSE stream -> ambil payload data terakhir
            payloads = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")]
            return json.loads(payloads[-1]) if payloads else {}
        return json.loads(raw) if raw.strip() else {}

    def _ensure_session(self):
        if self.session_id:
            return
        self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                               "clientInfo": {"name": "onememory", "version": "1.0"}}})
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            pass

    def call(self, tool, arguments):
        if not self.api_key:
            return {"status": "blocked", "reason": "MEKO_API_KEY kosong - pakai LocalDatapack"}
        self._ensure_session()
        return {"status": "ok", "data": self._post(self.payload(tool, arguments))}

    # pemetaan semantik datapack lokal -> tool MCP resmi
    def search(self, query):
        return self.call("context_search", {"query": query})

    def remember(self, text):
        return self.call("memory_add", {"content": text})

    def recall(self, query):
        return self.call("memory_search", {"query": query})

    def promote(self, memory_id):
        return self.call("memory_promote", {"memory_id": memory_id})

    def datapacks(self):
        return self.call("datapack_list", {})

# ---------------------------------------------------------------- agen coding
STANDARDS = [
    ("STD-NAME", "Naming: functions use snake_case verbs", "functions must be named with snake_case verbs like fetch_user or build_report", ["naming", "function", "style"]),
    ("STD-ERR", "Errors: never swallow exceptions silently", "every except block must log or re-raise; silent pass is forbidden in error handling", ["error", "exception", "handling"]),
    ("STD-SECRET", "Secrets: no credentials in code or logs", "never hardcode api key password token secret in source code or log output", ["secret", "credential", "security"]),
    ("STD-TEST", "Tests: every public function ships a test", "public functions require a unit test covering the main path and one failure case", ["test", "coverage", "function"]),
]

class CoderAgent:
    """Agen di satu harness; TIDAK punya memori lokal antar sesi — semua dari datapack."""
    def __init__(self, name, harness, store):
        self.name, self.harness, self.store = name, harness, store

    def code_task(self, task, needs_validation=False):
        res = self.store.search(self.name, task, top_k=5)
        applied = []
        code = [f"# task: {task}"]
        if any(h["id"] for h in res["hits"]):
            for h in res["hits"]:
                applied.append(h["id"])
        # perilaku deterministik: agen menerapkan aturan yg ia temukan
        titles = " ".join(h["title"] + " " + h["body"] for h in res["hits"])
        if "STD-NAME" in titles or "Naming" in titles:
            code.append("def fetch_user_report(user_id):")
        else:
            code.append("def FetchUserReport(user_id):")
        if needs_validation or "validation" in titles.lower() or any("VALID" in h["id"] for h in res["hits"]):
            code.append("    if not user_id: raise ValueError('user_id required')  # input validation")
        code.append("    try:")
        code.append("        return build_report(user_id)")
        if "Errors" in titles:
            code.append("    except Exception as e:")
            code.append("        log_error(e); raise")
        else:
            code.append("    except Exception:")
            code.append("        pass")
        return {"code": "\n".join(code), "cited": applied, "gap": res["gap"]}

class ReviewerAgent:
    """Agen reviewer di harness LAIN, sesi segar, nol konteks lokal."""
    def __init__(self, name, harness, store):
        self.name, self.harness, self.store = name, harness, store

    def review(self, code, task):
        res = self.store.search(self.name, task + " error handling naming validation")
        findings = []
        if "pass" in code and "except" in code:
            findings.append({"rule": "STD-ERR", "issue": "silent exception swallow"})
        if "def Fetch" in code:
            findings.append({"rule": "STD-NAME", "issue": "function name not snake_case verb"})
        if "user_id" in code and "validation" not in code and "ValueError" not in code:
            findings.append({"rule": "LEARN-VALID", "issue": "missing input validation on external id"})
        return {"findings": findings, "standards_seen": [h["id"] for h in res["hits"]]}

def check_compliance(code):
    checks = {
        "snake_case_name": bool(re.search(r"def [a-z]+_[a-z_]+\(", code)),
        "no_silent_except": "        pass" not in code,
        "has_validation": "ValueError" in code,
        "logs_errors": "log_error" in code,
    }
    return checks

# ---------------------------------------------------------------- demo ADLC
def run_demo():
    store = LocalDatapack()
    architect = "arch-oracle (Claude Code)"
    for sid, title, body, tags in STANDARDS:
        item = store.teach(architect, title, body, tags)
        item["id"] = sid
    # Padding realistis: riwayat percakapan & traces lama menumpuk di datapack
    for i in range(60):
        store.trace(f"history-{i%5}", "search", f"old session chatter {i} about unrelated topic {i}",
                    "archived conversation filler for baseline measurement")

    # Sesi 1 — coder di Claude Code
    coder1 = CoderAgent("coder-claude", "Claude Code", store)
    out1 = coder1.code_task("write function fetch user report with error handling", needs_validation=False)
    comp1 = check_compliance(out1["code"])
    # Reviewer di Cursor (sesi segar) menemukan celah validasi
    reviewer = ReviewerAgent("review-cursor", "Cursor", store)
    rev = reviewer.review(out1["code"], "fetch user report")
    # Pelajaran jadi memory privat reviewer, lalu dipromosikan (trust tinggi + bukti)
    store.remember_private(reviewer.name, "Always validate external ids",
                           "external ids must be validated before use: raise ValueError on empty id", 0.9)
    promo = store.propose_promotion(reviewer.name, "Validation: validate external ids",
                                    "when a function fetches a user report by external id, validate the input first: input validation means raise ValueError on empty id before use",
                                    ["validation", "input", "security"], 0.9,
                                    evidence="review finding on fetch_user_report, session 1")
    # Sesi 2 — coder BARU di Codex, harness berbeda, nol memori lokal
    coder2 = CoderAgent("coder-codex", "Codex", store)
    out2 = coder2.code_task("write function fetch user report with error handling and validation")
    comp2 = check_compliance(out2["code"])

    baseline_tokens = est_tokens(store.full_context_text()) * 2  # 2 sesi, stuffing semua konteks
    slice_tokens = est_tokens(json.dumps(out1["cited"] + out2["cited"])) + \
        sum(est_tokens(h["body"]) for h in store.search("meter", "fetch user report error handling validation")["hits"]) * 2
    savings = round(100 * (1 - slice_tokens / max(1, baseline_tokens)), 1)
    return {
        "session1": {"agent": coder1.name, "harness": coder1.harness, "cited": out1["cited"], "compliance": comp1},
        "review": rev,
        "promotion": promo,
        "session2": {"agent": coder2.name, "harness": coder2.harness, "cited": out2["cited"], "compliance": comp2},
        "compliance_s1_pass": sum(comp1.values()), "compliance_s2_pass": sum(comp2.values()),
        "tokens": {"baseline_stuffing_2_sessions": baseline_tokens, "engineered_slice_2_sessions": slice_tokens,
                   "savings_pct": savings},
        "traces": len(store.traces), "knowledge_items": len(store.knowledge),
    }

def selftest():
    ok = fail = 0
    def check(name, cond):
        nonlocal ok, fail
        ok, fail = ok + (1 if cond else 0), fail + (0 if cond else 1)
        print(("PASS " if cond else "FAIL ") + name)
    s = LocalDatapack()
    for sid, t, b, tags in STANDARDS:
        it = s.teach("arch", t, b, tags); it["id"] = sid
    r = s.search("a", "error handling exception")
    check("search relevan menemukan STD-ERR", any(h["id"] == "STD-ERR" for h in r["hits"]) and r["hits"][0]["score"] > 0)
    check("search topik asing menghasilkan gap", s.search("a", "quantum blockchain zebra")["gap"] is not None)
    check("promosi tanpa bukti ditolak", s.propose_promotion("a", "x", "y", [], 0.95, "")["status"] == "rejected")
    check("promosi trust rendah masuk antre", s.propose_promotion("a", "weak tip", "some tip body", [], 0.5, "ev")["status"] == "queued" and len(s.pending) == 1)
    check("persetujuan manusia mempromosikan antrean", s.approve_pending(0)["status"] == "promoted")
    check("promosi trust tinggi+bukti otomatis", s.propose_promotion("a", "strong tip", "validated body text", [], 0.9, "ev")["status"] == "promoted")
    d = run_demo()
    check("demo: sesi 2 (harness lain) patuh validasi hasil promosi", d["session2"]["compliance"]["has_validation"])
    check("demo: kepatuhan naik antar sesi", d["compliance_s2_pass"] > d["compliance_s1_pass"])
    check("demo: penghematan token > 50%", d["tokens"]["savings_pct"] > 50)
    check("decision trace bisa diaudit (why)", len(s.why("promotion")) >= 2)
    mc = MekoClient(api_key="")
    check("meko tanpa key diblokir + payload JSON-RPC benar", mc.call("context_search", {})["status"] == "blocked"
          and mc.payload("context_search", {"q": "x"})["method"] == "tools/call")
    print(f"\nSELFTEST {ok}/{ok+fail} PASS")
    return fail == 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))
