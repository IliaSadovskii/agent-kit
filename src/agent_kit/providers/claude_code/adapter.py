"""Claude Code: what cannot be declared — the process, the answer, the limit.

Everything that *can* be declared is in `provider.toml` beside this file: the
binary, the flags, where each fact lives in the answer, where the transcript
lands, how a limited account announces itself. This module runs the thing and
turns its answer into the two shapes the driver knows: raw text, and the facts
that make the session observable.

The kit never talks to a model API. It runs the CLI, because the CLI brings the
tool loop, the editing, the permissions and — decisively — the subscription.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...logs import get_logger
from ..base import ExecutorFailed, ExecutorResult, SessionFacts, StepRequest

DECLARATION = Path(__file__).resolve().parent / "provider.toml"

#: A step of real work is minutes, not hours; a session that has said nothing
#: for this long has stopped rather than paused.
DEFAULT_TIMEOUT = 1800

log = get_logger("providers.claude_code")


@dataclass(frozen=True)
class Declaration:
    """`provider.toml`, read once. Nothing in here is a choice of this machine."""

    binary: str
    flags: dict[str, list[str]]
    answer: dict[str, str]
    transcript_root: str
    limit_says: list[str]
    limit_until: str

    @classmethod
    def read(cls, path: Path = DECLARATION) -> "Declaration":
        block = tomllib.loads(path.read_text(encoding="utf-8"))["provider"]
        return cls(
            binary=block["binary"],
            flags=block["flags"],
            answer=block["answer"],
            transcript_root=block["transcript"]["root"],
            limit_says=block["limits"]["says"],
            limit_until=block["limits"]["until"],
        )


class ClaudeCode:
    """One composed input in, one JSON answer out."""

    name = "claude_code"

    def __init__(
        self,
        binary: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        declaration: Declaration | None = None,
        new_session: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.declared = declaration or Declaration.read()
        self.binary = binary or self.declared.binary
        self.model = model
        self.effort = effort
        self.timeout = timeout
        self.new_session = new_session

    # --- level A ----------------------------------------------------------

    def command(self, session: str) -> list[str]:
        flags = self.declared.flags
        argv = [self.binary, *flags["headless"], *flags["full_access"], *flags["session"], session]
        if self.model:
            argv += [*flags["model"], self.model]
        if self.effort:
            argv += [*flags["effort"], self.effort]
        return argv

    def execute(self, request: StepRequest) -> ExecutorResult:
        session = self.new_session()
        workdir = request.project or request.workdir
        argv = self.command(session)
        log.info("claude_code: %s in %s (session %s)", request.step_name, workdir, session)

        answer = self._run(argv, request.input_text, workdir)
        facts = self._facts(answer, session, workdir)
        text = answer.get(self.declared.answer["text"])

        self._refuse_if_limited(answer, text)
        if answer.get(self.declared.answer["failed"]):
            raise ExecutorFailed(
                "session-error",
                f"the session reported a failure: {_short(text) or answer.get('subtype', 'no reason given')}",
            )
        if not isinstance(text, str) or not text.strip():
            raise ExecutorFailed("empty-answer", f"the answer carried no {self.declared.answer['text']!r}")

        return ExecutorResult(
            raw=text,
            meta={"session": session, "num_turns": answer.get("num_turns"), "duration_ms": answer.get("duration_ms")},
            facts=facts,
        )

    def version(self) -> str:
        """Does the CLI answer at all? The second rung of the ladder."""
        finished = self._spawn([self.binary, *self.declared.flags["version"]], input_text="", cwd=None, timeout=60)
        if finished.returncode != 0:
            raise ExecutorFailed("session-failed", _short(finished.stderr or finished.stdout) or "no answer")
        return finished.stdout.strip()

    # --- the process ------------------------------------------------------

    def _run(self, argv: list[str], input_text: str, workdir: Path) -> dict[str, Any]:
        finished = self._spawn(argv, input_text, workdir, self.timeout)
        if finished.returncode != 0:
            self._refuse_if_limited({}, f"{finished.stdout}\n{finished.stderr}")
            raise ExecutorFailed(
                "session-failed",
                f"{self.binary} exited with {finished.returncode}: "
                f"{_short(finished.stderr) or _short(finished.stdout) or 'and said nothing'}",
            )
        try:
            answer = json.loads(finished.stdout)
        except json.JSONDecodeError as error:
            raise ExecutorFailed(
                "unreadable-answer", f"{self.binary} did not print the JSON it promises: {error}"
            ) from error
        if not isinstance(answer, dict):
            raise ExecutorFailed("unreadable-answer", f"{self.binary} printed JSON that is not an answer")
        return answer

    def _spawn(self, argv: list[str], input_text: str, cwd: Path | None, timeout: int) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                argv,
                input=input_text,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as error:
            raise ExecutorFailed(
                "binary-missing", f"{self.binary} is not on PATH", hint=f"install it, or set its path"
            ) from error
        except PermissionError as error:
            raise ExecutorFailed("binary-missing", f"{self.binary} cannot be run: {error}") from error
        except subprocess.TimeoutExpired as error:
            raise ExecutorFailed(
                "session-timeout", f"the session said nothing for {timeout} seconds and was stopped"
            ) from error

    # --- level B ----------------------------------------------------------

    def _facts(self, answer: dict[str, Any], session: str, workdir: Path) -> SessionFacts:
        keys = self.declared.answer
        used = answer.get(keys["used"])
        window, model = self._window(answer.get(keys["window"]))
        return SessionFacts(
            session=answer.get(keys["session"]) or session,
            model=model,
            context_used=_context_used(used),
            context_window=window,
            cost_usd=answer.get(keys["cost"]),
            transcript=self.transcript_of(answer.get(keys["session"]) or session, workdir),
        )

    def transcript_of(self, session: str, workdir: Path) -> Path:
        """Where the session's own record lands, by the CLI's own convention."""
        folder = re.sub(r"[/.]", "-", str(Path(workdir).resolve()))
        return Path(self.declared.transcript_root).expanduser() / folder / f"{session}.jsonl"

    @staticmethod
    def _window(model_usage: Any) -> tuple[int | None, str | None]:
        if not isinstance(model_usage, dict) or not model_usage:
            return None, None
        name, block = next(iter(model_usage.items()))
        window = block.get("contextWindow") if isinstance(block, dict) else None
        return (window if isinstance(window, int) else None), name

    def _refuse_if_limited(self, answer: dict[str, Any], text: Any) -> None:
        haystack = f"{text or ''}\n{answer.get('api_error_status') or ''}".lower()
        if not any(phrase in haystack for phrase in self.declared.limit_says):
            return
        found = re.search(self.declared.limit_until, str(text or ""), re.IGNORECASE)
        until = found.group(1).strip() if found else "an hour it did not say"
        raise ExecutorFailed("provider-limited", f"the account is limited; it resets at {until}")


def _context_used(usage: Any) -> int | None:
    """Everything the model was carrying when it answered — cache included."""
    if not isinstance(usage, dict):
        return None
    counted = [
        usage.get(key)
        for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    ]
    numbers = [number for number in counted if isinstance(number, int)]
    return sum(numbers) if numbers else None


def _short(text: Any, limit: int = 400) -> str:
    text = (str(text) if text is not None else "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def build_executor(options: dict[str, list[str]]) -> ClaudeCode:
    """`binary=`, `model=`, `effort=`, `timeout=` — the machine's choices, not the tool's facts."""

    def one(key: str) -> str | None:
        values = options.get(key)
        return values[-1] if values else None

    timeout = one("timeout")
    return ClaudeCode(
        binary=one("binary"),
        model=one("model"),
        effort=one("effort"),
        timeout=int(timeout) if timeout else DEFAULT_TIMEOUT,
    )
