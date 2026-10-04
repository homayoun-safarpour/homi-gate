"""Live stop: a denied write never runs, and the run does not continue.

Recipe copied from the pre-tool-use hook pattern: check before the call,
block on deny. The spy tool writes a real file, so a tool that ran leaves
evidence the test can see.
"""
import json
from pathlib import Path

import pytest

from homi_gate.guard import Denied, run_guarded

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _agent(payload, ledger, calls):
    def write_tool(**kw):
        calls.append(payload["proposed"]["name"])
        ledger.write_text(json.dumps(kw))

    def run():
        run_guarded(payload, {payload["proposed"]["name"]: write_tool})
        calls.append("next_step")

    return run


def test_denied_write_never_runs_and_run_stops(tmp_path):
    payload = json.loads((EXAMPLES / "prewrite_uncovered.json").read_text())
    assert payload["status"] == "done" and payload["judge"] == "ACCEPT"
    ledger, calls = tmp_path / "ledger.json", []
    with pytest.raises(Denied):
        _agent(payload, ledger, calls)()
    assert calls == []
    assert not ledger.exists()


def test_allowed_write_runs_then_continues(tmp_path):
    payload = json.loads((EXAMPLES / "prewrite_cancel_ok.json").read_text())
    ledger, calls = tmp_path / "ledger.json", []
    _agent(payload, ledger, calls)()
    assert calls == ["cancel_reservation", "next_step"]
    assert json.loads(ledger.read_text()) == {"id": "R1"}
