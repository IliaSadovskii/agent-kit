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

from ..errors import ConfigError, UsageError
from ..logs import get_logger
from ..shell import kill_group
from .base import ExecutorFailed, ExecutorResult, SessionFacts, StepRequest

#: A step of real work is minutes, not hours; a session that has said nothing
#: for this long has stopped rather than paused.
DEFAULT_TIMEOUT = 1800

#: How long a CLI is given to say what it is. Printing a version is the
#: cheapest thing a program does, and this rung is climbed for every shipped
#: provider every time the machine's standing is read — so the session's half
#: hour here would make one hung CLI a hung `doctor`.
VERSION_TIMEOUT = 15

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
    #: What a person runs to put this tool on the machine, and what they run to
    #: log it in. Argv, never prose: the kit runs neither — installing is the
    #: owner's act on the owner's machine — but argv can be taken by its first
    #: word and asked of PATH, and what installing did is measured afterwards by
    #: the `binary` rung. A sentence could be held to neither.
    install: list[str] = field(default_factory=list)
    #: Printed only. Whether the account behind it answers is the `login` rung,
    #: and that costs a session, so it is `provider check` that measures it.
    login: list[str] = field(default_factory=list)
    #: One short line about *this tool's* login, printed by the walk under the
    #: command. What happens when a person runs it differs by tool and by
    #: nothing else: Gemini opens a screen that does not close itself, Codex
    #: prints a code to type on another machine because a server has no browser.
    #: A walk that wrote one sentence for all of them would be wrong about two.
    #:
    #: Prose, and Russian, because a person reads it — the same rule the rest of
    #: the kit's screens follow. Argv, keys and titles beside it stay as they are.
    login_note: str = ""

    KNOWN = (
        "title", "level", "real", "binary", "notes", "flags", "answer",
        "transcript", "limits", "setup",
    )
    SETUP = ("install", "login", "login_note")
    #: Every flag the kit will ever look for, and the reader of each is named
    #: where it is used: `headless`, `full_access`, `instructions`, `model` and
    #: `effort` in `ProcessExecutor.command`, `version` in `ProcessExecutor.version`,
    #: `session` in the Claude Code adapter.
    #:
    #: Checked rather than passed through, because this is the one table where a
    #: typo is invisible. A provider may leave `headless` out on purpose — Gemini
    #: CLI goes non-interactive by itself when stdin is not a terminal — and a
    #: provider that spells it `hedless` builds exactly the same argv. Nothing
    #: downstream can tell those two apart, so the declaration is where they are.
    FLAGS = (
        "headless", "full_access", "instructions", "model", "effort", "session", "version",
    )
    #: Where each fact lives in the JSON a level-B adapter reads. Level A reads
    #: none of them; the shipped reader is `claude_code/adapter.py`.
    ANSWER = ("text", "session", "cost", "failed", "window", "used")

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
        setup = _table(block.get("setup"), path, "setup", cls.SETUP)
        flags = _table(block.get("flags"), path, "flags", cls.FLAGS)
        answer = _table(block.get("answer"), path, "answer", cls.ANSWER)
        return cls(
            name=name,
            title=block.get("title", name),
            level=block.get("level", "A"),
            real=bool(block.get("real", True)),
            binary=block.get("binary"),
            notes=block.get("notes", ""),
            flags=flags,
            answer=answer,
            transcript_root=transcript.get("root"),
            limit_says=limits.get("says", []),
            limit_until=limits.get("until"),
            install=_argv(setup.get("install"), path, "setup.install"),
            login=_argv(setup.get("login"), path, "setup.login"),
            login_note=_prose(setup.get("login_note"), path, "setup.login_note"),
        )

    @property
    def reads_limits(self) -> bool:
        return bool(self.limit_says and self.limit_until)


def _table(value: Any, path: Path, where: str, known: tuple[str, ...]) -> dict:
    """One of the declaration's sub-tables, with every key held to what is read.

    The same shape `setup` has had since S9a, applied to the two tables that
    were still going through untouched. A key nobody reads is not a harmless
    extra: it is argv the kit will never pass and a fact it will never look up,
    and neither leaves any trace at the hour it matters.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _bad(f"{path}: [provider.{where}] must be a table")
    unknown = [key for key in value if key not in known]
    if unknown:
        raise _bad(
            f"{path}: {where}.{f', {where}.'.join(sorted(unknown))} is not something the kit reads"
        )
    return dict(value)


def _argv(value: Any, path: Path, where: str) -> list[str]:
    """A command, in the one form a program can do anything with.

    A string would be prose: the kit would have to split it to find the first
    word, and splitting somebody else's command line is guessing. A list of
    words is not guessed at.
    """
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        raise _bad(f"{path}: {where} must be a non-empty list of words, not a sentence")
    if any(not isinstance(word, str) or not word.strip() for word in value):
        raise _bad(f"{path}: {where} holds something that is not a word of a command")
    return list(value)


def _prose(value: Any, path: Path, where: str) -> str:
    """A sentence, where the thing beside it is a command.

    Held to being a string for the same reason `_argv` holds a command to being
    a list: a declaration that got the shape wrong must say so here, where a
    person is reading the file, rather than at the hour somebody is mid-install.
    """
    if value is None:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise _bad(f"{path}: {where} must be a sentence somebody can read")
    return value.strip()


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
        self._refuse_a_choice_it_cannot_pass_on("model", model)
        self._refuse_a_choice_it_cannot_pass_on("effort", effort)

    def _refuse_a_choice_it_cannot_pass_on(self, what: str, chosen: str | None) -> None:
        """A choice this machine made that this tool has no flag for.

        Refused rather than dropped, and refused here — before a session, before
        a slot, before a token. `command()` used to read `if self.model and
        flags.get("model")`, so a machine that named a model for a tool with no
        such flag ran the night on whatever that tool defaults to and said
        nothing about it anywhere.

        The code is the *machine's*, not the provider's: `provider.toml` states
        what is true about a tool and is not wrong here, `config.toml` asked for
        something this tool does not offer, and the file to edit is the second
        one. Which is why it is a `ConfigError` and leaves exit code 2.
        """
        if chosen and not self.declared.flags.get(what):
            raise ConfigError(
                f"{what}-not-selectable",
                f"this machine chose {what} {chosen!r} for {self.declared.name}, "
                f"which declares no flag that passes one on",
                hint=f"drop the {what} from [providers.{self.declared.name}] in the machine's "
                     f"configuration, or add a {what} flag to that provider's declaration",
            )

    # --- the command ------------------------------------------------------

    def command(self) -> list[str]:
        flags = self.declared.flags
        argv = [self.binary, *flags.get("headless", [])]
        argv += flags.get("full_access", [])
        argv += flags.get("instructions", [])
        # No `and flags.get(...)` here any more: a choice this tool cannot be
        # told is refused when the executor is built, so reaching this line with
        # one and no flag for it is impossible rather than quietly survivable.
        if self.model:
            argv += [*flags["model"], self.model]
        if self.effort:
            argv += [*flags["effort"], self.effort]
        return argv

    def version(self) -> str:
        """Does the CLI answer at all? The second rung, and it costs no session.

        Here rather than in an adapter: which flag asks a CLI what it is is a
        fact about the tool, and it is already declared. Left in `claude_code`'s
        adapter it was true that *the two free rungs are climbed for everyone*
        only for the one provider that ships an adapter.
        """
        flags = self.declared.flags.get("version")
        if not flags:
            raise ExecutorFailed(
                "no-version-flag",
                f"{self.name} declares no flag that asks it what it is",
                retryable=False,
            )
        stdout, _ = self.run([self.binary, *flags], "", None, timeout=VERSION_TIMEOUT)
        return stdout.strip()

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
