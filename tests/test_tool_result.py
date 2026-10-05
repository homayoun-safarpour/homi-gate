"""MCP CallToolResult: isError true fails even when content is non-empty.

Fixtures are copied verbatim from the official MCP schema examples
(modelcontextprotocol/modelcontextprotocol, schema/2026-07-28/examples/CallToolResult).
A tool that errored still returns text, so a gate that only checks for
non-empty content would wave it through. This one must not.
"""
import json
from pathlib import Path

from homi_gate.cli import main

FX = Path(__file__).resolve().parent.parent / "examples" / "mcp_tool_result"
BAD = FX / "invalid-tool-input-error.json"
OK = FX / "result-with-unstructured-text.json"


def test_is_error_true_fails_even_with_content(capsys):
    payload = json.loads(BAD.read_text(encoding="utf-8"))
    assert payload["isError"] is True and payload["content"]
    assert main(["check-tool-result", str(BAD)]) == 1
    assert "isError" in capsys.readouterr().err


def test_unstructured_text_pass_fixture_exits_0():
    assert json.loads(OK.read_text(encoding="utf-8"))["isError"] is False
    assert main(["check-tool-result", str(OK)]) == 0


def test_omitted_is_error_is_success(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"content": [{"type": "text", "text": "ok"}]}))
    assert main(["check-tool-result", str(p)]) == 0


def test_non_bool_is_error_fails_closed(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"content": [{"type": "text", "text": "x"}], "isError": "true"}))
    assert main(["check-tool-result", str(p)]) == 1