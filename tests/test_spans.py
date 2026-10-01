"""field-remix-3 / A2E thin det asserts A1–A3 (no LLM)."""

from pathlib import Path

from homi_gate.cli import (
    assert_span_tree_min,
    assert_tool_invocation_valid,
    assert_two_zero_split,
    assert_two_zero_split_paths,
    check_spans,
    main,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_span_ok_a1_a2():
    assert check_spans(EXAMPLES / "span_ok.json") == []


def test_span_missing_tool_a1_fail():
    reasons = check_spans(EXAMPLES / "span_missing_tool.json")
    assert reasons
    joined = " ".join(reasons)
    assert "A1" in joined
    assert "missing tool span" in joined or "no tool spans" in joined


def test_tool_malform_a2_fail():
    reasons = check_spans(EXAMPLES / "tool_malform.json")
    assert reasons
    joined = " ".join(reasons)
    assert "A2" in joined
    assert "empty" in joined or "status" in joined or "args" in joined


def test_cli_spans_pass():
    assert main(["check-spans", str(EXAMPLES / "span_ok.json")]) == 0


def test_cli_spans_missing_exit_1():
    assert main(["check-spans", str(EXAMPLES / "span_missing_tool.json")]) == 1


def test_cli_spans_malform_exit_1():
    assert main(["check-spans", str(EXAMPLES / "tool_malform.json")]) == 1


def test_two_zero_split_pass():
    reasons = assert_two_zero_split(
        EXAMPLES / "zero_early_stall.json",
        EXAMPLES / "zero_late_tool_malform.json",
    )
    assert reasons == []


def test_cli_two_zero_pass():
    assert (
        main(
            [
                "check-spans",
                "--two-zero",
                str(EXAMPLES / "zero_early_stall.json"),
                str(EXAMPLES / "zero_late_tool_malform.json"),
            ]
        )
        == 0
    )


def test_cli_two_zero_dir_pass():
    # Directory mode picks zero_* fixtures under examples/
    assert main(["check-spans", "--two-zero", str(EXAMPLES)]) == 0


def test_two_zero_identical_theater(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    body = (
        '{"correctness": 0, "plan_complete": false, '
        '"tool_call_count": 12, "unique_tools": 1, '
        '"tool_invocation_valid": true}'
    )
    a.write_text(body, encoding="utf-8")
    b.write_text(body, encoding="utf-8")
    reasons = assert_two_zero_split(a, b)
    assert reasons
    joined = " ".join(reasons)
    assert "identical" in joined or "missing late" in joined or "early stall" in joined


def test_two_zero_non_zero_fails(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(
        '{"correctness": 1, "plan_complete": false, '
        '"tool_call_count": 12, "unique_tools": 1}',
        encoding="utf-8",
    )
    b.write_text(
        '{"correctness": 0, "plan_complete": true, '
        '"tool_call_count": 3, "unique_tools": 2, '
        '"tool_invocation_valid": false}',
        encoding="utf-8",
    )
    reasons = assert_two_zero_split(a, b)
    assert any("correctness != 0" in r for r in reasons)


def test_a1_skipped_when_no_tool_claim(tmp_path: Path):
    p = tmp_path / "no_claim.json"
    p.write_text('{"spans": [], "tool_use": false}', encoding="utf-8")
    rec = {"spans": [], "tool_use": False}
    assert assert_span_tree_min(rec) == []
    assert assert_tool_invocation_valid(rec) == []


def test_flat_parent_id_spans(tmp_path: Path):
    p = tmp_path / "flat.json"
    p.write_text(
        """{
          "tool_use": true,
          "spans": [
            {"span_id": "p", "name": "agent.run", "kind": "agent", "status": "ok"},
            {"span_id": "t", "parent_id": "p", "name": "search", "kind": "tool",
             "status": "ok", "args": {"q": "x"}}
          ]
        }""",
        encoding="utf-8",
    )
    assert check_spans(p) == []


def test_assert_two_zero_paths_pair():
    assert (
        assert_two_zero_split_paths(
            [
                EXAMPLES / "zero_early_stall.json",
                EXAMPLES / "zero_late_tool_malform.json",
            ]
        )
        == []
    )
