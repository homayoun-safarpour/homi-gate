# Market need — Ireland/EU hire signals → homi-gate

Public JD mirrors + careers pages (Dublin / Ireland / EU-hiring remote), skimmed 2026-09. Skill tags that gate interviews — not toolkit logos.

## What live JDs actually ask for

1. **Eval harness + CI release gates**  
   Regression suites and green/red quality gates before ship. “Owned the eval harness.” “Eval as engineering” + release gates. Automated retrieval / agent-behavior metrics.

2. **MCP / tool contracts — wrong-tool = 0**  
   MCP or MCP-style tool protocols in production. Idempotent orchestration. Named tools, not “whatever the model picks.”

3. **Completion ≠ satisfaction**  
   Agents that stop. HITL checkpoints. Agentic-behavior eval. A run that truncates mid-tool is not a successful completion — the receipt must carry a completion bit.

4. **Handoff context: null**  
   Multi-agent / failover paths need compact handoffs (`proved` | `pending=<one>` | `stop` | `forbidden` | `report`). `context: null` plus a transcript dump is the anti-pattern that burns the next worker.

5. **Gates with numbers / asserts**  
   Sell the red CI bar and the count (unsupported=0, wrong-tool=0, truncated=false). Do not treat a framework name as proof of hire-ready skill.

## How homi-gate maps

| Signal | Gate command | Fail-closed assert |
|--------|--------------|--------------------|
| Agents that stop | `check-completion` | `completion_bit` / complete status; `truncated≠true` |
| Compact handoff | `check-handoff` | required fields non-null; no `context:null`; one `pending` |
| MCP wrong-tool=0 shape | `check-mcp-allowlist` | allowlist+denylist, or `enabled:false` + named tools |

## What this is not

- Not a full eval framework.
- Not a RAG scorer.
- Not a substitute for human review on regulated paths.
- Not auto-publish / not a LinkedIn bot.

It is the thin CI layer that turns “we care about evals / MCP / stop” into merge blockers.
