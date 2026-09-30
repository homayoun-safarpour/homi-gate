# homi-gate

Fail-closed CI checks for agent pipelines.

Three asserts that should be red before merge:

1. **Completion bit** — a truncated or incomplete run is not a pass  
2. **Handoff contract** — `context: null` and missing stop fields fail  
3. **MCP allowlist** — wide-open tool surfaces fail  

Deterministic. Exit `0` / `1`. No LLM in the loop.

[Why these three](docs/MARKET.md) · MIT license

---

## Install

```bash
pip install -e ".[dev]"
# or
PYTHONPATH=src python -m homi_gate --help
```

Python ≥ 3.11.

## Quick start

```bash
# should pass
homi-gate check-completion examples/pass.json
homi-gate check-handoff examples/handoff_ok.json
homi-gate check-mcp-allowlist examples/mcp_ok.yaml

# should fail (exit 1, reasons on stderr)
homi-gate check-completion examples/fail.json
homi-gate check-handoff examples/handoff_bad.json
homi-gate check-mcp-allowlist examples/mcp_bad.yaml
```

### What each check asserts

| Command | Pass when | Fail when |
|---------|-----------|-----------|
| `check-completion` | `completion_bit: true` or a known complete `status` | `truncated: true` / incomplete status |
| `check-handoff` | required fields present and non-null; one `pending` | `context: null`; missing `stop` / `proved` / … |
| `check-mcp-allowlist` | allowlist + denylist, **or** `enabled: false` + named tools | open “enable whole server” shape |

Handoff required fields: `from_agent`, `to_agent`, `proved`, `pending`, `stop`, `forbidden`, `report` (aliases `from` / `to` accepted).

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

## Non-goals

- Not a full eval framework (DeepEval / Ragas / Promptfoo territory)  
- Not an LLM-as-judge  
- Not a RAG scorer  
- Not a substitute for human review on regulated paths  

If a weekend clone does **not** catch a truncated run, a null handoff, and an open MCP config in the examples, treat the wedge as dead and open an issue.

## Roadmap

- JSON Schema exports + optional SARIF for PR annotations  
- More receipt dialects (Agents SDK / LangGraph slices)  
- wrong-tool=0 counter from tool-call logs (still det asserts, not scores)

Build-in-public drafts (manual post only): [CONTENT/FOLLOWERS.md](CONTENT/FOLLOWERS.md).

## License

MIT — [LICENSE](LICENSE).

## Safety

Examples are public/synthetic. No secrets. Nothing in `CONTENT/` is auto-published.
