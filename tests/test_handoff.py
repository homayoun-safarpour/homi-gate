import json
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


def test_handoff_transcript_dump():
    reasons = check_handoff(EXAMPLES / "handoff_transcript_dump.json")
    assert reasons
    joined = " ".join(reasons)
    assert "context is null" in joined
    assert "transcript dump" in joined
    assert "missing required field" in joined
    assert "transcript.context is null" in joined


def test_cli_handoff_transcript_dump_exit_1():
    assert main(["check-handoff", str(EXAMPLES / "handoff_transcript_dump.json")]) == 1


def test_handoff_soft_null_coerce():
    reasons = check_handoff(EXAMPLES / "handoff_soft_null_coerce.json")
    assert reasons
    assert any("soft-null coerce" in r or "context is empty" in r for r in reasons)


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


_BASE = {
    "from_agent": "a",
    "to_agent": "b",
    "proved": ["x"],
    "pending": "one goal",
    "stop": "s",
    "forbidden": [],
    "report": "r",
}


def _handoff(tmp_path: Path, **over) -> Path:
    p = tmp_path / "h.json"
    p.write_text(json.dumps({**_BASE, **over}), encoding="utf-8")
    return p


def test_pending_object_or_number_fails(tmp_path: Path):
    for val in ({}, {"goal": "x"}, 3, True):
        reasons = check_handoff(_handoff(tmp_path, pending=val))
        assert any("pending must be one goal" in r for r in reasons), val


def test_pending_one_item_list_must_hold_non_empty_string(tmp_path: Path):
    assert check_handoff(_handoff(tmp_path, pending=["one goal"])) == []
    for val in ([""], [{}], [None]):
        reasons = check_handoff(_handoff(tmp_path, pending=val))
        assert any("pending must be one goal" in r for r in reasons), val


def test_empty_string_context_fails_like_null(tmp_path: Path):
    p = _handoff(tmp_path, context="  ")
    assert any("context is empty" in r for r in check_handoff(p))
    assert main(["check-handoff", str(p)]) == 1


def test_empty_stop_or_report_container_fails(tmp_path: Path):
    for field in ("stop", "report"):
        for val in ([], {}):
            reasons = check_handoff(_handoff(tmp_path, **{field: val}))
            assert any(f"{field} is empty" in r for r in reasons), (field, val)


def test_limit_empty_proved_and_forbidden_lists_are_allowed(tmp_path: Path):
    """README Limits: an empty proved or forbidden list is an explicit none."""
    assert check_handoff(_handoff(tmp_path, proved=[], forbidden=[])) == []


def test_reviewer_handoff_h1_fails(tmp_path: Path):
    p = _handoff(tmp_path, pending={}, context="")
    assert main(["check-handoff", str(p)]) == 1
