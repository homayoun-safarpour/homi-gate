"""The guarded dispatcher must execute the call accepted by the checker."""
from copy import deepcopy

import pytest

from homi_gate.cli import evaluate_prewrite
from homi_gate.guard import Denied, run_guarded


def receipt(name="record", args=None):
    return {
        "proposed": {"name": name, "args": args},
        "state": {"blocked": False},
        "rules": [{"tool": "record", "deny_if": {"eq": ["state.blocked", True]}}],
    }


@pytest.mark.parametrize("name", ["record", " record ", "\trecord\n"])
@pytest.mark.parametrize("args", [None, {}, {"item": "sample"}])
def test_dispatch_uses_the_checked_name_and_arguments(name, args):
    payload = receipt(name, args)
    original = deepcopy(payload)
    calls = []

    def record(**kwargs):
        calls.append(kwargs)
        return "recorded"

    assert evaluate_prewrite(payload) == []
    assert run_guarded(payload, {"record": record}) == "recorded"
    assert calls == [args if args is not None else {}]
    assert payload == original


def test_omitted_arguments_still_dispatch_as_empty_mapping():
    payload = receipt()
    del payload["proposed"]["args"]
    assert run_guarded(payload, {"record": lambda **kw: kw}) == {}


@pytest.mark.parametrize("args", [[], "text", 0, False])
def test_malformed_arguments_do_not_call_the_tool(args):
    calls = []
    with pytest.raises(Denied):
        run_guarded(receipt(args=args), {"record": lambda **kw: calls.append(kw)})
    assert calls == []


def test_normalization_does_not_bypass_a_denial():
    payload = receipt(" record ", None)
    payload["state"]["blocked"] = True
    calls = []
    with pytest.raises(Denied):
        run_guarded(payload, {"record": lambda **kw: calls.append(kw)})
    assert calls == []


def test_unregistered_tool_is_denied():
    with pytest.raises(Denied, match="no tool registered"):
        run_guarded(receipt(args={}), {})


def test_registered_tool_error_is_not_reported_as_success():
    def record(**kwargs):
        raise RuntimeError("tool failed")

    with pytest.raises(RuntimeError, match="tool failed"):
        run_guarded(receipt(args={}), {"record": record})
