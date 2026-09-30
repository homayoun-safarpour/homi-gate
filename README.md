# homi-gate

**Fail-closed CI gates for agent / MCP / RAG pipelines** — completion bit, handoff contracts, MCP allowlist check.

Built from Ireland/EU hire signals: eval harness + release gates, MCP wrong-tool=0, agents that stop. Gates with numbers and asserts — not framework logos.

> Working title. Public/synthetic scaffold. MIT.

## Problem

Agent runs “finish” without finishing. Handoffs arrive with `context: null` and a chat dump. MCP toolsets ship with every tool enabled. CI stays green because nobody asserted the contract.

Completion ≠ satisfaction. A truncated receipt with `status: truncated` is not a pass. A handoff missing `proved` / `pending` / `stop` is not a handoff. An MCP config without an allowlist is an open surface.

## Market need (hire signals, public JDs)

- **Eval harness + CI release gates** — regression suites that fail closed before merge (Dublin/IE AI eng JDs).
- **MCP / tool contracts with wrong-tool=0** — named allowlist + denylist, or tools disabled with an explicit named set.
- **Agents that stop** — completion bit on the receipt; no silent truncate.
- **Compact handoff** — required fields non-null; `context: null` is a fail, not a shrug.
- **Gates with numbers/asserts** — sell the red/green bar, not a toolkit name-drop.

See [docs/MARKET.md](docs/MARKET.md) for the signal copy.

## Install

```bash
# from this repo
pip install -e ".[dev]"

# or run without install
PYTHONPATH=src python -m homi_gate --help
```

Requires Python ≥ 3.11.

## CLI usage

```bash
# Completion bit — fail if truncated / incomplete
homi-gate check-completion examples/pass.json      # exit 0
homi-gate check-completion examples/fail.json      # exit 1
homi-gate check-completion examples/pass.jsonl

# Handoff contract — required fields non-null, schema
homi-gate check-handoff examples/handoff_ok.json   # exit 0
homi-gate check-handoff examples/handoff_bad.json  # exit 1

# MCP allowlist — allowlist+denylist, or enabled:false + named tools
homi-gate check-mcp-allowlist examples/mcp_ok.yaml           # exit 0
homi-gate check-mcp-allowlist examples/mcp_disabled_ok.yaml  # exit 0
homi-gate check-mcp-allowlist examples/mcp_bad.yaml          # exit 1
```

Exit codes: `0` = pass, `1` = fail-closed (reasons on stderr).

### Receipt shapes (minimal)

**Completion** — final record must have `completion_bit: true` **or** a known complete `status` (`completed` / `complete` / `success` / `ok` / `done`). `truncated: true` or incomplete statuses fail.

**Handoff** — required non-null: `from_agent`, `to_agent`, `proved`, `pending` (one goal), `stop`, `forbidden`, `report`. Aliases `from`/`to` accepted. `context: null` fails.

**MCP** — either `allowlist` + `denylist` (non-empty allowlist), or `enabled: false` with a non-empty named `tools` list. Overlap between allow and deny fails.

## GitHub Action snippet

```yaml
name: homi-gate
on: [push, pull_request]
jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest -q
      - name: Demo — expect PASS
        run: |
          homi-gate check-completion examples/pass.json
          homi-gate check-handoff examples/handoff_ok.json
          homi-gate check-mcp-allowlist examples/mcp_ok.yaml
      - name: Demo — expect FAIL (fail-closed)
        run: |
          ! homi-gate check-completion examples/fail.json
          ! homi-gate check-handoff examples/handoff_bad.json
          ! homi-gate check-mcp-allowlist examples/mcp_bad.yaml
```

Full workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Roadmap (followers → clients)

1. **Week 0** — this scaffold live; build-in-public posts (see [CONTENT/FOLLOWERS.md](CONTENT/FOLLOWERS.md)); no auto-publish.
2. **Week 1–2** — JSON Schema exports; optional SARIF output for PR annotations; more receipt dialects (OpenAI Agents / LangGraph trace slices).
3. **Week 3–4** — “wrong-tool=0” counter from tool-call logs; golden-set regression gate stub (assert counts, not model scores).
4. **Clients** — hire-prep / release-gate workshops from Ireland JD gaps; paid review of a team’s agent CI (gates only — no secrets, no private data in the OSS path).

## License

MIT — see [LICENSE](LICENSE).

## Safety

No secrets. No private data. Public/synthetic examples only. Drafts in `CONTENT/` are not auto-published.
