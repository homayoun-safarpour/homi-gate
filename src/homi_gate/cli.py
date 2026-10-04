"""homi-gate CLI - fail-closed checks for completion, handoff, MCP allowlist."""

from __future__ import annotations

import argparse
import json
import sys
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
    if bit is False:
        reasons.append("completion_bit=false")
    elif bit is None:
        status = last.get("status")
        if status is None:
            reasons.append("missing completion_bit/complete and status")
        else:
            status_l = str(status).lower()
            if status_l in _INCOMPLETE_STATUSES:
                reasons.append(f"status={status!r} is incomplete")
            elif status_l not in _COMPLETE_STATUSES:
                reasons.append(f"status={status!r} not a known complete status")
    elif bit is not True:
        reasons.append(f"completion_bit must be bool, got {type(bit).__name__}")

    # Mid-stream truncate flag also fails closed
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
            # proved may be empty list if nothing proved yet - allow, but pending must be set
            pass

    # Explicit anti-pattern from hire signals: context:null with no substitute
    if "context" in payload and payload["context"] is None:
        reasons.append("context is null (pass compact proved/pending/stop instead)")

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
        reasons.append("allowlist is empty - fail-closed requires at least one named tool")
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
        description="Fail-closed CI gates: completion bit, handoff contracts, MCP allowlist.",
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

    args = parser.parse_args(argv)
    if args.command == "check-completion":
        return _run_check("check-completion", args.path, check_completion)
    if args.command == "check-handoff":
        return _run_check("check-handoff", args.path, check_handoff)
    if args.command == "check-mcp-allowlist":
        return _run_check("check-mcp-allowlist", args.path, check_mcp_allowlist)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
