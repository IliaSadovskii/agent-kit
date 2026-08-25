"""Running a CLI from what its folder declares.

This is the level-A executor: a provider whose `provider.toml` names a binary
and its flags needs no Python at all. Promoting it to level B means putting an
`adapter.py` beside the declaration that knows what cannot be declared — the
transcript, the context, the limit.

Killing a session kills everything it started. An agent CLI spawns tools, and a
tool that outlives the session it belongs to keeps editing files and keeps
spending; so the child gets its own process group and the group is what dies.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import UsageError
from ..logs import get_logger
from ..shell import kill_group
from .base import ExecutorFailed, ExecutorResult, SessionFacts, StepRequest

#: A step of real work is minutes, not hours; a session that has said nothing
#: for this long has stopped rather than paused.
DEFAULT_TIMEOUT = 1800

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

log = get_logger("providers.process")


@dataclass(frozen=True)
class Declaration:
    """`provider.toml`, read once. Nothing in here is a choice of this machine."""

    name: str
    title: str = ""
    level: str = "A"
    real: bool = True
    binary: str | None = None
    notes: str = ""
    flags: dict[str, list[str]] = field(default_factory=dict)
    answer: dict[str, str] = field(default_factory=dict)
    transcript_root: str | None = None
    limit_says: list[str] = field(default_factory=list)
    limit_until: str | None = None

    KNOWN = ("title", "level", "real", "binary", "notes", "flags", "answer", "transcript", "limits")

    @classmethod
    def read(cls, name: str, path: Path) -> "Declaration":
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as error:
            raise _bad(f"{path} cannot be read: {error}") from error

        block = document.get("provider")
        if not isinstance(block, dict):
            raise _bad(f"{path} has no [provider] table; silence must not read as a real level A agent")

        unknown = [key for key in block if key not in cls.KNOWN]
        if unknown:
            raise _bad(f"{path}: {', '.join(sorted(unknown))} is not something the kit reads")

        transcript = block.get("transcript") or {}
        limits = block.get("limits") or {}
        return cls(
            name=name,
            title=block.get("title", name),
            level=block.get("level", "A"),
            real=bool(block.get("real", True)),
            binary=block.get("binary"),
            notes=block.get("notes", ""),
            flags=block.get("flags", {}),
            answer=block.get("answer", {}),
            transcript_root=transcript.get("root"),
            limit_says=limits.get("says", []),
            limit_until=limits.get("until"),
        )

    @property
    def reads_limits(self) -> bool:
        return bool(self.limit_says and self.limit_until)


def _bad(detail: str) -> Exception:
    from ..errors import ProviderError

    return ProviderError("bad-declaration", detail)


class ProcessExecutor:
    """One composed input in on stdin, one answer out on stdout."""

    def __init__(
        self,
        declared: Declaration,
        binary: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.declared = declared
        self.name = declared.name
        self.binary = binary or declared.binary
        self.model = model
        self.effort = effort
        self.timeout = timeout
        if not self.binary:
            raise _bad(f"{declared.name} declares no binary and ships no adapter to run instead")

    # --- the command ------------------------------------------------------

    def command(self) -> list[str]:
        flags = self.declared.flags
        argv = [self.binary, *flags.get("headless", [])]
        argv += flags.get("full_access", [])
        argv += flags.get("instructions", [])
        if self.model and flags.get("model"):
            argv += [*flags["model"], self.model]
        if self.effort and flags.get("effort"):
            argv += [*flags["effort"], self.effort]
        return argv

    # --- running it -------------------------------------------------------

    def execute(self, request: StepRequest) -> ExecutorResult:
        workdir = request.where
        stdout, stderr = self.run(self.command(), request.input_text, workdir)
        return ExecutorResult(raw=self.text_of(stdout, stderr), meta={})

    def text_of(self, stdout: str, stderr: str) -> str:
        text = stdout.strip()
        if not text:
            raise ExecutorFailed("empty-answer", f"{self.binary} said nothing")
        return text

    def run(self, argv: list[str], input_text: str, workdir: Path | None, timeout: int | None = None) -> tuple[str, str]:
        timeout = self.timeout if timeout is None else timeout
        try:
            child = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workdir,
                text=True,
                encoding="utf-8",
                errors="replace",  # an odd byte is not worth losing an answer over
                start_new_session=True,  # its own process group, so its tools die with it
            )
        except FileNotFoundError as error:
            raise ExecutorFailed(
                "binary-missing", f"{self.binary} is not on PATH", retryable=False
            ) from error
        except (PermissionError, NotADirectoryError, OSError) as error:
            raise ExecutorFailed(
                "binary-missing", f"{self.binary} cannot be run: {error}", retryable=False
            ) from error

        try:
            stdout, stderr = child.communicate(input_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_group(child)
            raise ExecutorFailed(
                "session-timeout", f"the session said nothing for {timeout} seconds and was stopped"
            ) from None

        if child.returncode != 0:
            self._refuse_if_limited(f"{stdout}\n{stderr}")
            raise ExecutorFailed(
                "session-failed",
                f"{self.binary} exited with {child.returncode}: "
                f"{short(stderr) or short(stdout) or 'and said nothing'}",
            )
        return stdout, stderr

    # --- the limit --------------------------------------------------------

    def _refuse_if_limited(self, text: str, facts: SessionFacts | None = None) -> None:
        """Only ever called on a failure. A good answer that talks about limits is a good answer."""
        if not self.declared.reads_limits:
            return
        haystack = (text or "").lower()
        if not any(phrase in haystack for phrase in self.declared.limit_says):
            return
        found = re.search(self.declared.limit_until, text or "", re.IGNORECASE)
        until = found.group(1).strip() if found else None
        raise ExecutorFailed(
            "provider-limited",
            f"the account is limited; it resets at {until or 'an hour it did not say'}",
            retryable=False,  # asking an exhausted account again is guaranteed waste
            until=until,
            facts=facts,
        )


def json_answer(stdout: str, binary: str) -> dict[str, Any]:
    """The JSON the CLI promises, found in a stream that may hold other things too."""
    for candidate in (stdout.strip(), *(_JSON_OBJECT.findall(stdout) or [])):
        try:
            answer = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(answer, dict):
            return answer
    raise ExecutorFailed(
        "unreadable-answer",
        f"{binary} did not print the JSON it promises: {short(stdout) or 'nothing at all'}",
        retryable=False,
    )


def short(text: Any, limit: int = 400) -> str:
    text = (str(text) if text is not None else "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def whole_number(options: dict[str, list[str]], key: str, default: int) -> int:
    values = options.get(key)
    if not values:
        return default
    try:
        return int(values[-1])
    except ValueError:
        raise UsageError("bad-option", f"{key}={values[-1]!r} is not a whole number") from None


def build_from_declaration(declared: Declaration, options: dict[str, list[str]]) -> ProcessExecutor:
    def one(key: str) -> str | None:
        values = options.get(key)
        return values[-1] if values else None

    return ProcessExecutor(
        declared=declared,
        binary=one("binary"),
        model=one("model"),
        effort=one("effort"),
        timeout=whole_number(options, "timeout", DEFAULT_TIMEOUT),
    )
