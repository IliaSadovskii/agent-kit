"""An executor with no CLI behind it: it answers from a script and remembers what it was asked.

A session does two things — it answers, and it edits the working copy. A fixture
that only answers can be handed to the driver but cannot plant a trap: the build
it plays says it wrote a file, and no file was written. So a reply file may carry
a script of the same name beside it, and that script runs in the project before
the answer is given. It is the one thing here that stands where a session would.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from ...errors import UsageError
from ..base import ExecutorFailed, ExecutorResult, StepRequest

#: A reply's script has the reply's name and this ending.
ACTS = ".sh"

#: A script that plants a trap is a few lines of shell. One that has said nothing
#: for this long is a case that will never finish.
ACTS_TIMEOUT = 60


@dataclass(frozen=True)
class Scripted:
    """One answer, and what the session that gave it did to the working copy."""

    text: str
    acts: Path | None = None


Reply = str | Scripted | Callable[[StepRequest], str]


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
        if isinstance(reply, Scripted):
            if reply.acts is not None:
                self._act(reply.acts, request)
            raw = reply.text
        else:
            raw = reply(request) if callable(reply) else reply
        return ExecutorResult(raw=raw, meta={"model": f"{self.name}-script", "cost": 0.0})

    def _act(self, script: Path, request: StepRequest) -> None:
        """What the session did before it answered, run where it would have run."""
        where = Path(request.project) if request.project else Path(request.workdir)
        try:
            done = subprocess.run(
                ["sh", str(script)], cwd=where, capture_output=True, text=True, timeout=ACTS_TIMEOUT
            )
        except OSError as error:
            raise ExecutorFailed("reply-script-failed", f"{script} could not be run: {error}") from error
        except subprocess.TimeoutExpired:
            raise ExecutorFailed(
                "reply-script-failed", f"{script} said nothing for {ACTS_TIMEOUT} seconds"
            ) from None
        if done.returncode != 0:
            raise ExecutorFailed(
                "reply-script-failed",
                f"{script} exited with {done.returncode}: {(done.stderr or done.stdout).strip()[:400]}",
            )

    @classmethod
    def from_files(cls, name: str, paths: Sequence[Path]) -> "FakeExecutor":
        return cls(
            name=name,
            replies=[
                Scripted(
                    text=path.read_text(encoding="utf-8"),
                    acts=path.with_suffix(ACTS) if path.with_suffix(ACTS).is_file() else None,
                )
                for path in paths
            ],
        )


def build_executor(options: dict[str, list[str]]) -> FakeExecutor:
    """`reply=<path>`, once per attempt: the file this provider answers with."""
    paths = [Path(value) for value in options.get("reply", [])]
    if not paths:
        raise UsageError(
            "no-reply",
            "the fake provider answers from files: pass --option reply=FILE at least once",
        )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise UsageError("no-reply", f"no such file: {', '.join(str(path) for path in missing)}")
    return FakeExecutor.from_files("fake", paths)
