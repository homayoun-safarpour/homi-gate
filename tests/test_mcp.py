import json
from pathlib import Path

from homi_gate.cli import check_mcp_allowlist, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_mcp_ok():
    assert check_mcp_allowlist(EXAMPLES / "mcp_ok.yaml") == []


def test_mcp_disabled_ok():
    assert check_mcp_allowlist(EXAMPLES / "mcp_disabled_ok.yaml") == []


def test_mcp_bad():
    reasons = check_mcp_allowlist(EXAMPLES / "mcp_bad.yaml")
    assert reasons
    joined = " ".join(reasons)
    assert "allowlist" in joined
    assert "denylist" in joined or "blocklist" in joined


def test_cli_mcp_pass():
    assert main(["check-mcp-allowlist", str(EXAMPLES / "mcp_ok.yaml")]) == 0


def test_cli_mcp_fail():
    assert main(["check-mcp-allowlist", str(EXAMPLES / "mcp_bad.yaml")]) == 1


def test_overlap_fail(tmp_path: Path):
    p = tmp_path / "overlap.yaml"
    p.write_text(
        "mcp:\n  allowlist: [a, b]\n  denylist: [b, c]\n",
        encoding="utf-8",
    )
    reasons = check_mcp_allowlist(p)
    assert any("both allowlist and denylist" in r for r in reasons)


def test_empty_allowlist_fail(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text('{"mcp": {"allowlist": [], "denylist": []}}', encoding="utf-8")
    reasons = check_mcp_allowlist(p)
    assert any("empty" in r for r in reasons)


def test_wildcard_allowlist_entry_fails(tmp_path: Path):
    for entry in ("*", "fs_*", "read?", "[a-z]+", "all", "ANY"):
        p = tmp_path / "wild.json"
        p.write_text(json.dumps({"allowlist": ["read", entry], "denylist": ["rm"]}), encoding="utf-8")
        reasons = check_mcp_allowlist(p)
        assert any("wildcard" in r for r in reasons), entry
        assert main(["check-mcp-allowlist", str(p)]) == 1


def test_wildcard_named_tool_with_enabled_false_fails(tmp_path: Path):
    p = tmp_path / "wild_off.json"
    p.write_text('{"enabled": false, "tools": ["*"]}', encoding="utf-8")
    assert any("wildcard" in r for r in check_mcp_allowlist(p))


def test_empty_denylist_is_allowed(tmp_path: Path):
    p = tmp_path / "m2.json"
    p.write_text('{"allowlist": ["read"], "denylist": []}', encoding="utf-8")
    assert check_mcp_allowlist(p) == []
    assert main(["check-mcp-allowlist", str(p)]) == 0


def test_null_denylist_still_fails(tmp_path: Path):
    p = tmp_path / "m2n.json"
    p.write_text('{"allowlist": ["read"], "denylist": null}', encoding="utf-8")
    assert any("missing denylist" in r for r in check_mcp_allowlist(p))


def test_invalid_yaml_prints_fail_line_not_traceback(tmp_path: Path, capsys):
    p = tmp_path / "m3.yaml"
    p.write_text("allowlist: [a\n", encoding="utf-8")
    assert main(["check-mcp-allowlist", str(p)]) == 1
    err = capsys.readouterr().err
    assert err.startswith(f"FAIL check-mcp-allowlist: {p}: invalid YAML")
    assert "Traceback" not in err
