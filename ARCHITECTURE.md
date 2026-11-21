# Architecture — OneMemory

## Flow (one ADLC loop)

```
TEACH      Architect agent ──teach──▶ ┌──────────────────────────────┐
                                      │  MEKO DATAPACK (one memory)  │
CODE       Coder (Claude Code) ──search(relevance-scored)──▶ slice  │
           writes code + cites rule IDs                            │
REVIEW     Reviewer (Cursor, fresh session) ──search──▶ standards  │
           finding → PRIVATE memory (agent-scoped)                 │
LEARN      propose promotion + evidence ──▶ GOVERNANCE GATE        │
             trust ≥ 0.80 & evidence → auto-promote to SHARED      │
             trust < 0.80 → human approval queue                   │
APPLY      Coder (Codex, different harness, zero local memory)     │
           retrieves promoted rule → complies → cites it           │
AUDIT      every step = decision trace → "why?" query              │
                                      └──────────────────────────────┘
```

## Meko features used (brief mapping)

| Meko capability | Where OneMemory uses it |
|---|---|
| Datapack (conversations, memory, knowledge, traces, artifacts in one governed environment) | The single shared store behind all agents; local fallback mirrors the same shape |
| Single MCP endpoint | `MekoClient` → `https://mcp.mekodata.ai/mcp` (JSON-RPC `tools/call`, Bearer API key) |
| Relevance-scored retrieval + gap explanation | `search()` returns 0–1 scores and an explicit "missing topics" gap when recall is weak |
| Private-by-default memory, promotion with approval | `remember_private()` → `propose_promotion()` gate (evidence required; trust bar 0.80; human queue below it) |
| Decision traces | `trace()` on teach/search/promote/review; `why(needle)` audit query |
| Cross-tool sharing (Claude / Cursor / Codex) | Three simulated harnesses share one datapack; session 2's compliance gain comes only from the shared store |
| Engineered context (small relevant slice, not stuffing) | Token metering: 6,604 → 171 tokens for two sessions in the demo (−97.4%) |

## Design decisions

- **Code decides what persists, not the model.** Promotion rules are code:
  evidence is mandatory, the trust bar is a constant, and nothing becomes
  shared knowledge silently — mirroring Meko's "agents discover, humans govern".
- **Citations are compliance.** Agents return the rule IDs they applied, so a
  reviewer (or a judge) can verify *which* shared memory shaped the output.
- **Deterministic demo.** Simulated agents make the before/after measurable
  (3/4 → 4/4 compliance) and the selftest reproducible (11/11) without any
  paid LLM call. Live mode swaps the store, not the story.
- **Honest limits.** Tool names on the live MCP endpoint must be re-verified
  against the Meko Connect page once an API key exists; until then live calls
  are blocked by design rather than faked.

## Judging criteria mapping (published weights)

- **Use of Meko (30%)** — datapack as the only memory; MCP endpoint; scored
  retrieval with gaps; governed promotion; decision traces.
- **Impact & Usefulness (25%)** — kills the "each agent relearns the rules"
  tax for any team using ≥2 coding tools; measured compliance + token gains.
- **Technical Execution (20%)** — stdlib-only, selftest 11/11, demo output
  recorded in `data/demo-output.json`, offline-runnable.
- **Innovation (15%)** — promotion gate with trust bar + evidence as a
  code-review-like process for agent memory; citation-based compliance.
- **Presentation (10%)** — 5-minute video script in `SUBMISSION.md` following
  the exact ADLC loop the demo executes.
