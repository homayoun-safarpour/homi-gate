from pathlib import Path

from homi_gate.cli import check_tools, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_tools_ok():
    assert check_tools(EXAMPLES / "tools_ok.json") == []


def test_tools_wrong():
    reasons = check_tools(EXAMPLES / "tools_wrong.json")
    assert reasons
    joined = " ".join(reasons)
    assert "unexpected" in joined or "wrong-tool" in joined
    assert "shell_exec" in joined


def test_tools_missing():
    reasons = check_tools(EXAMPLES / "tools_missing.json")
    assert reasons
    joined = " ".join(reasons)
    assert "missing required tools" in joined
    assert "read_file" in joined
    assert "write_receipt" in joined


def test_cli_tools_pass():
    assert main(["check-tools", str(EXAMPLES / "tools_ok.json")]) == 0


def test_cli_tools_wrong_exit_1():
    assert main(["check-tools", str(EXAMPLES / "tools_wrong.json")]) == 1


def test_cli_tools_missing_exit_1():
    assert main(["check-tools", str(EXAMPLES / "tools_missing.json")]) == 1


def test_empty_expected_fails(tmp_path: Path):
    p = tmp_path / "empty_expected.json"
    p.write_text(
        '{"tools_called": ["search"], "expected_tools": []}',
        encoding="utf-8",
    )
    reasons = check_tools(p)
    assert any("empty expected" in r for r in reasons)


def test_object_form_names_only(tmp_path: Path):
    p = tmp_path / "objects.json"
    p.write_text(
        '{"tools_called": [{"name": "a", "args": {"x": 1}}, {"name": "b"}],'
        ' "expected_tools": ["a", "b"]}',
        encoding="utf-8",
    )
    assert check_tools(p) == []


def test_exact_args_mismatch(tmp_path: Path):
    p = tmp_path / "args.json"
    p.write_text(
        '{"tools_called": [{"name": "search", "args": {"q": "wrong"}}],'
        ' "expected_tools": [{"name": "search", "args": {"q": "right"}}]}',
        encoding="utf-8",
    )
    assert check_tools(p) == []  # names-only default
    reasons = check_tools(p, exact_args=True)
    assert any("exact-args" in r for r in reasons)


def test_exact_args_match(tmp_path: Path):
    p = tmp_path / "args_ok.json"
    p.write_text(
        '{"tools_called": [{"name": "search", "args": {"q": "right"}}],'
        ' "expected_tools": [{"name": "search", "args": {"q": "right"}}]}',
        encoding="utf-8",
    )
    assert check_tools(p, exact_args=True) == []


def test_expected_allowlist_alias(tmp_path: Path):
    p = tmp_path / "alias.json"
    p.write_text(
        '{"tools_called": ["a"], "expected_allowlist": ["a"]}',
        encoding="utf-8",
    )
    assert check_tools(p) == []
