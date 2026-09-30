# Build-in-public drafts — homi-gate

**No auto-publish.** Homayoun posts manually. Tone: Ireland hire-fast, gates not logos, public/synthetic only.

---

## 1 — LinkedIn (problem tease)

Most agent demos “complete.”  
Most production receipts don’t.

I’ve been reading Dublin/Ireland AI eng JDs. The hire signal isn’t “we use X framework.” It’s:

- eval harness + release gates  
- MCP wrong-tool = 0  
- agents that actually stop  

Open-sourced a tiny gate tonight: **homi-gate** — fail-closed checks for completion bit, handoff contracts, MCP allowlist.

Completion ≠ satisfaction. If the receipt says truncated, CI should go red.

https://github.com/homayoun-safarpour/homi-gate

#AIEngineering #LLMOps #Evals

---

## 2 — X / LinkedIn short

`context: null` is not a handoff.

If Worker-B inherits a chat dump and a null context field, you didn’t build multi-agent — you built a relay of confusion.

homi-gate `check-handoff`: required fields non-null, one pending goal, stop condition present. Fail closed.

Repo: https://github.com/homayoun-safarpour/homi-gate

---

## 3 — LinkedIn (MCP angle)

Open MCP tool surfaces are how “wrong tool” becomes a production incident.

Ireland JDs are asking for MCP-style tool protocols + observability. The boring part still wins:

- named allowlist  
- named denylist  
- or `enabled: false` with an explicit tool list  

That’s what `homi-gate check-mcp-allowlist` asserts in CI. No model score. Just config truth.

---

## 4 — X thread starter (build-in-public)

Day 1 of **homi-gate**:

Three CLI commands. Three exit codes. Zero vibes.

```
check-completion
check-handoff
check-mcp-allowlist
```

Built from public IE/EU hire signals → thin CI gates, not another eval framework.

MIT. Examples in repo. Bad fixtures must fail.

---

## 5 — LinkedIn (followers → clients path)

Open-source first, hire-prep second.

I’m publishing **homi-gate** as the public proof of “gates with numbers/asserts” — the same shape Ireland AI roles list under eval harness, MCP, and agents-that-stop.

Path:

1. Followers see the red/green demos  
2. Teams reuse the Action snippet  
3. Clients who want a review of *their* agent CI can ask — still gates only, no secrets in the OSS path  

If your CI can’t fail on a truncated agent run, we should talk after the repo is up.

---

## Posting rules

- Manual only — never auto-publish from agents.  
- No private data, no salary numbers, no 23–100.  
- No Ragas/DeepEval name-drop as the product value.  
- Link the public repo once it exists (Allow: create remote + push).
