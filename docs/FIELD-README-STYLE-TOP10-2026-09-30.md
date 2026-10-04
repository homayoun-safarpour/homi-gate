# Field notes - README style of top public OSS (evals / gates / MCP / CI)

| Field | Value |
|-------|-------|
| **Date** | 2026-09-30 Europe/London |
| **Lane** | Hire-fast: evals, agent stop/gates, MCP, CI harnesses |
| **Method** | Public raw README / docs only; paraphrase, no long verbatim dumps |
| **Homayoun repo skim** | https://github.com/homayoun-safarpour/homi-gate (matches local CONTENT; thin, already gate-shaped) |
| **Purpose** | Steal structure/behavior for `homi-gate` README; not brand voice |

---

## 1. promptfoo/promptfoo

- **Voice:** Product-marketing + developer-first. Short imperative tagline (“stop trial-and-error… ship secure agents”). Badge wall + link strip early.
- **Structure order:** Hero → Quick Start (install + one command) → capability bullets → why-us bullets → docs/contribute.
- **Leads with:** CLI that runs in minutes; evals *and* red team in one sentence.
- **Proof:** Screenshots/GIFs of CLI + UI + vulnerability reports; “battle-tested / 10M+ users” claim (platform scale - do not copy for early OSS).
- **Non-goals/limits:** Thin on explicit non-goals; “private / runs locally” used as trust signal more than scope fence.
- **Install pattern:** `npm i -g` / brew / pip / `npx` - multi-surface, env key then `eval` + `view`.
- **Steal for homi-gate:** One-command install → run → see red/green. Capability list as verbs. CI callout.
- **Avoid:** Badge spam, acquisition banners, unverifiable user-scale claims, SaaS funnel as hero.

## 2. confident-ai/deepeval

- **Voice:** Framework catalog voice (“Pytest for LLM apps”). Exhaustive metric taxonomy; emoji section headers; heavy Confident AI upsell callouts.
- **Structure order:** Hero/tagline → metric encyclopedia → integrations → dual quickstarts (agent vibe + human) → platform → contributing/roadmap/license.
- **Leads with:** Breadth of metrics and “end-to-end + trajectory + step” coverage.
- **Proof:** Runnable pytest-style test snippet; many framework snippets; demo GIF tied to cloud login.
- **Non-goals/limits:** Almost none - roadmap lists unfinished items; scope is “everything eval.”
- **Install pattern:** `pip install -U deepeval` → optional `deepeval login` → write `test_*.py` → `deepeval test run`.
- **Steal:** “Looks like pytest” familiarity; table/list of *what fails*; CI-native command.
- **Avoid:** Encyclopedia README; dual login/SaaS hero; emoji walls; claiming every agent surface.

## 3. explodinggradients/ragas (vibrantlabsai)

- **Voice:** Toolkit marketing (“supercharge evaluations”) + friendly community. Metrics + synthetic data + feedback loops.
- **Structure order:** Hero/badges → key features → install → quickstart templates → consulting CTA → community → analytics transparency → cite.
- **Leads with:** Objective metrics + test-set generation when you lack data.
- **Proof:** Short async metric code; `ragas quickstart` project scaffold; Discord.
- **Non-goals/limits:** Soft - “coming soon” templates; open analytics with opt-out (honest, but not a product fence).
- **Install pattern:** `pip install ragas` or git; `ragas quickstart <template>`.
- **Steal:** Scaffold command / example project; discrete metric mini-demo; opt-out telemetry honesty if you ever add any (homi-gate: prefer **zero** telemetry).
- **Avoid:** Consulting booking as mid-README CTA; hype adjectives (“ultimate toolkit”).

## 4. ai-evals-course/evals-skills

- **Voice:** Practitioner-teacher. “Product-specific evals, not foundation benchmarks.” Footgun-aware; course-grounded authority without swagger.
- **Structure order:** What/why → routing entry skill → install → skill table → deep dive on most important skill → write-your-own → beyond.
- **Leads with:** Mistake prevention and a **router** (`evals-start`) that picks the next skill.
- **Proof:** Workflow diagram; concrete agent prompt (“help me do error analysis on traces.jsonl”); cite teaching/company volume lightly.
- **Non-goals/limits:** Explicitly scoped away from prod monitoring / full course topics - “beyond these skills.”
- **Install pattern:** `npx skills add <repo>` (± single skill).
- **Steal:** Router mental model; severity-ordered next steps; “only write evals after error discovery”; skill table.
- **Avoid:** Course promo as the product; jargon without a path.

## 5. openai/openai-agents-python

- **Voice:** Official SDK: calm, numbered core concepts, provider-agnostic claim, minimal hype.
- **Structure order:** One-liner + badge → core concepts list → get started (venv/uv) → four run modes with full snippets → contributing policy → acknowledgements.
- **Leads with:** Lightweight multi-agent framework + concept map (agents, handoffs, guardrails, tracing…).
- **Proof:** Runnable hello-world; sandbox/realtime/voice variants; link to `examples/`.
- **Non-goals/limits:** Contribution policy is closed to non-collaborators (honest gate); not an eval product.
- **Install pattern:** `pip install openai-agents` or `uv add`; optional extras; `OPENAI_API_KEY`.
- **Steal:** Numbered concept list; smallest working snippet first; extras/groups for optional weight.
- **Avoid:** Treating SDK breadth as homi-gate’s job; closed-contrib posture unless true.

## 6. langchain-ai/agentevals

- **Voice:** Focused library README that *is* the docs. Conceptual framing (trajectory / black-box pain) then deep API.
- **Structure order:** Why trajectory evals → quickstart → ToC → installation → evaluator modes (strict/unordered/subset/LLM-judge/graph) → async → LangSmith → thanks.
- **Leads with:** Problem statement (control-flow freedom → hard to know downstream impact).
- **Proof:** Fake trajectory → printed score/reasoning; match-mode examples; LangSmith pytest snippet.
- **Non-goals/limits:** Points to `openevals` for general evals - good scope fence.
- **Install pattern:** `pip install agentevals` / `npm i agentevals`; key for judge path.
- **Steal:** Explicit companion-package pointer; mode matrix with *when to use*; printed eval_result as proof.
- **Avoid:** 4k-line README as the only doc surface for a tiny CLI; LangSmith-required framing.

## 7. braintrustdata/braintrust (SDK repos + docs)

- **Voice:** Platform + SDK. Thin repo READMEs; real story lives at braintrust.dev. `Eval(data, task, scores)` triad.
- **Structure order (SDK):** Logo/hero → one-liner → quickstart Eval → run with API key → package table → docs links → license.
- **Leads with:** “Platform for evaluating and shipping AI products” + 15-line Eval.
- **Proof:** Tiny Eval that runs via CLI; docs site for depth.
- **Non-goals/limits:** Repo is packaging; product limits live in docs/pricing (not fenced in README).
- **Install pattern:** `pip/npm install braintrust autoevals` → write `*.eval.*` → `braintrust eval` + `BRAINTRUST_API_KEY`.
- **Steal:** Ruthlessly small Eval shape; CLI verb `eval`; clear “API key for cloud log” boundary.
- **Avoid:** Logo-first empty hero; implying a hosted platform when you are local CLI only; key-required for the core gate (homi-gate must work offline).

## 8. anthropics/anthropic-sdk-python (+ engineering agents patterns)

- **SDK voice:** Minimal, documentation-pointer. Install → five-line Messages call → requirements → license. Almost no story.
- **Engineering post voice (better pattern reference):** Calm systems writing. Define terms (workflows vs agents). **When / when not.** Prefer simple composable patterns; measure before adding complexity; gates in prompt-chaining diagrams.
- **Structure (post):** Definitions → when-not → frameworks caution → patterns with “when to use” → principles summary.
- **Leads with:** Successful teams used simple patterns, not complex frameworks.
- **Proof:** Customer/domain appendices; pattern diagrams; SWE-bench mention as measured outcome.
- **Non-goals/limits:** Explicit “when not to use agents”; frameworks can obscure prompts.
- **Install (SDK):** `pip install anthropic`.
- **Steal from post:** When/when-not; named patterns; “add complexity only when measured”; programmatic **gates** between steps.
- **Avoid from SDK alone:** README so thin it dumps users to an external site with no local falsifier; from post - do not paste Anthropic brand essay voice.

## 9. vnmoorthy/groundtruth (Stop hook)

- **Voice:** Sharp operator. Imperative headline. In-vivo probe story. Comparison table. Honest limits + zero-telemetry manifesto. Closest cousin to homi-gate’s wedge.
- **Structure order:** Badges → one-liner + curl install → playground → 30s live probe → diagram → compare table → empirical calibration → quick start → CLI → composition → protocol → layout → **Honest limits** → telemetry none → community → docs → license.
- **Leads with:** Physical refusal of unverified “done” (Stop hook).
- **Proof:** Before/after assistant turns; corpus calibration table; test/audit badges; playground without install.
- **Non-goals/limits:** Mid-turn-only; regex detector; heuristic verifier; not adversarial; composes with gstack/superpowers rather than replacing.
- **Install pattern:** One-line `curl | bash` + `groundtruth status`; audit offline.
- **Steal:** Falsifying live story; honest limits section; composition (“does not replace X”); calibration against real sessions; CI-friendly `--fail-on`; SARIF.
- **Avoid:** Curl-pipe as *only* install if you can offer pip; Claude-Code-only framing for a CI library; badge overload; playground promise without shipping one.

## 10. bengodgart/llm-judge-calibration *(picked over omarnagy91/llm-eval-ci - richer offline README + honest verdict block; both real)*

- **Voice:** Hire-portfolio practitioner. Headline **number** first (kappa 0.58). Contrarian: everyone uses judges; almost nobody calibrates. Shows failure on refusals on purpose.
- **Structure order:** Headline metric + thesis → sample report dump → 30s quickstart → what it measures → verdict rules → bring-your-data → optional live judge (cost warned) → bundled set datasheet → tests pin numbers → why-I-built-it → license.
- **Leads with:** A real, slightly ugly number and “reliable for X, not Y.”
- **Proof:** Committed sample run; pytest pins kappa/agreement; datasheet for data provenance.
- **Non-goals/limits:** Offline by default; live judge off; not a full CI product platform.
- **Install pattern:** Clone + `python -m judgecal calibrate …` - stdlib only, $0 path.
- **Steal:** Ugly honest headline metric; exit-nonzero gate flag; pin numbers in tests; “not reliable” as a feature; cost-callout for optional network.
- **Avoid:** Making calibration the whole product when your wedge is deterministic asserts; resume-voice “why I built it” longer than the tool.

### Runner-up skim - omarnagy91/llm-eval-ci

- CI golden-set gate, six graders, offline-deterministic judge default, exit 1 on regression. Steal: “gate under test,” baseline vs PR. Avoid: paid services pitch mid-README if present on marketing page.

---

## Cross-cutting “behavior” (what winning READMEs *do*)

1. **Promise a narrow verb** (eval / calibrate / block stop / fail CI) in the first three lines.
2. **Show red and green** within one screen of install.
3. **Fence the product** with non-goals or “see companion package.”
4. **Prefer offline / deterministic paths** when the hire signal is CI trust.
5. **Proof > logos** - printed scores, fixtures, calibration tables, in-vivo stories.
6. **Composition**, not replacement - name adjacent tools you do *not* swallow.
7. **Falsifier** - if X doesn’t happen on the fixtures, the claim is dead (homi-gate already has this; keep it loud).

---

## Homayoun house style - README checklist (10 rules)

Synthesized for `homi-gate` and similar thin public tools. Professional human practitioner. **Not** Promptfoo/DeepEval/Braintrust brand voice.

1. **Lead with the failure mode, not the stack.** First lines name what goes red (truncated run, null handoff, open MCP) - frameworks come later if at all.
2. **One screen to proof.** Install (or `PYTHONPATH`) → three pass commands → three fail commands with exit `1`. No account, no API key for the core path.
3. **Determinism is a feature, say it once.** Exit `0`/`1`, no LLM in the loop - then stop repeating the slogan.
4. **Table the asserts.** Command | pass when | fail when. Required fields listed once.
5. **Non-goals in bullets.** Name the big eval frameworks as *out of scope*, not as enemies; “not a substitute for human review.”
6. **Falsifier paragraph.** Weekend clone must catch the three bad examples or the wedge is dead - invite the issue.
7. **CI snippet that looks like real Actions.** `pytest` + the three checks; link this repo’s workflow. No invented stars/users/SaaS.
8. **Composition line.** Works beside Promptfoo/DeepEval/Ragas/judges - those score quality; this fails contracts.
9. **Roadmap as thin next asserts** (schema/SARIF, dialects, wrong-tool counter) - still deterministic, still not a platform.
10. **Safety & license footer.** MIT; synthetic examples; no secrets; `CONTENT/` is drafts, never auto-published. Voice: short sentences, concrete nouns, zero emoji walls, zero “supercharge.”

