from pathlib import Path

from homi_gate.cli import check_completion, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_pass_json():
    assert check_completion(EXAMPLES / "pass.json") == []


def test_pass_jsonl():
    assert check_completion(EXAMPLES / "pass.jsonl") == []


def test_fail_truncated():
    reasons = check_completion(EXAMPLES / "fail.json")
    assert reasons
    assert any("completion_bit" in r or "truncated" in r or "incomplete" in r for r in reasons)


def test_soft_done_no_artifact():
    """status DONE / complete (even with bit) without proof path → soft DONE fail."""
    reasons = check_completion(EXAMPLES / "soft_done_no_artifact.json")
    assert reasons
    assert any("soft DONE" in r for r in reasons)


def test_cli_soft_done_exit_1():
    assert main(["check-completion", str(EXAMPLES / "soft_done_no_artifact.json")]) == 1


def test_doppelganger_stream_veto():
    """Truncated mid-stream + green final: stream-wide veto (not final-record-wins)."""
    reasons = check_completion(EXAMPLES / "doppelganger.jsonl")
    assert reasons
    assert any("truncated=true before final record" in r for r in reasons)


def test_cli_doppelganger_exit_1():
    assert main(["check-completion", str(EXAMPLES / "doppelganger.jsonl")]) == 1


def test_cli_pass_exit_0():
    assert main(["check-completion", str(EXAMPLES / "pass.json")]) == 0


def test_cli_fail_exit_1():
    assert main(["check-completion", str(EXAMPLES / "fail.json")]) == 1


def test_status_only_complete_is_soft_done(tmp_path: Path):
    p = tmp_path / "soft.json"
    p.write_text('{"status": "completed"}', encoding="utf-8")
    reasons = check_completion(p)
    assert any("soft DONE" in r for r in reasons)


def test_bit_true_without_artifact_is_soft_done(tmp_path: Path):
    p = tmp_path / "bit_only.json"
    p.write_text('{"completion_bit": true, "status": "completed"}', encoding="utf-8")
    reasons = check_completion(p)
    assert any("soft DONE" in r for r in reasons)


def test_status_with_artifact_passes(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(
        '{"status": "done", "artifact_path": "artifacts/run-1/out.txt"}',
        encoding="utf-8",
    )
    assert check_completion(p) == []


def test_missing_bit_and_status(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text('{"run_id": "x"}', encoding="utf-8")
    reasons = check_completion(p)
    assert any("missing" in r for r in reasons)
