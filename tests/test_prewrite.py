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
    reasons = check_prewrite(EXAMPLES / "prewrite_unchanged.json")
    assert any("changed" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_unchanged.json")]) == 1
    same = {
        "proposed": {"name": "update_passengers", "write": True, "args": {"count": 2}},
        "state": {"count": 2},
        "rules": [{"tool": "update_passengers", "deny_if": {"unchanged": "count"}}],
    }
    assert evaluate_prewrite(same) == []


def test_forbidden_field_fails_and_readonly_without_covering_rule():
    reasons = check_prewrite(EXAMPLES / "prewrite_forbidden.json")
    assert any("forbidden field ssn" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_forbidden.json")]) == 1
    readonly = {
        "proposed": {"name": "get_reservation", "write": False, "args": {"id": "R1"}},
        "state": {"refundable": False},
        "rules": [],
    }
    assert evaluate_prewrite(readonly) == []


def test_uncovered_write_fails_and_judge_does_not_override():
    reasons = check_prewrite(EXAMPLES / "prewrite_uncovered.json")
    assert any("no covering rule" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_uncovered.json")]) == 1


def test_covering_rule_missing_deny_if_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_missing_deny_if.json")
    assert any("missing deny_if" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_missing_deny_if.json")]) == 1


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


def test_unsupported_deny_if_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_unsupported_deny_if.json")
    assert any("unsupported deny_if" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_unsupported_deny_if.json")]) == 1


def test_proposed_name_missing_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_missing_name.json")
    assert any("proposed.name missing" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_missing_name.json")]) == 1


def test_rules_not_list_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_rules_not_list.json")
    assert any("rules must be a list" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_rules_not_list.json")]) == 1

def test_rule_tool_missing_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_missing_tool.json")
    assert any("tool missing" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_missing_tool.json")]) == 1

def test_rule_not_object_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_rule_not_object.json")
    assert any("must be an object" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_rule_not_object.json")]) == 1

def test_proposed_args_not_object_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_args_not_object.json")
    assert any("proposed.args must be an object" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_args_not_object.json")]) == 1

def test_state_not_object_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_state_not_object.json")
    assert any("state must be an object" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_state_not_object.json")]) == 1

def test_eq_path_missing_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_eq_path_missing.json")
    assert any("path missing" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_eq_path_missing.json")]) == 1

def test_eq_bad_arity_fails():
    reasons = check_prewrite(EXAMPLES / "prewrite_eq_bad_arity.json")
    assert any("expects [left, right]" in r for r in reasons)
    assert main(["check-prewrite", str(EXAMPLES / "prewrite_eq_bad_arity.json")]) == 1
