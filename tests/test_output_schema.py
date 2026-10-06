"""MCP CallToolResult outputSchema fail-closed (forge-outputschema).

When a tool declares outputSchema and isError is false/omitted, validate
structuredContent with jsonschema. isError true wins and skips schema.
No outputSchema + unstructured text stays green (yesterday's control).

Patterns from:
- https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- modelcontextprotocol/python-sdk tests/client/test_output_schema_validation.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from homi_gate.cli import (
    REASON_IS_ERROR,
    REASON_MISSING_STRUCTURED,
    REASON_SCHEMA_MISMATCH,
    evaluate_tool_result,
    main,
)

ADA_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}

ADA_TOOL = {
    "name": "get_user",
    "description": "Get user data",
    "inputSchema": {"type": "object"},
    "outputSchema": ADA_SCHEMA,
}

FX = Path(__file__).resolve().parent.parent / "examples" / "mcp_tool_result"
BAD = FX / "invalid-tool-input-error.json"
OK = FX / "result-with-unstructured-text.json"


def _reasons(result: dict, tool: dict | None = None) -> list[str]:
    return evaluate_tool_result(result, tool)


def _codes(reasons: list[str]) -> set[str]:
    found: set[str] = set()
    for r in reasons:
        for code in (REASON_IS_ERROR, REASON_SCHEMA_MISMATCH, REASON_MISSING_STRUCTURED):
            if f"{code}:" in r or f": {code}:" in r:
                found.add(code)
    return found


def _result(
    *,
    structured=None,
    structured_absent: bool = False,
    is_error=None,
    text: str = "ok",
) -> dict:
    body: dict = {
        "content": [{"type": "text", "text": text}],
    }
    if not structured_absent and structured is not None:
        body["structuredContent"] = structured
    # structured_absent => do not set the key at all
    if is_error is not None:
        body["isError"] = is_error
    return body


# --- R1–R6 + traps (Learn Next LN-MORNING-2026-10-06) -----------------------


def test_r1_valid_ada_exit_0():
    """R1 structuredContent {name:'Ada', age:36}, isError omitted → exit 0."""
    reasons = _reasons(_result(structured={"name": "Ada", "age": 36}), ADA_TOOL)
    assert reasons == []


def test_r2_age_as_string_schema_mismatch():
    """R2 {name:'Ada', age:'36'} → exit 1 schema_mismatch."""
    reasons = _reasons(
        _result(structured={"name": "Ada", "age": "36"}, is_error=False),
        ADA_TOOL,
    )
    assert reasons
    assert _codes(reasons) == {REASON_SCHEMA_MISMATCH}


def test_r3_age_missing_schema_mismatch():
    """R3 {name:'Ada'} age missing → exit 1 schema_mismatch."""
    reasons = _reasons(
        _result(structured={"name": "Ada"}, is_error=False),
        ADA_TOOL,
    )
    assert reasons
    assert _codes(reasons) == {REASON_SCHEMA_MISMATCH}


def test_r4_missing_structured_content():
    """R4 schema declared, no structuredContent, isError false → missing_structured."""
    reasons = _reasons(
        _result(structured_absent=True, is_error=False),
        ADA_TOOL,
    )
    assert reasons
    assert _codes(reasons) == {REASON_MISSING_STRUCTURED}


def test_r5_is_error_skips_schema():
    """R5 isError true with text, no structuredContent → is_error (skip schema)."""
    reasons = _reasons(
        _result(structured_absent=True, is_error=True, text="boom"),
        ADA_TOOL,
    )
    assert reasons
    assert _codes(reasons) == {REASON_IS_ERROR}
    assert REASON_MISSING_STRUCTURED not in _codes(reasons)
    assert REASON_SCHEMA_MISMATCH not in _codes(reasons)


def test_r6_no_output_schema_unstructured_ok():
    """R6 tool with no outputSchema, unstructured text only → exit 0."""
    tool = {
        "name": "get_weather",
        "inputSchema": {"type": "object"},
        # no outputSchema
    }
    reasons = _reasons(
        _result(structured_absent=True, is_error=False, text="72F partly cloudy"),
        tool,
    )
    assert reasons == []


def test_trap_a_extra_field_without_additional_properties_false_passes():
    """Trap A: extra field OK when additionalProperties not false."""
    reasons = _reasons(
        _result(structured={"name": "Ada", "age": 36, "extra": 1}),
        ADA_TOOL,
    )
    assert reasons == []


def test_trap_b_valid_text_invalid_structured_still_fails():
    """Trap B: valid-looking JSON text does not rescue invalid structuredContent."""
    text = json.dumps({"name": "Ada", "age": 36})
    reasons = _reasons(
        _result(
            structured={"name": "Ada", "age": "36"},  # invalid
            is_error=False,
            text=text,
        ),
        ADA_TOOL,
    )
    assert reasons
    assert _codes(reasons) == {REASON_SCHEMA_MISMATCH}


# --- CLI wiring + official fixtures ----------------------------------------


def test_cli_r1_via_combined_receipt(tmp_path: Path):
    p = tmp_path / "r1.json"
    p.write_text(
        json.dumps(
            {
                "tool": ADA_TOOL,
                "result": {
                    "content": [{"type": "text", "text": "ok"}],
                    "structuredContent": {"name": "Ada", "age": 36},
                },
            }
        ),
        encoding="utf-8",
    )
    assert main(["check-tool-result", str(p)]) == 0


def test_cli_r2_via_tool_flag(tmp_path: Path, capsys):
    tool_p = tmp_path / "tool.json"
    result_p = tmp_path / "result.json"
    tool_p.write_text(json.dumps(ADA_TOOL), encoding="utf-8")
    result_p.write_text(
        json.dumps(
            {
                "content": [{"type": "text", "text": "x"}],
                "structuredContent": {"name": "Ada", "age": "36"},
                "isError": False,
            }
        ),
        encoding="utf-8",
    )
    assert main(["check-tool-result", str(result_p), "--tool", str(tool_p)]) == 1
    err = capsys.readouterr().err
    assert REASON_SCHEMA_MISMATCH in err


def test_cli_r4_missing_structured(tmp_path: Path, capsys):
    p = tmp_path / "r4.json"
    p.write_text(
        json.dumps(
            {
                "tool": ADA_TOOL,
                "result": {
                    "content": [{"type": "text", "text": "x"}],
                    "isError": False,
                },
            }
        ),
        encoding="utf-8",
    )
    assert main(["check-tool-result", str(p)]) == 1
    assert REASON_MISSING_STRUCTURED in capsys.readouterr().err


def test_cli_r5_is_error_with_schema_declared(tmp_path: Path, capsys):
    p = tmp_path / "r5.json"
    p.write_text(
        json.dumps(
            {
                "tool": ADA_TOOL,
                "result": {
                    "content": [{"type": "text", "text": "Invalid input"}],
                    "isError": True,
                },
            }
        ),
        encoding="utf-8",
    )
    assert main(["check-tool-result", str(p)]) == 1
    err = capsys.readouterr().err
    assert REASON_IS_ERROR in err
    assert "isError" in err
    assert REASON_MISSING_STRUCTURED not in err


def test_official_is_error_fixture_still_fails(capsys):
    payload = json.loads(BAD.read_text(encoding="utf-8"))
    assert payload["isError"] is True and payload["content"]
    assert main(["check-tool-result", str(BAD)]) == 1
    assert "isError" in capsys.readouterr().err


def test_official_unstructured_pass_fixture_exits_0():
    assert json.loads(OK.read_text(encoding="utf-8"))["isError"] is False
    assert main(["check-tool-result", str(OK)]) == 0


@pytest.mark.parametrize(
    "structured, expect_code",
    [
        ({"name": "Ada", "age": "invalid"}, REASON_SCHEMA_MISMATCH),  # SDK age-invalid
        ({"name": "John", "age": 30}, None),  # missing email would need larger schema
    ],
)
def test_crosscheck_sdk_style_age_invalid(structured, expect_code):
    """Cross-check R2-style fail against python-sdk invalid age pattern."""
    reasons = _reasons(_result(structured=structured, is_error=False), ADA_TOOL)
    if expect_code is None:
        assert reasons == []
    else:
        assert _codes(reasons) == {expect_code}
