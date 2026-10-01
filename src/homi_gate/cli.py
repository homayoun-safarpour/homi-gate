"""homi-gate CLI — fail-closed checks for completion, handoff, MCP allowlist, tool correctness."""

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
        description="Fail-closed CI gates: completion bit, handoff, MCP allowlist, tool correctness.",
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
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
