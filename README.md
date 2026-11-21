# OneMemory — One Memory, Every Coding Agent

**ContextCon (HackerEarth × YugabyteDB) · Theme 01: Coding Agents & ADLC**
*Teach the standard once. Every coding agent follows it.*

## The problem (from the official brief)

Coding agents start every session cold. They re-derive your team's standards,
repeat last week's mistakes, and keep what they learn in a local markdown file
that no other agent can read. Claude Code learns a rule on Monday; Cursor
violates it on Tuesday; Codex never hears about it.

## The solution

One shared **Meko datapack** holds the project's conversations, memories,
knowledge, decision traces and artifacts behind a single MCP endpoint.
Every coding agent — any harness — works from the same memory:

1. **Codify once** — an architect agent teaches the project standards
   (naming, error handling, secrets, tests) into the datapack one time.
2. **Work across tools** — a coder in Claude Code retrieves only the relevant,
   relevance-scored slice, writes code that follows it, and **cites the rule
   IDs it applied**.
3. **Learn once, apply everywhere** — a reviewer in Cursor finds a gap
   (missing input validation). The lesson starts as *private memory*, is
   proposed for promotion with evidence attached, and passes a **governance
   gate**: trust ≥ 0.80 + evidence → auto-promoted; below the bar → queued
   for a human. A brand-new coder in **Codex** — different harness, zero local
   memory — then retrieves the promoted rule and complies with it.
4. **Run the lifecycle** — every search, teach, promotion and review is a
   decision trace: any action can be audited with *"why did the agent do that?"*

## Measured results (deterministic demo, `data/demo-output.json`)

| Metric | Session 1 (Claude Code) | Session 2 (Codex, fresh) |
|---|---|---|
| Standards compliance | 3/4 | **4/4** (incl. the promoted validation rule, cited as `K5`) |
| Context tokens per 2 sessions | 6,604 (stuff-everything baseline) | **171 (engineered slice) → 97.4% fewer** |

## Run it

```bash
python3 onememory.py --selftest   # 11/11 checks
python3 onememory.py --demo       # full ADLC story as JSON
```

No dependencies (Python stdlib), no paid APIs, no LLM required for the demo —
agents are deterministic so compliance and token numbers are verifiable.

## Live Meko mode — VERIFIED 21 Nov 2026

`MekoClient` speaks MCP JSON-RPC (streamable HTTP, session handshake) to
`https://mcp.mekodata.ai/mcp`, using the official tool names from Meko's docs
(57 tools listed by the server). `live_test.py` ran the full cycle against the
real account and passed **6/6**: `conversation_create` → `datapack_list`
(real datapack found) → `memory_add` (STD-ERR stored) → `memory_search`
(same memory retrieved) → `context_search` (retrieved via context) →
`memory_promote` (promoted, `inserted_ids` returned). Results recorded in
`data/live-test.json` and `data/mcp-tools.json`.

To reproduce: put `MEKO_API_KEY=<your key>` in a local `.env` (git-ignored,
mode 0600) and run `python3 live_test.py`. Without a key the client refuses
and the local datapack — same semantics: relevance-scored search (0–1) with
gap explanation, private→shared promotion, decision traces — is used, so the
project is fully demoable offline.

## Layout

- `onememory.py` — datapack (local + Meko MCP client), governance gate, agents, ADLC demo, selftest
- `ARCHITECTURE.md` — design, Meko feature mapping, judging-criteria mapping
- `SUBMISSION.md` — submission checklist + demo video script (<5 min)
- `data/demo-output.json` — recorded demo run
