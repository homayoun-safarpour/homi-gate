"""homi-gate CLI — fail-closed checks for completion, handoff, MCP allowlist, tool correctness, spans (A2E), trajectory."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# --- completion -------------------------------------------------------------

_INCOMPLETE_STATUSES = frozenset(
    {"truncated", "incomplete", "error", "failed", "running", "aborted"}
)
_COMPLETE_STATUSES = frozenset({"completed", "complete", "success", "ok", "done"})
_ARTIFACT_KEYS = (
    "artifact",
    "artifact_path",
    "proof",
    "proof_path",
    "evidence",
    "evidence_path",
)


def _has_artifact_or_proof(rec: dict[str, Any]) -> bool:
    """True when receipt carries a non-empty artifact/proof/evidence path or payload."""
    for key in _ARTIFACT_KEYS:
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return True
        if isinstance(val, (list, dict)) and len(val) > 0:
            return True
    return False


def _load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"empty receipt: {path}")
    if path.suffix.lower() == ".jsonl" or "\n" in text and not text.lstrip().startswith("{"):
        records: list[dict[str, Any]] = []
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{i}: invalid JSONL: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{i}: each JSONL line must be an object")
            records.append(obj)
        if not records:
            raise ValueError(f"empty JSONL receipt: {path}")
        return records
    obj = json.loads(text)
    if isinstance(obj, list):
        if not obj:
            raise ValueError(f"empty receipt list: {path}")
        if not all(isinstance(x, dict) for x in obj):
            raise ValueError(f"{path}: receipt list items must be objects")
        return obj
    if isinstance(obj, dict):
        return [obj]
    raise ValueError(f"{path}: receipt must be object, list, or JSONL")


def check_completion(path: Path) -> list[str]:
    """Return list of failure reasons (empty = pass)."""
    records = _load_json_or_jsonl(path)
    last = records[-1]
    reasons: list[str] = []

    if last.get("truncated") is True:
        reasons.append("truncated=true on final record")

    bit = last.get("completion_bit", last.get("complete"))
    status = last.get("status")
    status_l = str(status).lower() if status is not None else None

    if bit is False:
        reasons.append("completion_bit=false")
    elif bit is None:
        if status is None:
            reasons.append("missing completion_bit/complete and status")
        elif status_l in _INCOMPLETE_STATUSES:
            reasons.append(f"status={status!r} is incomplete")
        elif status_l not in _COMPLETE_STATUSES:
            reasons.append(f"status={status!r} not a known complete status")
    elif bit is not True:
        reasons.append(f"completion_bit must be bool, got {type(bit).__name__}")

    # Soft DONE: claiming complete (bit or known status) requires artifact/proof path
    claims_complete = bit is True or (
        bit is None and status_l in _COMPLETE_STATUSES
    )
    if claims_complete and not _has_artifact_or_proof(last):
        reasons.append(
            "soft DONE: complete/DONE without proof_path/evidence_path/artifact"
        )

    # Mid-stream truncate flag stream-vetoes a later green final (not final-record-wins)
    for i, rec in enumerate(records):
        if rec.get("truncated") is True and i < len(records) - 1:
            reasons.append(f"record[{i}] truncated=true before final record")
            break

    return reasons


# --- handoff ----------------------------------------------------------------

_HANDOFF_REQUIRED = ("from_agent", "to_agent", "proved", "pending", "stop", "forbidden", "report")
# Accept aliases commonly seen in compact handoff kits
_HANDOFF_ALIASES = {
    "from": "from_agent",
    "to": "to_agent",
    "from_worker": "from_agent",
    "to_worker": "to_agent",
}


def _normalize_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    for alias, canon in _HANDOFF_ALIASES.items():
        if alias in out and canon not in out:
            out[canon] = out[alias]
    return out


def check_handoff(path: Path) -> list[str]:
    """Validate handoff payload: required fields present and non-null."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return ["empty handoff file"]
    payload = json.loads(text)
    if not isinstance(payload, dict):
        return ["handoff must be a JSON object"]
    payload = _normalize_handoff(payload)
    reasons: list[str] = []

    for field in _HANDOFF_REQUIRED:
        if field not in payload:
            reasons.append(f"missing required field: {field}")
            continue
        val = payload[field]
        if val is None:
            reasons.append(f"{field} is null")
        elif isinstance(val, str) and not val.strip():
            reasons.append(f"{field} is empty string")
        elif isinstance(val, (list, dict)) and len(val) == 0 and field in ("proved",):
            # proved may be empty list if nothing proved yet — allow, but pending must be set
            pass

    # Explicit anti-pattern from hire signals: context:null with no substitute
    if "context" in payload and payload["context"] is None:
        reasons.append("context is null (pass compact proved/pending/stop instead)")
    # Soft-null coerce: empty {} / [] keeps dashboards green (RD-G / CRED-1 score theater)
    elif "context" in payload and isinstance(payload["context"], (dict, list)) and len(payload["context"]) == 0:
        reasons.append(
            "context is empty (soft-null coerce); pass compact proved/pending/stop instead"
        )

    # Nested context:null (report/transcript wrappers from transcript-dump handoffs)
    for nest_key in ("report", "transcript", "payload"):
        nest = payload.get(nest_key)
        if isinstance(nest, dict) and "context" in nest and nest["context"] is None:
            reasons.append(f"{nest_key}.context is null (nested)")

    # pending must be a single goal string, not a dump
    pending = payload.get("pending")
    if isinstance(pending, list):
        if len(pending) != 1:
            reasons.append(f"pending must be one goal, got list len={len(pending)}")
    elif isinstance(pending, str) and "\n\n" in pending and len(pending) > 500:
        reasons.append("pending looks like a transcript dump (>500 chars with blank lines)")

    return reasons


# --- MCP allowlist ----------------------------------------------------------

def _load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML required for YAML configs; pip install pyyaml")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping/object")
    return data


def _mcp_section(data: dict[str, Any]) -> dict[str, Any]:
    if "mcp" in data and isinstance(data["mcp"], dict):
        return data["mcp"]
    return data


def check_mcp_allowlist(path: Path) -> list[str]:
    """Validate MCP toolset has allowlist+denylist, or enabled:false + named tools."""
    data = _load_config(path)
    mcp = _mcp_section(data)
    reasons: list[str] = []

    enabled = mcp.get("enabled", True)

    if enabled is False:
        tools = mcp.get("tools") or mcp.get("named_tools") or mcp.get("allowlist")
        if tools is None:
            reasons.append("enabled:false requires named tools (tools/named_tools/allowlist)")
        elif not isinstance(tools, list) or len(tools) == 0:
            reasons.append("enabled:false tools list must be a non-empty list of names")
        elif not all(isinstance(t, str) and t.strip() for t in tools):
            reasons.append("enabled:false tools must be non-empty strings")
        return reasons

    allow = mcp.get("allowlist")
    deny = mcp.get("denylist") or mcp.get("blocklist")

    if allow is None:
        reasons.append("missing allowlist (or set enabled:false with named tools)")
    elif not isinstance(allow, list):
        reasons.append("allowlist must be a list")
    elif len(allow) == 0:
        reasons.append("allowlist is empty — fail-closed requires at least one named tool")
    elif not all(isinstance(t, str) and t.strip() for t in allow):
        reasons.append("allowlist entries must be non-empty strings")

    if deny is None:
        reasons.append("missing denylist/blocklist (or set enabled:false with named tools)")
    elif not isinstance(deny, list):
        reasons.append("denylist must be a list")
    # empty denylist is allowed (explicit empty = documented none-blocked)

    if isinstance(allow, list) and isinstance(deny, list):
        overlap = sorted(set(allow) & set(deny))
        if overlap:
            reasons.append(f"tools in both allowlist and denylist: {overlap}")

    return reasons



# --- tool correctness (field-remix: DeepEval ToolCorrectness det-first + Promptfoo hermetic mocks) ---

_EXPECTED_TOOL_KEYS = ("expected_tools", "expected", "expected_allowlist")
_CALLED_TOOL_KEYS = ("tools_called", "tools", "tool_calls")


def _tool_name(entry: Any) -> str | None:
    """Normalize a tools_called / expected_tools entry to a tool name."""
    if isinstance(entry, str):
        name = entry.strip()
        return name or None
    if isinstance(entry, dict):
        for key in ("name", "tool", "tool_name", "function"):
            val = entry.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
            # OpenAI-style {"function": {"name": "..."}}
            if key == "function" and isinstance(val, dict):
                nested = val.get("name")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
        return None
    return None


def _tool_args(entry: Any) -> Any:
    """Return args/input payload when entry is an object; None for bare names."""
    if not isinstance(entry, dict):
        return None
    for key in ("args", "arguments", "input", "input_parameters", "params"):
        if key in entry:
            return entry[key]
    fn = entry.get("function")
    if isinstance(fn, dict) and "arguments" in fn:
        return fn["arguments"]
    return None


def _extract_tool_list(rec: dict[str, Any], keys: tuple[str, ...]) -> tuple[list[Any] | None, str | None]:
    """Return (list_or_None, key_used). None list means key absent."""
    for key in keys:
        if key in rec:
            return rec[key], key
    return None, None


def check_tools(path: Path, *, exact_args: bool = False) -> list[str]:
    """Compare tools_called vs expected_tools deterministically (wrong-tool=0).

    Names-only by default. With exact_args=True, also require matching args/input
    for each expected tool occurrence. No LLM in the loop.
    """
    records = _load_json_or_jsonl(path)
    last = records[-1]
    reasons: list[str] = []

    called_raw, called_key = _extract_tool_list(last, _CALLED_TOOL_KEYS)
    expected_raw, expected_key = _extract_tool_list(last, _EXPECTED_TOOL_KEYS)

    if called_raw is None:
        reasons.append("missing tools_called (or tools / tool_calls)")
    elif not isinstance(called_raw, list):
        reasons.append(f"{called_key} must be a list, got {type(called_raw).__name__}")

    if expected_raw is None:
        reasons.append("missing expected_tools (or expected / expected_allowlist)")
    elif not isinstance(expected_raw, list):
        reasons.append(f"{expected_key} must be a list, got {type(expected_raw).__name__}")
    elif len(expected_raw) == 0:
        # claim asserts tools (tools_called present) or expected key exists empty
        reasons.append(
            "empty expected_tools when claim asserts tools — fail-closed (no judge-alone green)"
        )

    if reasons:
        return reasons

    assert isinstance(called_raw, list) and isinstance(expected_raw, list)

    called_names: list[str] = []
    for i, entry in enumerate(called_raw):
        name = _tool_name(entry)
        if name is None:
            reasons.append(f"tools_called[{i}] has no usable tool name")
        else:
            called_names.append(name)

    expected_names: list[str] = []
    for i, entry in enumerate(expected_raw):
        name = _tool_name(entry)
        if name is None:
            reasons.append(f"expected_tools[{i}] has no usable tool name")
        else:
            expected_names.append(name)

    if reasons:
        return reasons

    called_set = set(called_names)
    expected_set = set(expected_names)

    unexpected = sorted(called_set - expected_set)
    missing = sorted(expected_set - called_set)

    if unexpected:
        reasons.append(f"unexpected tools (wrong-tool=0): {unexpected}")
    if missing:
        reasons.append(f"missing required tools: {missing}")

    if exact_args and not unexpected and not missing:
        # Multiset match by name+args for expected entries that carry args
        def _sig(entry: Any) -> tuple[str, str]:
            name = _tool_name(entry) or ""
            args = _tool_args(entry)
            # Canonical JSON for stable compare; bare-name expected skips args check
            if args is None:
                return name, ""
            return name, json.dumps(args, sort_keys=True, default=str)

        # Only enforce args when expected entry provides them
        expected_with_args = [e for e in expected_raw if _tool_args(e) is not None]
        if expected_with_args:
            called_counter = Counter(_sig(e) for e in called_raw)
            for entry in expected_with_args:
                sig = _sig(entry)
                if called_counter[sig] <= 0:
                    reasons.append(
                        f"exact-args mismatch: expected {sig[0]} with args {sig[1]} not found in tools_called"
                    )
                else:
                    called_counter[sig] -= 1

    return reasons




# --- spans / A2E thin det asserts (field-remix-3 / PAPER-FIELD-REMIX-3 / arXiv 2608.07346) ---

_TOOL_SPAN_KINDS = frozenset({"tool", "TOOL", "tool_call", "TOOL_CALL"})
_AGENT_SPAN_KINDS = frozenset({"agent", "AGENT", "chain", "CHAIN", "llm", "LLM", "run", "parent"})
_TOOL_STATUS_OK = frozenset({"ok", "error", "denied"})
_DEFAULT_EARLY_STALL_MIN_CALLS = 5


def _claims_tool_use(rec: dict[str, Any]) -> bool:
    """True when the receipt claims tool use (A1 applies)."""
    for key in ("tool_use", "claimed_tool_use", "uses_tools"):
        if rec.get(key) is True:
            return True
    count = rec.get("tool_call_count")
    if isinstance(count, int) and count > 0:
        return True
    for key in _CALLED_TOOL_KEYS:
        val = rec.get(key)
        if isinstance(val, list) and len(val) > 0:
            return True
    # Presence of any tool-kind span also counts as a claim
    if _collect_tool_spans(rec.get("spans")):
        return True
    return False


def _span_kind(span: dict[str, Any]) -> str:
    for key in ("kind", "type", "role", "span_kind", "openinference_span_kind"):
        val = span.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _is_tool_span(span: dict[str, Any]) -> bool:
    kind = _span_kind(span).lower()
    if kind in {k.lower() for k in _TOOL_SPAN_KINDS}:
        return True
    # Heuristic: explicit tool name field + args often means tool even without kind
    if span.get("is_tool") is True:
        return True
    return False


def _iter_spans_nested(spans: Any) -> list[dict[str, Any]]:
    """Flatten nested children / flat list into a list of span dicts (depth-first)."""
    out: list[dict[str, Any]] = []
    if not isinstance(spans, list):
        return out
    for span in spans:
        if not isinstance(span, dict):
            continue
        out.append(span)
        kids = span.get("children") or span.get("spans")
        if kids:
            out.extend(_iter_spans_nested(kids))
    return out


def _collect_tool_spans(spans: Any) -> list[dict[str, Any]]:
    return [s for s in _iter_spans_nested(spans) if _is_tool_span(s)]


def _collect_parent_spans(spans: Any) -> list[dict[str, Any]]:
    """Parent = top-level spans, or spans with kind agent/chain/llm, or spans that have children."""
    if not isinstance(spans, list):
        return []
    parents: list[dict[str, Any]] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        kind = _span_kind(span).lower()
        has_kids = isinstance(span.get("children") or span.get("spans"), list) and len(
            span.get("children") or span.get("spans") or []
        ) > 0
        if kind in {k.lower() for k in _AGENT_SPAN_KINDS} or has_kids or span.get("parent_id") in (None, "", 0):
            # For flat lists: treat roots (no parent_id / parent_id null) as parents
            if "parent_id" in span and span.get("parent_id") not in (None, "", 0):
                continue
            parents.append(span)
    # Flat parent_id form: also include any span referenced as parent of a tool
    flat = _iter_spans_nested(spans)
    by_id = {s.get("span_id"): s for s in flat if isinstance(s.get("span_id"), (str, int))}
    for tool in _collect_tool_spans(spans):
        pid = tool.get("parent_id")
        if pid in by_id and by_id[pid] not in parents:
            parents.append(by_id[pid])
    return parents


def _tool_span_name(span: dict[str, Any]) -> str | None:
    for key in ("name", "tool", "tool_name", "function"):
        val = span.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if key == "function" and isinstance(val, dict):
            nested = val.get("name")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _tool_span_args(span: dict[str, Any]) -> Any:
    for key in ("args", "arguments", "input", "input_parameters", "params", "attributes"):
        if key in span:
            return span[key]
    return None


def assert_span_tree_min(rec: dict[str, Any]) -> list[str]:
    """A1: when tool use claimed, require ≥1 parent + ≥1 child tool span with name+status."""
    reasons: list[str] = []
    if not _claims_tool_use(rec):
        return reasons  # A1 only applies when tool use is claimed
    spans = rec.get("spans")
    if spans is None:
        return ["A1 assert_span_tree_min: missing spans (tool use claimed)"]
    if not isinstance(spans, list) or len(spans) == 0:
        return ["A1 assert_span_tree_min: spans must be a non-empty list"]

    parents = _collect_parent_spans(spans)
    tools = _collect_tool_spans(spans)
    if not parents:
        reasons.append("A1 assert_span_tree_min: no parent span found")
    if not tools:
        reasons.append(
            "A1 assert_span_tree_min: missing tool span on run that claimed tool use"
        )
        return reasons

    for i, tool in enumerate(tools):
        name = _tool_span_name(tool)
        status = tool.get("status")
        if name is None:
            reasons.append(f"A1 assert_span_tree_min: tool span[{i}] missing non-empty name")
        if status is None or (isinstance(status, str) and not status.strip()):
            reasons.append(f"A1 assert_span_tree_min: tool span[{i}] missing status")
    return reasons


def assert_tool_invocation_valid(rec: dict[str, Any]) -> list[str]:
    """A2: every tool span status ∈ {ok,error,denied}; args object; non-empty name."""
    reasons: list[str] = []
    spans = rec.get("spans")
    if spans is None:
        if _claims_tool_use(rec):
            return ["A2 assert_tool_invocation_valid: missing spans (tool use claimed)"]
        return reasons
    if not isinstance(spans, list):
        return ["A2 assert_tool_invocation_valid: spans must be a list"]

    tools = _collect_tool_spans(spans)
    if _claims_tool_use(rec) and not tools:
        reasons.append("A2 assert_tool_invocation_valid: no tool spans to validate")
        return reasons

    for i, tool in enumerate(tools):
        name = _tool_span_name(tool)
        if name is None:
            reasons.append(f"A2 assert_tool_invocation_valid: tool span[{i}] empty/missing name")
        status = tool.get("status")
        status_l = str(status).lower().strip() if status is not None else ""
        if status_l not in _TOOL_STATUS_OK:
            reasons.append(
                f"A2 assert_tool_invocation_valid: tool span[{i}] status={status!r} "
                f"not in {{ok,error,denied}}"
            )
        args = _tool_span_args(tool)
        if args is None:
            reasons.append(f"A2 assert_tool_invocation_valid: tool span[{i}] missing args object")
        elif not isinstance(args, dict):
            reasons.append(
                f"A2 assert_tool_invocation_valid: tool span[{i}] args must be object, "
                f"got {type(args).__name__}"
            )
    return reasons


def check_spans(path: Path) -> list[str]:
    """Run A1 + A2 on a span-tree receipt (field-remix-3). Empty list = pass."""
    records = _load_json_or_jsonl(path)
    last = records[-1]
    return assert_span_tree_min(last) + assert_tool_invocation_valid(last)


def _load_zero_fixture(path: Path) -> dict[str, Any]:
    records = _load_json_or_jsonl(path)
    return records[-1]


def _is_early_stall(rec: dict[str, Any], *, min_calls: int) -> bool:
    count = rec.get("tool_call_count")
    unique = rec.get("unique_tools")
    if not isinstance(count, int) or not isinstance(unique, int):
        return False
    return count >= min_calls and unique <= 1


def _is_late_tool_malform(rec: dict[str, Any]) -> bool:
    plan_complete = rec.get("plan_complete")
    valid = rec.get("tool_invocation_valid")
    if plan_complete is not True:
        return False
    if valid is False:
        return True
    # Derive from spans if explicit flag absent/true but A2 would fail
    if "spans" in rec and assert_tool_invocation_valid(rec):
        return True
    return False


def _zero_correctness(rec: dict[str, Any]) -> bool:
    c = rec.get("correctness")
    if c == 0 or c == 0.0:
        return True
    if c is False:
        return True
    return False


def assert_two_zero_split(
    path_a: Path,
    path_b: Path,
    *,
    min_calls: int = _DEFAULT_EARLY_STALL_MIN_CALLS,
) -> list[str]:
    """A3: two correctness=0 fixtures must discriminate early stall vs late tool malform."""
    reasons: list[str] = []
    a = _load_zero_fixture(path_a)
    b = _load_zero_fixture(path_b)

    if not _zero_correctness(a):
        reasons.append(f"A3 assert_two_zero_split: {path_a.name} correctness != 0")
    if not _zero_correctness(b):
        reasons.append(f"A3 assert_two_zero_split: {path_b.name} correctness != 0")
    if reasons:
        return reasons

    flags_a = (
        _is_early_stall(a, min_calls=min_calls),
        _is_late_tool_malform(a),
    )
    flags_b = (
        _is_early_stall(b, min_calls=min_calls),
        _is_late_tool_malform(b),
    )

    has_early = flags_a[0] or flags_b[0]
    has_late = flags_a[1] or flags_b[1]

    if not has_early:
        reasons.append(
            "A3 assert_two_zero_split: missing early-stall fixture "
            f"(need tool_call_count>={min_calls} AND unique_tools<=1)"
        )
    if not has_late:
        reasons.append(
            "A3 assert_two_zero_split: missing late-tool-malform fixture "
            "(need tool_invocation_valid=false after plan_complete)"
        )

    # Same mode on both = indistinguishable theater
    if flags_a == flags_b:
        reasons.append(
            "A3 assert_two_zero_split: both zeros look identical under det (theater)"
        )
    elif flags_a[0] and flags_b[0] and not (flags_a[1] or flags_b[1]):
        reasons.append(
            "A3 assert_two_zero_split: both look like early stall — no discrimination"
        )
    elif flags_a[1] and flags_b[1] and not (flags_a[0] or flags_b[0]):
        reasons.append(
            "A3 assert_two_zero_split: both look like late malform — no discrimination"
        )

    return reasons


def assert_two_zero_split_paths(
    paths: list[Path],
    *,
    min_calls: int = _DEFAULT_EARLY_STALL_MIN_CALLS,
) -> list[str]:
    """A3 over a pair, a list, or a directory of correctness=0 fixtures."""
    expanded: list[Path] = []
    for p in paths:
        if p.is_dir():
            found = sorted(
                q
                for q in p.iterdir()
                if q.suffix.lower() in (".json", ".jsonl") and q.is_file()
            )
            # Prefer zero_* fixtures when present
            zeros = [q for q in found if q.name.startswith("zero_")]
            expanded.extend(zeros if len(zeros) >= 2 else found)
        else:
            expanded.append(p)

    # Dedupe while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in expanded:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)

    if len(unique) < 2:
        return [
            "A3 assert_two_zero_split: need ≥2 fixtures (pair or directory with zero_*)"
        ]

    # If more than 2, keep only correctness=0 and require early+late among them
    if len(unique) > 2:
        zero_paths: list[Path] = []
        for p in unique:
            try:
                rec = _load_zero_fixture(p)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if _zero_correctness(rec):
                zero_paths.append(p)
        unique = zero_paths

    if len(unique) < 2:
        return ["A3 assert_two_zero_split: need ≥2 correctness=0 fixtures"]

    # Pairwise: first two that can form a discriminating pair, else check first two
    # For hermetic dir with exactly early+late, compare all pairs until one passes
    reasons_all: list[str] = []
    for i in range(len(unique)):
        for j in range(i + 1, len(unique)):
            reasons = assert_two_zero_split(unique[i], unique[j], min_calls=min_calls)
            if not reasons:
                return []
            reasons_all = reasons
    return reasons_all or [
        "A3 assert_two_zero_split: no discriminating early/late pair among fixtures"
    ]



# --- trajectory match (field-remix-4 / AgentEvals det slice) ----------------
# Primary (opened 2026-10-03):
#   https://docs.langchain.com/oss/python/langchain/test/evals
# Modes match that page, and this gate also requires order:
#   strict:   actual == expected (extra, missing, or reorder fails)
#   subset:   every actual call is in expected, in order; no extras
#             (a shorter actual is allowed — agent did not exceed scope)
#   superset: every expected call appears in actual, in order; extras allowed
# unordered is not shipped. No LLM judge.

_TRAJECTORY_MODES = frozenset({"strict", "subset", "superset"})
_EXPECTED_TRAJ_KEYS = ("expected", "reference", "reference_outputs")
_ACTUAL_TRAJ_KEYS = ("actual", "outputs")
_JUDGE_SCORE_KEYS = ("score", "judge", "judge_score", "llm_score", "trajectory_score")


def _canonical_args(args: Any) -> str:
    return json.dumps(args, sort_keys=True, default=str)


def _call_pin(entry: Any) -> tuple[str, str | None] | None:
    """(name, canonical args or None when the call does not pin args)."""
    name = _tool_name(entry)
    if name is None:
        return None
    args = _tool_args(entry)
    if args is None:
        return name, None
    return name, _canonical_args(args)


def _calls_match(expected: tuple[str, str | None], actual: tuple[str, str | None]) -> bool:
    if expected[0] != actual[0]:
        return False
    if expected[1] is None:
        return True
    return expected[1] == actual[1]


def _as_subsequence(expected: list[tuple[str, str | None]], actual: list[tuple[str, str | None]]) -> bool:
    """True when every expected call appears in actual, in order. Extras allowed (superset)."""
    j = 0
    for exp in expected:
        while j < len(actual) and not _calls_match(exp, actual[j]):
            j += 1
        if j == len(actual):
            return False
        j += 1
    return True


def _fmt_call(pin: tuple[str, str | None]) -> str:
    if pin[1] is None:
        return pin[0]
    return f"{pin[0]}{pin[1]}"


def _superset_breaks(
    expected: list[tuple[str, str | None]],
    actual: list[tuple[str, str | None]],
    exp_s: list[str],
) -> list[str]:
    """Labels for expected calls that are missing or out of order in actual."""
    j = 0
    broken: list[str] = []
    for exp, label in zip(expected, exp_s):
        k = j
        while k < len(actual) and not _calls_match(exp, actual[k]):
            k += 1
        if k < len(actual):
            j = k + 1
            continue
        earlier = any(_calls_match(exp, actual[t]) for t in range(j))
        if earlier:
            broken.append(f"reorder:{label}")
        else:
            broken.append(f"missing:{label}")
    return broken


def _subset_breaks(
    expected: list[tuple[str, str | None]],
    actual: list[tuple[str, str | None]],
    act_s: list[str],
) -> list[str]:
    """Labels for actual calls that are extras or out of order vs expected.

    Empty means actual is an order-preserving subsequence of expected (no extras).
    Missing expected calls are allowed.
    """
    i = 0
    consumed: set[int] = set()
    broken: list[str] = []
    for act, label in zip(actual, act_s):
        k = i
        while k < len(expected) and not _calls_match(expected[k], act):
            k += 1
        if k < len(expected):
            consumed.add(k)
            i = k + 1
            continue
        skipped = any(
            t not in consumed and _calls_match(expected[t], act) for t in range(i)
        )
        if skipped:
            broken.append(f"reorder:{label}")
        else:
            broken.append(f"extra:{label}")
    return broken


def _format_breaks(mode: str, broken: list[str], act_s: list[str], exp_s: list[str]) -> list[str]:
    if any(b.startswith("extra:") for b in broken):
        kind = "extra tool call(s)"
        detail = [b.split(":", 1)[1] for b in broken if b.startswith("extra:")]
    elif any(b.startswith("reorder:") for b in broken):
        kind = "reorder"
        detail = [b.split(":", 1)[1] for b in broken if b.startswith("reorder:")]
    else:
        kind = "missing expected tool call(s)"
        detail = [b.split(":", 1)[1] for b in broken]
    return [f"{mode}: {kind}: {detail}; actual {act_s} expected {exp_s}"]


def check_trajectory(path: Path, *, mode: str) -> list[str]:
    """Deterministic expected-vs-actual tool trajectory. No judge, no network.

    strict: same calls, same order, no extras.
    subset: every actual call is in expected, in order; no extras.
    superset: every expected call appears in actual, in order; extras allowed.
    A judge/score field never authorizes a pass.
    """
    if mode not in _TRAJECTORY_MODES:
        return [
            f"unknown trajectory mode {mode!r}; this gate accepts strict|subset|superset only "
            "(unordered is not shipped)"
        ]

    records = _load_json_or_jsonl(path)
    last = records[-1]
    reasons: list[str] = []

    expected_raw, expected_key = _extract_tool_list(last, _EXPECTED_TRAJ_KEYS)
    actual_raw, actual_key = _extract_tool_list(last, _ACTUAL_TRAJ_KEYS)
    judge_present = any(k in last for k in _JUDGE_SCORE_KEYS)

    if expected_raw is None or actual_raw is None:
        if judge_present and expected_raw is None and actual_raw is None:
            return [
                "judge-only trajectory score is not a gate (missing expected and actual)"
            ]
        if expected_raw is None:
            reasons.append("missing expected (or reference / reference_outputs)")
        if actual_raw is None:
            reasons.append("missing actual (or outputs)")
        return reasons

    if not isinstance(expected_raw, list):
        reasons.append(f"{expected_key} must be a list, got {type(expected_raw).__name__}")
    if not isinstance(actual_raw, list):
        reasons.append(f"{actual_key} must be a list, got {type(actual_raw).__name__}")
    if reasons:
        return reasons

    assert isinstance(expected_raw, list) and isinstance(actual_raw, list)
    if len(expected_raw) == 0:
        return ["empty expected trajectory — fail-closed (no vacuous pass)"]

    expected: list[tuple[str, str | None]] = []
    for i, entry in enumerate(expected_raw):
        pin = _call_pin(entry)
        if pin is None:
            reasons.append(f"expected[{i}] has no usable tool name")
        else:
            expected.append(pin)

    actual: list[tuple[str, str | None]] = []
    for i, entry in enumerate(actual_raw):
        pin = _call_pin(entry)
        if pin is None:
            reasons.append(f"actual[{i}] has no usable tool name")
        else:
            actual.append(pin)
    if reasons:
        return reasons

    exp_s = [_fmt_call(c) for c in expected]
    act_s = [_fmt_call(c) for c in actual]
    superset_ok = _as_subsequence(expected, actual)

    if mode == "strict":
        pairwise = len(expected) == len(actual) and all(
            _calls_match(e, a) for e, a in zip(expected, actual)
        )
        if pairwise:
            return []
        if superset_ok and len(actual) > len(expected):
            return [
                "strict: extra tool call(s); actual "
                f"{act_s} != expected {exp_s}"
            ]
        if len(expected) == len(actual) and sorted(exp_s) == sorted(act_s):
            return [
                f"strict: reorder; actual {act_s} != expected {exp_s}"
            ]
        if not superset_ok:
            broken = _superset_breaks(expected, actual, exp_s)
            missing = [b.split(":", 1)[1] for b in broken if b.startswith("missing:")]
            if any(b.startswith("reorder:") for b in broken) and len(actual) >= len(expected):
                return [
                    f"strict: reorder or mismatch; missing in order {missing or exp_s}; "
                    f"actual {act_s} != expected {exp_s}"
                ]
            return [
                f"strict: missing expected tool call(s) {missing or exp_s}; "
                f"actual {act_s}"
            ]
        return [f"strict: trajectory mismatch; actual {act_s} != expected {exp_s}"]

    if mode == "superset":
        if superset_ok:
            return []
        return _format_breaks("superset", _superset_breaks(expected, actual, exp_s), act_s, exp_s)

    # subset: no extras; actual is an ordered subsequence of expected
    broken = _subset_breaks(expected, actual, act_s)
    if not broken:
        return []
    return _format_breaks("subset", broken, act_s, exp_s)


# --- CLI wiring -------------------------------------------------------------

def _run_check(name: str, path: Path, checker) -> int:
    try:
        reasons = checker(path)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"FAIL {name}: {path}: {exc}", file=sys.stderr)
        return 1
    if reasons:
        print(f"FAIL {name}: {path}", file=sys.stderr)
        for r in reasons:
            print(f"  - {r}", file=sys.stderr)
        return 1
    print(f"PASS {name}: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="homi-gate",
        description="Fail-closed CI gates: completion bit, handoff, MCP allowlist, tool correctness, spans (A2E), trajectory.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_comp = sub.add_parser("check-completion", help="Fail if run receipt is truncated/incomplete")
    p_comp.add_argument("path", type=Path, help="JSON or JSONL run receipt")

    p_hand = sub.add_parser("check-handoff", help="Validate handoff payload schema + non-null fields")
    p_hand.add_argument("path", type=Path, help="JSON handoff payload")

    p_mcp = sub.add_parser(
        "check-mcp-allowlist",
        help="Validate MCP config has allowlist+denylist (or enabled:false + named tools)",
    )
    p_mcp.add_argument("path", type=Path, help="YAML or JSON MCP toolset config")

    p_tools = sub.add_parser(
        "check-tools",
        help="Fail if tools_called vs expected_tools mismatches (wrong-tool=0; field-remix)",
    )
    p_tools.add_argument("path", type=Path, help="JSON or JSONL tool-call receipt")
    p_tools.add_argument(
        "--exact-args",
        action="store_true",
        default=False,
        help="Also require matching args/input for expected tools that declare them (default: names-only)",
    )

    p_spans = sub.add_parser(
        "check-spans",
        help="A2E thin det (field-remix-3): A1 span_tree_min + A2 tool_invocation_valid; "
        "optional --two-zero for A3 early-stall vs late-malform split",
    )
    p_spans.add_argument(
        "paths",
        type=Path,
        nargs="*",
        help="Span receipt JSON/JSONL (A1+A2), or with --two-zero: pair/dir of correctness=0 fixtures",
    )
    p_spans.add_argument(
        "--two-zero",
        action="store_true",
        default=False,
        help="A3 assert_two_zero_split: require early stall vs late tool malform discrimination",
    )
    p_spans.add_argument(
        "--min-calls",
        type=int,
        default=_DEFAULT_EARLY_STALL_MIN_CALLS,
        help=f"A3 early-stall minimum tool_call_count (default {_DEFAULT_EARLY_STALL_MIN_CALLS})",
    )

    p_traj = sub.add_parser(
        "check-trajectory",
        help="Fail unless actual tool trajectory matches expected (strict, subset, or superset). "
        "No LLM. Judge score is ignored.",
    )
    p_traj.add_argument("path", type=Path, help="JSON or JSONL expected-vs-actual trajectory")
    p_traj.add_argument(
        "--mode",
        required=True,
        choices=sorted(_TRAJECTORY_MODES),
        help="strict: actual equals expected, in order. "
        "subset: every actual call is in expected, in order, no extras. "
        "superset: every expected call appears in actual, in order; extras allowed",
    )

    args = parser.parse_args(argv)
    if args.command == "check-completion":
        return _run_check("check-completion", args.path, check_completion)
    if args.command == "check-handoff":
        return _run_check("check-handoff", args.path, check_handoff)
    if args.command == "check-mcp-allowlist":
        return _run_check("check-mcp-allowlist", args.path, check_mcp_allowlist)
    if args.command == "check-tools":
        return _run_check(
            "check-tools",
            args.path,
            lambda p: check_tools(p, exact_args=args.exact_args),
        )
    if args.command == "check-trajectory":
        return _run_check(
            f"check-trajectory --mode {args.mode}",
            args.path,
            lambda p: check_trajectory(p, mode=args.mode),
        )
    if args.command == "check-spans":
        if args.two_zero:
            if not args.paths:
                print("FAIL check-spans: --two-zero requires path(s) or a directory", file=sys.stderr)
                return 1
            try:
                reasons = assert_two_zero_split_paths(args.paths, min_calls=args.min_calls)
            except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
                print(f"FAIL check-spans --two-zero: {exc}", file=sys.stderr)
                return 1
            label = " ".join(str(p) for p in args.paths)
            if reasons:
                print(f"FAIL check-spans --two-zero (A3): {label}", file=sys.stderr)
                for r in reasons:
                    print(f"  - {r}", file=sys.stderr)
                return 1
            print(f"PASS check-spans --two-zero (A3): {label}")
            return 0
        if len(args.paths) != 1:
            print(
                "FAIL check-spans: provide exactly one span receipt (or use --two-zero)",
                file=sys.stderr,
            )
            return 1
        return _run_check("check-spans", args.paths[0], check_spans)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
