# homi-gate

Agent CI often stays green while the run is truncated, the next worker gets `context: null`, or MCP exposes every tool. Those are contract failures. They do not need an LLM judge.

**homi-gate** is a thin, fail-closed CLI: four deterministic checks, exit `0` or `1`, no model in the loop.

1. **Completion bit** — truncated / incomplete receipts fail  
2. **Handoff contract** — null context and missing stop fields fail  
3. **MCP allowlist** — “enable the whole server” shapes fail  
4. **Tool correctness** *(field-remix)* — `tools_called` vs `expected_tools`, wrong-tool=0  

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
homi-gate check-tools examples/tools_ok.json
```

Should fail (exit `1`, reasons on stderr):

```bash
homi-gate check-completion examples/fail.json
homi-gate check-completion examples/soft_done_no_artifact.json
homi-gate check-completion examples/doppelganger.jsonl
homi-gate check-handoff examples/handoff_bad.json
homi-gate check-handoff examples/handoff_transcript_dump.json
homi-gate check-mcp-allowlist examples/mcp_bad.yaml
homi-gate check-tools examples/tools_wrong.json
homi-gate check-tools examples/tools_missing.json
```

Also covered: `examples/pass.jsonl`, `examples/mcp_disabled_ok.yaml` (explicitly disabled MCP + named tools), `examples/tools_*.json` (field-remix tool correctness).

### What each check asserts

| Command | Pass when | Fail when |
|---------|-----------|-----------|
| `check-completion` | complete claim (`completion_bit`/`complete` or known `status`) **plus** artifact/proof path | soft DONE (no proof path) / `truncated: true` / mid-stream truncate before green final / missing bit+status |
| `check-handoff` | required fields present and non-null; exactly one `pending` | `context: null`; missing `stop` / `proved` / … |
| `check-mcp-allowlist` | allowlist **and** denylist, **or** `enabled: false` with named tools | open “enable whole server” shape |
| `check-tools` | `tools_called` names match `expected_tools` set (optional `--exact-args`) | unexpected tool / missing required / empty expected when claim asserts tools |

Handoff required fields: `from_agent`, `to_agent`, `proved`, `pending`, `stop`, `forbidden`, `report` (aliases `from` / `to` accepted). Receipts may be JSON, a JSON list, or JSONL. Completion still inspects the final record for bit/status/artifact, but mid-stream `truncated: true` stream-vetoes a later green final (see `examples/doppelganger.jsonl`).

## CI

Wire into any repo:

```yaml
- run: pip install -e ".[dev]"
- run: pytest -q
- run: |
    homi-gate check-completion path/to/receipt.json
    homi-gate check-handoff path/to/handoff.json
    homi-gate check-mcp-allowlist path/to/mcp.yaml
    homi-gate check-tools path/to/tools-receipt.json
```

This repository’s workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Composition

Use this **beside** full eval stacks (Promptfoo, DeepEval, Ragas, judge harnesses). Those score quality and trajectories. This only fails closed on completion, handoff, MCP, and tool-call contract shapes. It does not replace Stop-hook tools, LangSmith, or human review.

### Optional: Promptfoo quality evals (beside Homi Gate)

Contracts stay here. For prompt/agent **quality** in CI, add Promptfoo with **deterministic** asserts (`not-contains` / `is-json` / trajectory tool checks) and `--fail-on-error` — never LLM-rubric alone for green. See Promptfoo [CI/CD](https://www.promptfoo.dev/docs/integrations/ci-cd/) + [asserts](https://www.promptfoo.dev/docs/configuration/expected-outputs/). Companion trajectory match: LangChain AgentEvals (Course 031).

Then still run Homi Gate on receipts (completion · handoff · MCP).



### Field-remix: `check-tools` (wrong-tool=0)

Deterministic `tools_called` vs `expected_tools` — names-only by default, optional `--exact-args`. Exit `0`/`1`, **no LLM in the loop**. Soft-DONE still fails if judge-alone.

Public pattern sources (FN-ENGINE2):

- [Promptfoo — Mock Tool Execution / hermetic `toolMocks`](https://www.promptfoo.dev/docs/providers/openai-agents/)
- [DeepEval — ToolCorrectnessMetric (det-first)](https://deepeval.com/docs/metrics-tool-correctness)

Evals measure; gates authorize. This check is the gate slice of those field tactics — not a full eval framework.

## Non-goals

- Not a full eval framework  
- Not an LLM-as-judge or judge calibrator  
- Not a RAG scorer  
- Not a hosted SaaS / observability platform  
- Not a substitute for human review on regulated paths  

## Falsifier

If a weekend clone does **not** catch a truncated run, a null handoff, an open MCP config, and a wrong-tool receipt in `examples/`, treat the wedge as dead and open an issue.

## Roadmap

- JSON Schema exports + optional SARIF for PR annotations  
- More receipt dialects (Agents SDK / LangGraph slices)  
- ~~wrong-tool=0 from tool-call receipts~~ → shipped as `check-tools` (field-remix)

Build-in-public drafts (manual post only): [CONTENT/FOLLOWERS.md](CONTENT/FOLLOWERS.md).

## License

MIT — [LICENSE](LICENSE).

## Safety

Examples are public/synthetic. No secrets. Nothing in `CONTENT/` is auto-published.
