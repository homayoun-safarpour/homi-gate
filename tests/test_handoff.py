from pathlib import Path

from homi_gate.cli import check_handoff, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_handoff_ok():
    assert check_handoff(EXAMPLES / "handoff_ok.json") == []


def test_handoff_bad():
    reasons = check_handoff(EXAMPLES / "handoff_bad.json")
    assert reasons
    joined = " ".join(reasons)
    assert "proved is null" in joined
    assert "context is null" in joined
    assert "pending must be one goal" in joined
    assert "stop is empty string" in joined


def test_cli_handoff_pass():
    assert main(["check-handoff", str(EXAMPLES / "handoff_ok.json")]) == 0


def test_cli_handoff_fail():
    assert main(["check-handoff", str(EXAMPLES / "handoff_bad.json")]) == 1


def test_alias_from_to(tmp_path: Path):
    p = tmp_path / "alias.json"
    p.write_text(
        '{"from":"a","to":"b","proved":["x"],"pending":"one","stop":"halt","forbidden":[],"report":"ok"}',
        encoding="utf-8",
    )
    assert check_handoff(p) == []
