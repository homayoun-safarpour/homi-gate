# Why these gates

Agent CI often stays green while the run is truncated, the next worker gets `context: null`, or MCP exposes every tool. Those are contract failures - they do not need an LLM judge.

## Signals (public hiring + production writing, 2026)

Live Ireland / EU AI engineering roles and practitioner notes keep asking for the same shape:

1. **Eval harness + release gates** - regression that can go red before merge  
2. **MCP / tool contracts** - named allowlist (wrong-tool toward zero), not “enable the whole server”  
3. **Agents that stop** - completion is a receipt field, not a vibe  
4. **Handoff boundaries** - silent null context while spans look healthy is a known multi-agent fail class  
5. **Asserts over logos** - a green bar beats naming a framework

## Mapping

| Failure mode | Command | Assert |
|--------------|---------|--------|
| Truncated / incomplete run | `check-completion` | completion bit / complete status; not truncated |
| Null or incomplete handoff | `check-handoff` | required fields non-null; one pending; stop present |
| Open MCP surface | `check-mcp-allowlist` | allowlist+denylist or disabled+named tools |

## Falsifier

If the example fixtures in this repo do not produce exit `1` on the bad paths, the product claim is false - fix or delete.

## What this is not

Not a full eval stack. Not a judge. Not auto-outreach. Thin CI layer only.
