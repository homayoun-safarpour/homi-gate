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
