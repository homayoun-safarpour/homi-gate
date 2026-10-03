from pathlib import Path

from homi_gate.cli import check_prewrite, evaluate_prewrite, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_refundable_false_cancel_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_cancel_denied.json")
    assert reasons
    assert any("deny cancel_reservation" in r for r in reasons)


def test_refundable_true_cancel_passes():
    assert check_prewrite(EXAMPLES / "prewrite_cancel_ok.json") == []


def test_passenger_count_change_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_count_change.json")
    assert reasons
    assert any("update_passengers" in r and "ne" in r for r in reasons)


def test_missing_rules_on_write_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_missing_rules.json")
    assert any("missing rules" in r for r in reasons)


def test_judge_only_no_proposed_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_judge_only.json")
    assert reasons
    joined = " ".join(reasons)
    assert "proposed" in joined
    assert "not a gate" in joined


def test_cli_pass_and_fail():
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_cancel_ok.json")]) == 0
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_cancel_denied.json")]) == 1


def test_unchanged_field_denies_change_and_allows_same():
    changed = {
        "proposed": {"name": "update_passengers", "write": True, "args": {"count": 3}},
        "state": {"count": 2},
        "rules": [{"tool": "update_passengers", "deny_if": {"unchanged": "count"}}],
    }
    same = {
        "proposed": {"name": "update_passengers", "write": True, "args": {"count": 2}},
        "state": {"count": 2},
        "rules": [{"tool": "update_passengers", "deny_if": {"unchanged": "count"}}],
    }
    assert any("changed" in r for r in evaluate_prewrite(changed))
    assert evaluate_prewrite(same) == []


def test_forbidden_field_and_readonly_without_covering_rule():
    forbidden = {
        "proposed": {"name": "update_passengers", "write": True, "args": {"ssn": "x", "count": 2}},
        "state": {"count": 2},
        "rules": [{"tool": "update_passengers", "deny_if": {"forbidden": "ssn"}}],
    }
    readonly = {
        "proposed": {"name": "get_reservation", "write": False, "args": {"id": "R1"}},
        "state": {"refundable": False},
        "rules": [],
    }
    assert any("forbidden field ssn" in r for r in evaluate_prewrite(forbidden))
    assert evaluate_prewrite(readonly) == []


def test_uncovered_write_fails_and_judge_does_not_override():
    uncovered = {
        "proposed": {"name": "delete_reservation", "write": True, "args": {}},
        "state": {},
        "rules": [{"tool": "other", "deny_if": {"eq": ["state.x", 1]}}],
        "status": "done",
        "judge": "ACCEPT",
        "comment": "looks good",
    }
    reasons = evaluate_prewrite(uncovered)
    assert any("no covering rule" in r for r in reasons)


def test_state_not_mutated():
    payload = {
        "proposed": {"name": "cancel_reservation", "write": True, "args": {"id": "R1"}},
        "state": {"refundable": False},
        "rules": [
            {"tool": "cancel_reservation", "deny_if": {"eq": ["state.refundable", False]}}
        ],
    }
    before = repr(payload)
    evaluate_prewrite(payload)
    assert repr(payload) == before
