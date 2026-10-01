# homi-gate

Agent CI often stays green while the run is truncated, the next worker gets `context: null`, or MCP exposes every tool. Those are contract failures. They do not need an LLM judge.

**homi-gate** is a thin, fail-closed CLI: five deterministic checks, exit `0` or `1`, no model in the loop.

1. **Completion bit** — truncated / incomplete receipts fail  
2. **Handoff contract** — null context and missing stop fields fail  
3. **MCP allowlist** — “enable the whole server” shapes fail  
4. **Tool correctness** *(field-remix-1)* — `tools_called` vs `expected_tools`, wrong-tool=0  
5. **Spans / two-zero** *(field-remix-3 / A2E)* — OTel-style parent→tool spans + early-stall vs late-malform split  

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
homi-gate check-spans examples/span_ok.json
homi-gate check-spans --two-zero examples/zero_early_stall.json examples/zero_late_tool_malform.json
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
homi-gate check-spans examples/span_missing_tool.json
homi-gate check-spans examples/tool_malform.json
```

Also covered: `examples/pass.jsonl`, `examples/mcp_disabled_ok.yaml` (explicitly disabled MCP + named tools), `examples/tools_*.json` (field-remix-1), `examples/span_*.json` + `examples/zero_*.json` + `examples/tool_malform.json` (field-remix-3 / A2E).

### What each check asserts

| Command | Pass when | Fail when |
|---------|-----------|-----------|
| `check-completion` | complete claim (`completion_bit`/`complete` or known `status`) **plus** artifact/proof path | soft DONE (no proof path) / `truncated: true` / mid-stream truncate before green final / missing bit+status |
| `check-handoff` | required fields present and non-null; exactly one `pending` | `context: null`; missing `stop` / `proved` / … |
| `check-mcp-allowlist` | allowlist **and** denylist, **or** `enabled: false` with named tools | open “enable whole server” shape |
| `check-tools` | `tools_called` names match `expected_tools` set (optional `--exact-args`) | unexpected tool / missing required / empty expected when claim asserts tools |
| `check-spans` | A1 parent+tool child (name+status); A2 tool status∈{ok,error,denied}+args object; A3 `--two-zero` discriminates early stall vs late malform | missing tool span / malformed invocation / identical correctness=0 theater |

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
    homi-gate check-spans path/to/span-tree.json
    homi-gate check-spans --two-zero path/to/zero_early.json path/to/zero_late.json
```

This repository’s **det** workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml) — pytest + every `check-*` on pass fixtures **and** fail-fixture smokes (`!` invert → exit 1 expected).

### Two-speed CI (field-remix-2 / Autonoma)

| Lane | When | What | ACCEPT? |
|------|------|------|---------|
| **Det** | every PR / push | `pytest` + `homi-gate check-*` exit codes | Yes — authorize stop |
| **Soft** | merge / nightly optional | LLM / judge companion (stub: [soft-lane.yml](.github/workflows/soft-lane.yml)) | **Never alone** |

Pattern from [Autonoma — How to run LLM evals in CI/CD](https://getautonoma.com/blog/how-to-run-llm-evals-in-ci-cd) (det every commit; evals merge + nightly). Homi map: det = `check-*`; soft = optional companion. **PAPER-032**: soft / judge never ACCEPT alone.

**Falsifier:** skip-when-no-key still green = theater. The soft stub is `workflow_dispatch` only, `continue-on-error: false`, and **exits 1** when `LLM_API_KEY` is missing (skip ≠ pass) or when no real eval runner is wired. Soft never greens by skipping keys.

## Composition

Use this **beside** full eval stacks (Promptfoo, DeepEval, Ragas, judge harnesses). Those score quality and trajectories. This only fails closed on completion, handoff, MCP, tool-call, and span/two-zero contract shapes. It does not replace Stop-hook tools, LangSmith, or human review.

### Optional: Promptfoo quality evals (beside Homi Gate)

Contracts stay here. For prompt/agent **quality** in CI, add Promptfoo with **deterministic** asserts (`not-contains` / `is-json` / trajectory tool checks) and `--fail-on-error` — never LLM-rubric alone for green. See Promptfoo [CI/CD](https://www.promptfoo.dev/docs/integrations/ci-cd/) + [asserts](https://www.promptfoo.dev/docs/configuration/expected-outputs/). Companion trajectory match: LangChain AgentEvals (Course 031).

Then still run Homi Gate on receipts (completion · handoff · MCP).



### Field-remix: `check-tools` (wrong-tool=0)

Deterministic `tools_called` vs `expected_tools` — names-only by default, optional `--exact-args`. Exit `0`/`1`, **no LLM in the loop**. Soft-DONE still fails if judge-alone.

Public pattern sources (FN-ENGINE2):

- [Promptfoo — Mock Tool Execution / hermetic `toolMocks`](https://www.promptfoo.dev/docs/providers/openai-agents/)
- [DeepEval — ToolCorrectnessMetric (det-first)](https://deepeval.com/docs/metrics-tool-correctness)

Evals measure; gates authorize. This check is the gate slice of those field tactics — not a full eval framework.

### Field-remix-3: `check-spans` (A2E thin det · soft never alone)

Cite [PAPER-FIELD-REMIX-3](https://arxiv.org/abs/2608.07346) A2E — ship **only** the deterministic slice (no LLM judge / no full A2E DB/UI):

| ID | Assert | Gate |
|----|--------|------|
| **A1** | `assert_span_tree_min` | Parent + ≥1 child tool span with name+status when tool use claimed |
| **A2** | `assert_tool_invocation_valid` | Tool status ∈ {ok,error,denied}; args object; non-empty name |
| **A3** | `assert_two_zero_split` | Pair of `correctness=0` fixtures must split early stall (high `tool_call_count`, `unique_tools≤1`) vs late tool malform (`tool_invocation_valid=false` after `plan_complete`) |

Soft / LLM lifecycle petals stay optional companions and **never ACCEPT alone** (PAPER-032 · field-remix-2 two-speed).

## Non-goals

- Not a full eval framework  
- Not an LLM-as-judge or judge calibrator  
- Not a RAG scorer  
- Not a hosted SaaS / observability platform  
- Not a substitute for human review on regulated paths  

## Falsifier

If a weekend clone does **not** catch a truncated run, a null handoff, an open MCP config, a wrong-tool receipt, a missing tool span, and indistinguishable correctness=0 zeros in `examples/`, treat the wedge as dead and open an issue.

## Roadmap

- JSON Schema exports + optional SARIF for PR annotations  
- More receipt dialects (Agents SDK / LangGraph slices)  
- ~~wrong-tool=0 from tool-call receipts~~ → shipped as `check-tools` (field-remix-1)
- ~~A2E span / two-zero det asserts~~ → shipped as `check-spans` (field-remix-3)

Build-in-public drafts (manual post only): [CONTENT/FOLLOWERS.md](CONTENT/FOLLOWERS.md).

## License

MIT — [LICENSE](LICENSE).

## Safety

Examples are public/synthetic. No secrets. Nothing in `CONTENT/` is auto-published.
