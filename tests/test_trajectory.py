"""field-remix-4 / AgentEvals trajectory match, det slice (no LLM)."""

from pathlib import Path

from homi_gate.cli import check_trajectory, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_strict_pass():
    assert check_trajectory(EXAMPLES / "trajectory_strict_ok.json", mode="strict") == []


def test_strict_fail_extra_tool():
    reasons = check_trajectory(EXAMPLES / "trajectory_strict_extra.json", mode="strict")
    assert reasons
    assert "extra" in " ".join(reasons)
    assert "shell_exec" in " ".join(reasons)


def test_subset_pass_with_extra_tool():
    assert check_trajectory(EXAMPLES / "trajectory_strict_extra.json", mode="subset") == []


def test_subset_fail_missing_expected():
    reasons = check_trajectory(EXAMPLES / "trajectory_subset_missing.json", mode="subset")
    assert reasons
    joined = " ".join(reasons)
    assert "missing" in joined
    assert "authorize" in joined


def test_reorder_fails_strict_and_subset():
    path = EXAMPLES / "trajectory_reorder.json"
    strict = " ".join(check_trajectory(path, mode="strict"))
    subset = " ".join(check_trajectory(path, mode="subset"))
    assert "reorder" in strict
    assert "reorder" in subset


def test_judge_only_does_not_pass():
    path = EXAMPLES / "trajectory_judge_only.json"
    reasons = check_trajectory(path, mode="strict")
    assert reasons
    assert "judge-only" in " ".join(reasons)
    assert main(["check-trajectory", "--mode", "subset", str(path)]) == 1


def test_cli_strict_pass_and_extra_exit():
    ok = EXAMPLES / "trajectory_strict_ok.json"
    extra = EXAMPLES / "trajectory_strict_extra.json"
    assert main(["check-trajectory", "--mode", "strict", str(ok)]) == 0
    assert main(["check-trajectory", "--mode", "strict", str(extra)]) == 1
    assert main(["check-trajectory", "--mode", "subset", str(extra)]) == 0


def test_args_mismatch_fails_even_with_score(tmp_path: Path):
    p = tmp_path / "args.json"
    p.write_text(
        '{"score": true, "expected": [{"name": "lookup_policy", "args": {"id": "p1"}}],'
        ' "actual": [{"name": "lookup_policy", "args": {"id": "other"}}]}',
        encoding="utf-8",
    )
    assert check_trajectory(p, mode="strict")
    assert check_trajectory(p, mode="subset")


def test_unknown_mode_not_aliased(tmp_path: Path):
    p = tmp_path / "t.json"
    p.write_text('{"expected": ["a"], "actual": ["a", "b"]}', encoding="utf-8")
    reasons = check_trajectory(p, mode="superset")
    assert reasons
    assert "unknown" in reasons[0]
