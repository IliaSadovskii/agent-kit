"""An executor with no CLI behind it: it answers from a script and remembers what it was asked."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from ...driver.executor import ExecutorFailed, ExecutorResult, StepRequest

Reply = str | Callable[[StepRequest], str]


class FakeExecutor:
    """Replies in order. A callable reply may raise `ExecutorFailed` to play a dead session."""

    def __init__(self, name: str = "fake", replies: Sequence[Reply] | None = None) -> None:
        self.name = name
        self.replies: list[Reply] = list(replies or [])
        self.requests: list[StepRequest] = []

    def execute(self, request: StepRequest) -> ExecutorResult:
        self.requests.append(request)
        if not self.replies:
            raise ExecutorFailed("no-reply", f"the fake provider {self.name!r} was asked once more than it was scripted")

        reply = self.replies.pop(0)
        raw = reply(request) if callable(reply) else reply
        return ExecutorResult(raw=raw, meta={"model": f"{self.name}-script", "cost": 0.0})

    @classmethod
    def from_files(cls, name: str, paths: Sequence[Path]) -> "FakeExecutor":
        return cls(name=name, replies=[path.read_text(encoding="utf-8") for path in paths])
