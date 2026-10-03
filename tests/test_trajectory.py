"""field-remix-4 / AgentEvals trajectory match, det slice (no LLM).

Modes follow https://docs.langchain.com/oss/python/langchain/test/evals
and keep order: strict (equal), subset (no extras), superset (extras allowed).
"""

from pathlib import Path

from homi_gate.cli import check_trajectory, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_strict_pass():
    assert check_trajectory(EXAMPLES / "trajectory_strict_ok.json", mode="strict") == []


def test_equal_trajectory_passes_every_ordered_mode():
    path = EXAMPLES / "trajectory_strict_ok.json"
    for mode in ("strict", "subset", "superset"):
        assert check_trajectory(path, mode=mode) == [], mode


def test_strict_fail_extra_tool():
    reasons = check_trajectory(EXAMPLES / "trajectory_strict_extra.json", mode="strict")
    assert reasons
    assert "extra" in " ".join(reasons)
    assert "shell_exec" in " ".join(reasons)


def test_superset_pass_with_extra_tool():
    assert check_trajectory(EXAMPLES / "trajectory_strict_extra.json", mode="superset") == []


def test_subset_fail_extra_tool():
    reasons = check_trajectory(EXAMPLES / "trajectory_strict_extra.json", mode="subset")
    assert reasons
    joined = " ".join(reasons)
    assert "extra" in joined
    assert "shell_exec" in joined


def test_subset_pass_when_actual_omits_expected():
    assert check_trajectory(EXAMPLES / "trajectory_missing_expected.json", mode="subset") == []


def test_superset_fail_missing_expected():
    reasons = check_trajectory(EXAMPLES / "trajectory_missing_expected.json", mode="superset")
    assert reasons
    joined = " ".join(reasons)
    assert "missing" in joined
    assert "authorize" in joined


def test_reorder_fails_strict_subset_and_superset():
    path = EXAMPLES / "trajectory_reorder.json"
    for mode in ("strict", "subset", "superset"):
        text = " ".join(check_trajectory(path, mode=mode))
        assert "reorder" in text, mode


def test_judge_only_does_not_pass():
    path = EXAMPLES / "trajectory_judge_only.json"
    reasons = check_trajectory(path, mode="strict")
    assert reasons
    assert "judge-only" in " ".join(reasons)
    assert main(["check-trajectory", "--mode", "subset", str(path)]) == 1
    assert main(["check-trajectory", "--mode", "superset", str(path)]) == 1


def test_cli_modes_on_extra_and_missing():
    ok = EXAMPLES / "trajectory_strict_ok.json"
    extra = EXAMPLES / "trajectory_strict_extra.json"
    missing = EXAMPLES / "trajectory_missing_expected.json"
    assert main(["check-trajectory", "--mode", "strict", str(ok)]) == 0
    assert main(["check-trajectory", "--mode", "strict", str(extra)]) == 1
    assert main(["check-trajectory", "--mode", "subset", str(extra)]) == 1
    assert main(["check-trajectory", "--mode", "superset", str(extra)]) == 0
    assert main(["check-trajectory", "--mode", "subset", str(missing)]) == 0
    assert main(["check-trajectory", "--mode", "superset", str(missing)]) == 1
    assert main(["check-trajectory", "--mode", "strict", str(missing)]) == 1


def test_args_mismatch_fails_even_with_score(tmp_path: Path):
    p = tmp_path / "args.json"
    p.write_text(
        '{"score": true, "expected": [{"name": "lookup_policy", "args": {"id": "p1"}}],'
        ' "actual": [{"name": "lookup_policy", "args": {"id": "other"}}]}',
        encoding="utf-8",
    )
    assert check_trajectory(p, mode="strict")
    assert check_trajectory(p, mode="subset")
    assert check_trajectory(p, mode="superset")


def test_unknown_mode_not_aliased(tmp_path: Path):
    p = tmp_path / "t.json"
    p.write_text('{"expected": ["a"], "actual": ["a", "b"]}', encoding="utf-8")
    reasons = check_trajectory(p, mode="unordered")
    assert reasons
    assert "unknown" in reasons[0]
    assert check_trajectory(p, mode="superset") == []
    assert check_trajectory(p, mode="subset")
