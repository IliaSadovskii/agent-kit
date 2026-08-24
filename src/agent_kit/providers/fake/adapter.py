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
from ...shell import kill_group
from ..base import ExecutorFailed, ExecutorResult, StepRequest

#: A reply's script has the reply's name and this ending.
ACTS = ".sh"

#: A reply file that begins with this is a refusal rather than an answer: the
#: session was limited, timed out, crashed. The bench needs it to plant a trap
#: about any of those, and one line is cheaper than a fixture per failure.
REFUSE = "!refuse"

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
            _refuse_if_asked(raw)
        else:
            raw = reply(request) if callable(reply) else reply
        return ExecutorResult(raw=raw, meta={"model": f"{self.name}-script", "cost": 0.0})

    def _act(self, script: Path, request: StepRequest) -> None:
        """What the session did before it answered, run where it would have run."""
        where = Path(request.project) if request.project else Path(request.workdir)
        # Its own process group, like every other place in the kit that starts
        # somebody else's process: a script that backgrounds something and then
        # hangs must not leave it behind.
        try:
            child = subprocess.Popen(
                ["sh", str(script)], cwd=where, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, start_new_session=True,
            )
        except OSError as error:
            raise ExecutorFailed("reply-script-failed", f"{script} could not be run: {error}") from error

        try:
            stdout, stderr = child.communicate(timeout=ACTS_TIMEOUT)
        except subprocess.TimeoutExpired:
            kill_group(child)
            raise ExecutorFailed(
                "reply-script-failed", f"{script} said nothing for {ACTS_TIMEOUT} seconds"
            ) from None
        if child.returncode != 0:
            raise ExecutorFailed(
                "reply-script-failed",
                f"{script} exited with {child.returncode}: {(stderr or stdout).strip()[:400]}",
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


def _refusal(text: str) -> ExecutorFailed | None:
    """`!refuse <code> [key=value…]` on the first line, and nowhere else.

    First line only: an answer that merely talks about a refusal is an answer,
    and a fixture that reads a word out of the middle of one is a fixture that
    fails whenever the prose changes.
    """
    first = (text or "").splitlines()[0].strip() if (text or "").strip() else ""
    if not first.startswith(REFUSE):
        return None
    words = first[len(REFUSE):].split()
    if not words:
        raise UsageError("bad-reply", f"{REFUSE} needs a code: the kit refuses by name, never by sentence")
    said = dict(
        word.split("=", 1) for word in words[1:] if "=" in word
    )
    code = words[0]
    # An exhausted account asked again is guaranteed waste, which is what the
    # real adapters already know. A fixture that answered otherwise would let a
    # trap pass that the live path would fail.
    retryable = said.get("retryable", "false" if code == "provider-limited" else "true") != "false"
    return ExecutorFailed(
        code,
        said.get("detail", "the fake provider was told to refuse"),
        retryable=retryable,
        expected=said.get("expected") == "true",
        until=said.get("until"),
    )


def _refuse_if_asked(text: str) -> None:
    refusal = _refusal(text)
    if refusal is not None:
        raise refusal


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
