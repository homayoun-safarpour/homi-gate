# homi-gate

**CI stays green while the agent run was truncated, the handoff is null, or MCP exposed every tool. This fails those three.**

Homayoun Safarpour

[![CI](https://github.com/homayoun-safarpour/homi-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/homayoun-safarpour/homi-gate/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Fail-closed CI checks for truncated agent runs, null handoffs, and open MCP tools.

```bash
git clone https://github.com/homayoun-safarpour/homi-gate
cd homi-gate && pip install -e .
homi-gate check-completion examples/fail.json
```

It exits 1. Real output:

```
FAIL check-completion: examples/fail.json
  - truncated=true on final record
  - completion_bit=false
```

---

## The three checks

No model in the loop. Exit `0` or `1`.

| Command | Pass when | Fail when |
| --- | --- | --- |
| `check-completion` | `completion_bit: true` (or `complete: true`), or a known complete `status` | `truncated: true` / incomplete status / missing bit+status |
| `check-handoff` | required fields present and non-null; exactly one `pending` | `context: null`; missing `stop` / `proved` |
| `check-mcp-allowlist` | allowlist **and** denylist, **or** `enabled: false` with named tools | open "enable whole server" shape |

Handoff required fields: `from_agent`, `to_agent`, `proved`, `pending`, `stop`, `forbidden`, `report` (aliases `from` / `to` accepted). Receipts may be JSON, a JSON list, or JSONL (final record wins for completion).

Should pass:

```bash
homi-gate check-completion examples/pass.json
homi-gate check-handoff examples/handoff_ok.json
homi-gate check-mcp-allowlist examples/mcp_ok.yaml
```

Should fail (exit `1`, reasons on stderr):

```bash
homi-gate check-handoff examples/handoff_bad.json
homi-gate check-mcp-allowlist examples/mcp_bad.yaml
```

Also covered: `examples/pass.jsonl`, `examples/mcp_disabled_ok.yaml` (explicitly disabled MCP + named tools).

## CI

```yaml
- run: pip install -e ".[dev]"
- run: pytest -q
- run: |
    homi-gate check-completion path/to/receipt.json
    homi-gate check-handoff path/to/handoff.json
    homi-gate check-mcp-allowlist path/to/mcp.yaml
```

This repository's workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Composition

Use this beside full eval stacks (Promptfoo, DeepEval, Ragas, judge harnesses). Those score quality and trajectories. This only fails closed on completion, handoff, and MCP contract shapes. It does not replace Stop-hook tools, LangSmith, or human review.

Contracts stay here. For prompt/agent quality in CI, add Promptfoo with deterministic asserts (`not-contains` / `is-json` / trajectory tool checks) and `--fail-on-error`. Never LLM-rubric alone for green.

## Non-goals

- Not a full eval framework
- Not an LLM-as-judge or judge calibrator
- Not a RAG scorer
- Not a hosted SaaS / observability platform
- Not a substitute for human review on regulated paths

## Falsifier

If a weekend clone does not catch a truncated run, a null handoff, and an open MCP config in `examples/`, treat the wedge as dead and open an issue.

## License

MIT. See [LICENSE](LICENSE).

## Safety

Examples are public/synthetic. No secrets. Nothing in `CONTENT/` is auto-published.
