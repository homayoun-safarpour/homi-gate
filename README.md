# homi-gate

Agent CI often stays green while the run is truncated, the next worker gets `context: null`, or MCP exposes every tool. Those are contract failures. They do not need an LLM judge.

**homi-gate** is a thin, fail-closed CLI: three deterministic checks, exit `0` or `1`, no model in the loop.

1. **Completion bit** — truncated / incomplete receipts fail  
2. **Handoff contract** — null context and missing stop fields fail  
3. **MCP allowlist** — “enable the whole server” shapes fail  

[Why these three](docs/MARKET.md) · MIT

---

## Install

Python ≥ 3.11. From this repo:

```bash
pip install -e ".[dev]"
homi-gate --help
```

Or without installing:

```bash
PYTHONPATH=src python -m homi_gate --help
```

No API key. Offline.

## Quick start

Should pass:

```bash
homi-gate check-completion examples/pass.json
homi-gate check-handoff examples/handoff_ok.json
homi-gate check-mcp-allowlist examples/mcp_ok.yaml
```

Should fail (exit `1`, reasons on stderr):

```bash
homi-gate check-completion examples/fail.json
homi-gate check-handoff examples/handoff_bad.json
homi-gate check-mcp-allowlist examples/mcp_bad.yaml
```

Also covered: `examples/pass.jsonl`, `examples/mcp_disabled_ok.yaml` (explicitly disabled MCP + named tools).

### What each check asserts

| Command | Pass when | Fail when |
|---------|-----------|-----------|
| `check-completion` | `completion_bit: true` (or `complete: true`), or a known complete `status` | `truncated: true` / incomplete status / missing bit+status |
| `check-handoff` | required fields present and non-null; exactly one `pending` | `context: null`; missing `stop` / `proved` / … |
| `check-mcp-allowlist` | allowlist **and** denylist, **or** `enabled: false` with named tools | open “enable whole server” shape |

Handoff required fields: `from_agent`, `to_agent`, `proved`, `pending`, `stop`, `forbidden`, `report` (aliases `from` / `to` accepted). Receipts may be JSON, a JSON list, or JSONL (final record wins for completion).

## CI

Wire into any repo:

```yaml
- run: pip install -e ".[dev]"
- run: pytest -q
- run: |
    homi-gate check-completion path/to/receipt.json
    homi-gate check-handoff path/to/handoff.json
    homi-gate check-mcp-allowlist path/to/mcp.yaml
```

This repository’s workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Composition

Use this **beside** full eval stacks (Promptfoo, DeepEval, Ragas, judge harnesses). Those score quality and trajectories. This only fails closed on completion, handoff, and MCP contract shapes. It does not replace Stop-hook tools, LangSmith, or human review.

## Non-goals

- Not a full eval framework  
- Not an LLM-as-judge or judge calibrator  
- Not a RAG scorer  
- Not a hosted SaaS / observability platform  
- Not a substitute for human review on regulated paths  

## Falsifier

If a weekend clone does **not** catch a truncated run, a null handoff, and an open MCP config in `examples/`, treat the wedge as dead and open an issue.

## Roadmap

- JSON Schema exports + optional SARIF for PR annotations  
- More receipt dialects (Agents SDK / LangGraph slices)  
- wrong-tool=0 counter from tool-call logs (still deterministic asserts, not scores)

Build-in-public drafts (manual post only): [CONTENT/FOLLOWERS.md](CONTENT/FOLLOWERS.md).

## License

MIT — [LICENSE](LICENSE).

## Safety

Examples are public/synthetic. No secrets. Nothing in `CONTENT/` is auto-published.
