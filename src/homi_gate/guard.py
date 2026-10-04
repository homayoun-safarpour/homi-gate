"""Run a tool only after its prewrite check passes.

Same shape as a pre-tool-use hook: the check runs before the tool, and a
deny means the tool is never called and the run stops with an exception.
status=done and judge=ACCEPT in the payload are ignored.
"""
from __future__ import annotations

from typing import Any, Callable

from homi_gate.cli import evaluate_prewrite


class Denied(RuntimeError):
    """Raised instead of calling a denied tool."""

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons) or "fail-closed")


def run_guarded(payload: dict[str, Any], tools: dict[str, Callable[..., Any]]) -> Any:
    """Check first. Call the proposed tool only if the check returns no reasons."""
    try:
        reasons = evaluate_prewrite(payload)
    except Exception as exc:  # fail closed on any checker error
        raise Denied([f"checker error: {exc}"]) from exc
    if reasons:
        raise Denied(reasons)
    proposed = payload["proposed"]
    name = proposed["name"]
    if name not in tools:
        raise Denied([f"no tool registered for {name!r}"])
    return tools[name](**proposed.get("args", {}))
