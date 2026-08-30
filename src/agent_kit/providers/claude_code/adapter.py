"""Claude Code: what cannot be declared — the transcript, the context, the limit.

Everything that *can* be declared is in `provider.toml` beside this file, and
`providers/process.py` runs it. What is left here is level B: reading the
session's own record for what it was actually carrying, picking out the model
that did the work, and turning an exhausted account into a refusal with an hour
attached.

The kit never talks to a model API. It runs the CLI, because the CLI brings the
tool loop, the editing, the permissions and — decisively — the subscription.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Callable

from ...logs import get_logger
from ..base import ExecutorFailed, ExecutorResult, SessionFacts, StepRequest
from ..process import (
    DEFAULT_TIMEOUT,
    Declaration,
    ProcessExecutor,
    json_answer,
    short,
    whole_number,
)

DECLARATION = Path(__file__).resolve().parent / "provider.toml"

log = get_logger("providers.claude_code")


class ClaudeCode(ProcessExecutor):
    """One composed input on stdin, one JSON answer on stdout, one session named by us."""

    def __init__(
        self,
        binary: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        declared: Declaration | None = None,
        new_session: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        super().__init__(
            declared=declared or Declaration.read("claude_code", DECLARATION),
            binary=binary,
            model=model,
            effort=effort,
            timeout=timeout,
        )
        self.new_session = new_session

    # --- level A ----------------------------------------------------------

    def command(self, session: str | None = None) -> list[str]:
        argv = super().command()
        if session and self.declared.flags.get("session"):
            argv += [*self.declared.flags["session"], session]
        return argv

    def execute(self, request: StepRequest) -> ExecutorResult:
        asked_for = self.new_session()
        workdir = request.where
        log.info("claude_code: %s in %s (session %s)", request.step_name, workdir, asked_for)

        stdout, _ = self.run(self.command(asked_for), request.input_text, workdir)
        answer = json_answer(stdout, self.binary)
        facts = self._facts(answer, asked_for, workdir)

        keys = self.declared.answer
        text = answer.get(keys["text"])
        if answer.get(keys["failed"]):
            # The one place a limit is read on purpose: the failure path.
            self._refuse_if_limited(f"{text}\n{answer.get('api_error_status') or ''}", facts)
            raise ExecutorFailed(
                "session-error",
                f"the session reported a failure: {short(text) or answer.get('subtype', 'no reason given')}",
                facts=facts,
            )
        if not isinstance(text, str) or not text.strip():
            raise ExecutorFailed(
                "empty-answer", f"the answer carried no {keys['text']!r}", facts=facts
            )

        return ExecutorResult(
            raw=text,
            meta={
                "session": asked_for,
                "num_turns": answer.get("num_turns"),
                "duration_ms": answer.get("duration_ms"),
            },
            facts=facts,
        )

    # --- level B ----------------------------------------------------------

    def _facts(self, answer: dict[str, Any], asked_for: str, workdir: Path) -> SessionFacts:
        keys = self.declared.answer
        # The name the session reports is the real one; the one we asked for was a wish.
        session = answer.get(keys["session"]) or asked_for
        window, model = _the_model_that_did_the_work(answer.get(keys["window"]))
        transcript = self.transcript_of(session, workdir)
        return SessionFacts(
            session=session,
            model=model,
            context_used=context_in(transcript),
            context_window=window,
            tokens_billed=_tokens_billed(answer.get(keys["used"])),
            cost_usd=answer.get(keys["cost"]),
            transcript=transcript,
        )

    def transcript_of(self, session: str, workdir: Path) -> Path:
        """Where the session's own record lands, by the CLI's own convention."""
        folder = re.sub(r"[/.]", "-", str(Path(workdir).resolve()))
        root = self.declared.transcript_root or "~/.claude/projects"
        return Path(root).expanduser() / folder / f"{session}.jsonl"


def context_in(transcript: Path) -> int | None:
    """What the session was carrying when it last answered.

    Not the counters in the result: those are totals over every turn, and the
    cached prefix is re-counted in each one, so they outgrow the window they
    would be compared against. The last assistant turn is the occupancy.
    """
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = entry.get("message", {}).get("usage") if isinstance(entry, dict) else None
        counted = _tokens_billed(usage)
        if entry.get("type") == "assistant" and counted:
            return counted
    return None


def _the_model_that_did_the_work(model_usage: Any) -> tuple[int | None, str | None]:
    """A subagent or a title generator puts a second, smaller model in the answer."""
    if not isinstance(model_usage, dict) or not model_usage:
        return None, None
    blocks = {name: block for name, block in model_usage.items() if isinstance(block, dict)}
    if not blocks:
        return None, None
    name = max(blocks, key=lambda key: (blocks[key].get("contextWindow") or 0, blocks[key].get("outputTokens") or 0))
    window = blocks[name].get("contextWindow")
    return (window if isinstance(window, int) else None), name


def _tokens_billed(usage: Any) -> int | None:
    """Everything the account paid for in one turn — cache re-reads included."""
    if not isinstance(usage, dict):
        return None
    counted = [
        usage.get(key)
        for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    ]
    numbers = [number for number in counted if isinstance(number, int)]
    return sum(numbers) if numbers else None


def build_executor(options: dict[str, list[str]]) -> ClaudeCode:
    """`binary=`, `model=`, `effort=`, `timeout=` — the machine's choices, not the tool's facts."""

    def one(key: str) -> str | None:
        values = options.get(key)
        return values[-1] if values else None

    return ClaudeCode(
        binary=one("binary"),
        model=one("model"),
        effort=one("effort"),
        timeout=whole_number(options, "timeout", DEFAULT_TIMEOUT),
    )
