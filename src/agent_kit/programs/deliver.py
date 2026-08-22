"""deliver — the branch, the commit, the pull request, all composed by the program.

Two reasons this is not a role. A pull request body assembled from what earlier
steps already recorded cannot describe work that did not happen; and a review
finding needs a consequence, or it is the second version's problem restated.
So `blocking` is read here, and it refuses.

The three final refusals it used to own — a blocking finding, a verify that did
not pass, a build that never finished — are asked of `deliverable.py` now,
because `record` has to ask the same question before it writes into the owner's
knowledge. They are still asked here: a run assembled from other steps may never
have had a `record` at all.

What the owner reads is in Russian, which is the project's rule for anything
addressed to them. The commit message is in English, which is the rule for
anything addressed to the history.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from ..logs import get_logger
from ..paths import project_paths
from ..shell import kill_group
from ..project import require_project
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest
from ..state.store import keep_runs_out_of_git
from .deliverable import BLOCKING, expensive_of, read, refuse_unless_deliverable
from .deliverable import where as _where

#: git and gh are local commands; one that has hung for this long has hung.
DEFAULT_TIMEOUT = 300

#: What git's own tooling wraps a subject at, near enough.
SUBJECT = 72

log = get_logger("programs.deliver")


class Deliver:
    name = "program:deliver"

    def __init__(self, root: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.root = Path(root)
        self.timeout = timeout

    def execute(self, request: StepRequest) -> ExecutorResult:
        root = Path(request.project) if request.project else self.root
        project = require_project(root)
        # A project that keeps knowledge cannot close a feature without the step
        # that writes it: the join is what S6 exists for, and a run that skipped
        # `record` has not made it.
        keeps = project.keeps_knowledge
        design, build, verify, review = read(request.prior, *(("record",) if keeps else ()))
        recorded = request.prior.get("record") or {"blocks": [], "closed": [], "files": []}

        refuse_unless_deliverable(build, verify, review)
        if keeps:
            _refuse_a_naked_assumption(design, recorded)

        body = compose_body(request, design, build, verify, review, recorded)
        # It goes beside the run's own state, which means it must be kept out
        # of the commit this step is about to make.
        runs_dir = project_paths(root).runs_dir
        keep_runs_out_of_git(runs_dir)
        body_file = runs_dir / request.slug / "pull-request.md"
        body_file.parent.mkdir(parents=True, exist_ok=True)
        body_file.write_text(body, encoding="utf-8")

        title = subject_line(design, request)
        branch = request.branch

        # Nothing above this line touched the repository, and nothing below it
        # is reached until the branch has been accounted for. A delivery that
        # overwrites somebody's work has already done the damage by the time it
        # notices, and `checkout -B` does exactly that.
        commit = self._settle_branch(
            root, branch, project.default_branch, title, _files(build, recorded), _message(title, build)
        )
        self._git(root, "push", "--set-upstream", "origin", branch)

        url = self._open_pull_request(root, project.default_branch, branch, title, body_file)

        return ExecutorResult(
            raw=json.dumps(
                {"branch": branch, "commit": commit, "pull_request": url}, indent=2, ensure_ascii=False
            ),
            # No `model`: a program is not a session, and the record must not
            # read as though one did this.
            meta={"pull_request": url},
        )

    # --- the branch, and whose it is --------------------------------------

    def _settle_branch(
        self, root: Path, branch: str, base: str, title: str, files: list[str], message: str
    ) -> str:
        """Make the branch hold this work, or refuse without having touched it.

        Four cases. It is not there, so it is ours to make. It holds exactly the
        commit this run would write, so an earlier attempt died after committing
        and this one carries it on — starting again would say there is nothing
        to deliver, and the work would sit on a branch with no pull request. It
        exists and holds no work at all, which is what happens when a session
        read `branch:` in its input as something to act on: committing onto it
        destroys nothing, and refusing it would strand a finished feature in a
        working copy. Or it holds somebody's commits, and that is where this stops.
        """
        ours = self._already_delivered(root, branch, title)
        if ours:
            self._git(root, "checkout", branch)
            return ours

        existing = _branch_exists(root, branch, self.timeout)
        if existing and not self._holds_work(root, branch, base):
            self._git(root, "checkout", branch)
            existing = False
        elif existing:
            raise ExecutorFailed(
                "branch-exists",
                f"{branch} already exists and holds commits that are not {base}'s; it is not ours to overwrite",
                retryable=False,
            )

        if not files:
            raise ExecutorFailed(
                "nothing-to-deliver", "the build named no file it changed", retryable=False
            )
        missing = [name for name in files if not (root / name).exists()]
        if missing:
            raise ExecutorFailed(
                "no-such-file",
                f"the build says it changed files that are not there: {', '.join(missing)}",
                retryable=False,
            )

        if not _on_branch(root, branch, self.timeout):
            self._git(root, "checkout", "-b", branch)
            made_it = True
        else:
            made_it = False
        try:
            # Only what the build named. `git add -A` sweeps up whatever else is
            # in the tree — a .env, a log, a half-written experiment — and pushes
            # it to a remote, and no project's .gitignore can be relied on for that.
            self._git(root, "add", "--", *files)
            if not _staged(root, self.timeout):
                raise ExecutorFailed(
                    "nothing-to-deliver",
                    f"none of the files the build named has changed: {', '.join(files)}",
                    retryable=False,
                )
            self._git(root, "commit", "-m", message)
        except BaseException:
            if made_it:
                # It was made a moment ago and holds nothing; leaving it behind
                # would make the next attempt look at somebody else's work.
                self._git(root, "checkout", "-")
                _run(["git", "branch", "-D", branch], root, self.timeout, "git-failed")
            raise
        return self._git(root, "rev-parse", "HEAD").strip()

    def _holds_work(self, root: Path, branch: str, base: str) -> bool:
        """Does this branch carry commits the base does not already have?

        A branch checked out and never committed to is not work, whoever made
        it. One with commits on top of the base is somebody's, and not ours.
        """
        printed = _run(
            ["git", "rev-list", "--count", f"{base}..{branch}"], root, self.timeout, "git-failed",
            allowed_to_fail=True,
        ).strip()
        return printed != "0"  # unreadable counts as work: refusing costs less than overwriting

    def _already_delivered(self, root: Path, branch: str, title: str) -> str | None:
        """The tip of an existing branch, when it is the commit this run would have written."""
        if not _branch_exists(root, branch, self.timeout):
            return None
        printed = _run(
            ["git", "log", "-1", "--format=%H%n%s", branch], root, self.timeout, "git-failed",
            allowed_to_fail=True,
        )
        lines = printed.strip().split("\n")
        if len(lines) < 2:
            return None
        return lines[0] if lines[1].strip() == title.strip() else None

    # --- the two commands it runs ----------------------------------------

    def _git(self, root: Path, *argv: str) -> str:
        return _run(["git", *argv], root, self.timeout, "git-failed")

    def _open_pull_request(self, root: Path, base: str, head: str, title: str, body_file: Path) -> str:
        standing = _run(
            ["gh", "pr", "view", head, "--json", "url", "--jq", ".url"], root, self.timeout, "gh-failed",
            allowed_to_fail=True,
        )
        for line in standing.splitlines():
            if line.strip().startswith("http"):
                # An earlier attempt opened it and died before it could say so.
                return line.strip()

        printed = _run(
            [
                "gh", "pr", "create",
                "--base", base,
                "--head", head,
                "--title", title,
                "--body-file", str(body_file),
            ],
            root,
            self.timeout,
            "gh-failed",
        )
        url = next((line.strip() for line in reversed(printed.splitlines()) if line.strip().startswith("http")), "")
        if not url:
            raise ExecutorFailed(
                "gh-failed", f"gh opened no pull request it would name: {printed.strip() or 'it said nothing'}"
            )
        return url


def _run(argv: Sequence[str], cwd: Path, timeout: int, code: str, allowed_to_fail: bool = False) -> str:
    """One command, and everything it started dies with it.

    `git` and `gh` spawn helpers — a credential helper, a pager, an ssh — and a
    helper that outlives the command it belongs to holds a lock or a terminal
    nobody is watching. So the child gets its own process group and the group is
    what dies.
    """
    try:
        child = subprocess.Popen(
            list(argv), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            start_new_session=True,
        )
    except FileNotFoundError as missing:
        raise ExecutorFailed(
            "binary-missing", f"{argv[0]} is not on PATH, and delivery needs it", retryable=False
        ) from missing
    except OSError as error:
        raise ExecutorFailed(
            "binary-missing", f"{argv[0]} cannot be run: {error}", retryable=False
        ) from error

    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(child)
        raise ExecutorFailed(code, f"{' '.join(argv)} said nothing for {timeout} seconds") from None

    if child.returncode != 0:
        if allowed_to_fail:
            return ""
        raise ExecutorFailed(
            code,
            f"{' '.join(argv)} exited with {child.returncode}: "
            f"{(stderr or stdout).strip()[:600] or 'and said nothing'}",
        )
    return stdout


def _branch_exists(root: Path, branch: str, timeout: int) -> bool:
    """Asked of git, and through the same door as everything else: a git that
    hangs here must die with its group rather than take the timeout uncaught."""
    printed = _run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        root, timeout, "git-failed", allowed_to_fail=True,
    )
    return bool(printed.strip())


def _on_branch(root: Path, branch: str, timeout: int) -> bool:
    printed = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, timeout, "git-failed")
    return printed.strip() == branch


def _staged(root: Path, timeout: int) -> bool:
    return bool(_run(["git", "diff", "--cached", "--name-only"], root, timeout, "git-failed").strip())


# --- what it reads, and what makes it refuse --------------------------------


def _files(build: dict, recorded: dict) -> list[str]:
    """What goes into the commit: what the build named, and what the program wrote.

    A block written into the owner's knowledge and left out of the commit is one
    nobody but this machine will ever see. It is still only what was named — the
    program named half of it.
    """
    named = [str(name) for name in (build.get("files") or []) if str(name).strip()]
    for name in (recorded.get("files") or []):
        if str(name).strip() and str(name) not in named:
            named.append(str(name))
    return named


def _refuse_a_naked_assumption(design: dict, recorded: dict) -> None:
    """The join, asked a second time by the step that closes the feature.

    It cannot fire while the design step's contract stands, and that is the
    point: it is what survives a run assembled from different steps, or a
    contract somebody loosens later without noticing what it held.
    """
    # Counted, not gathered into a set: two assumptions worded the same owe two
    # blocks, and a set says one block answers for both.
    written = Counter(str(block.get("what")) for block in (recorded.get("blocks") or []))
    naked = []
    for item in expensive_of(design):
        what = str(item.get("what"))
        if written[what] > 0:
            written[what] -= 1
        else:
            naked.append(item)
    if naked:
        raise ExecutorFailed(
            "assumption-with-no-block",
            "this project keeps knowledge, and a feature is not closed while an expensive assumption "
            "has no block: " + "; ".join(str(item.get("what")) for item in naked),
            retryable=False,
        )


# --- what the owner reads ----------------------------------------------------


def subject_line(design: dict, request: StepRequest) -> str:
    """What the history and the pull request are called.

    The design writes it, because the first 72 characters of an essay are not a
    subject line. When it comes back too long anyway it is cut at a word, never
    mid-word: a subject ending in half a word reads as a broken tool.
    """
    written = (design.get("title") or design.get("summary") or request.brief or request.slug).strip()
    first = written.split("\n")[0].rstrip(".")
    if len(first) <= SUBJECT:
        return first
    cut = first[:SUBJECT].rsplit(" ", 1)[0].rstrip(" ,;:—-")
    return (cut or first[:SUBJECT]) + "…"


def _message(subject: str, build: dict) -> str:
    """The history reads English, and it reads what was built, not what was planned."""
    return f"{subject}\n\n{(build.get('summary') or '').strip()}\n"


def compose_body(request: StepRequest, design: dict, build: dict, verify: dict, review: dict,
                 recorded: dict | None = None) -> str:
    """The pull request, written as a report to the owner rather than a dump.

    Three things are open, because they are the three the owner has to act on:
    what was done, what is wanted of them, and anything blocking. Everything
    else is the record — true, worth keeping, and folded away, because a body
    that opens with all of it is one nobody reads to the end.
    """
    findings = review.get("findings") or []
    blocking = [item for item in findings if item.get("severity") == BLOCKING]
    expensive = expensive_of(design)
    recorded = recorded or {}

    open_part = [
        "## Что сделано", "",
        (build.get("summary") or "").strip(), "",
        "**Задача:** " + (request.brief or "не записана").strip(), "",
    ]

    if blocking:
        open_part += ["## Что мешает выпуску", ""]
        open_part += [f"- {_where(item)}" for item in blocking]
        open_part.append("")

    asked = [item for item in (design.get("needs_owner") or []) if str(item).strip()]
    open_part += ["## Что нужно от владельца", ""]
    if asked:
        open_part += ["Вопросы, на которые может ответить только владелец:", ""]
        open_part += [f"- {item}" for item in asked]
        open_part.append("")
    if expensive:
        open_part.append("Дорогие допущения — если хоть одно неверно, работа сделана не та:")
        open_part.append("")
        open_part += [f"- **{item.get('what')}** — {item.get('because')}" for item in expensive]
        open_part.append("")
    if not asked and not expensive:
        open_part += ["Ничего: вопросов нет, дорогих допущений нет, ревью ничего не заблокировало.", ""]

    green = [f"`{item.get('command')}`" for item in (verify.get("commands") or []) if item.get("passed")]
    red = [
        f"`{item.get('command')}` — код {item.get('exit_code')}"
        for item in (verify.get("commands") or [])
        if not item.get("passed")
    ]
    open_part += [
        "## Проверка", "",
        "Зелено: " + ", ".join(green) if green else "Ничего не запускалось",
        "",
    ]
    if red:
        open_part += ["Не зелено: " + ", ".join(red), ""]

    folded = ["## Замысел", "", (design.get("summary") or "").strip(), ""]
    folded += _list("Что меняется", design.get("changes"))
    folded += _list("Швы", design.get("seams"))
    folded += _list("Чем это доказано — решено до кода", design.get("verification"))
    folded += _list("Файлы", build.get("files"))
    folded += _list("Тесты", build.get("tests"))

    departures = build.get("deviations") or []
    if departures:
        folded += ["## Отступления от замысла", ""]
        folded += [f"- {item.get('what')} — {item.get('because')}" for item in departures]
        folded.append("")

    ordinary = [item for item in (design.get("assumptions") or []) if not item.get("expensive")]
    if ordinary:
        folded += ["## Остальные допущения", ""]
        folded += [f"- {item.get('what')} — {item.get('because')}" for item in ordinary]
        folded.append("")

    written = recorded.get("blocks") or []
    closed = recorded.get("closed") or []
    if written or closed:
        folded += ["## Что записано в знание", ""]
        folded += [f"- `{item.get('id')}` → `{item.get('at')}` — {item.get('what')}" for item in written]
        folded += [f"- закрыт `{item}`" for item in closed]
        folded.append("")

    rest = [item for item in findings if item.get("severity") != BLOCKING]
    folded += ["## Что ещё нашло ревью", ""]
    folded += [f"- *{item.get('severity')}* — {_where(item)}" for item in rest] if rest else ["Ничего."]
    folded.append("")

    return "\n".join(
        open_part
        + ["<details>", "<summary>Запись прогона: замысел, швы, тесты, допущения</summary>", ""]
        + folded
        + ["</details>", "",
           "---", "",
           f"Собрано китом, прогон `{request.slug}`. Каждый пункт выше — запись шага, а не пересказ.", ""]
    )


def _list(heading: str, items: Any) -> list[str]:
    if not items:
        return []
    return [f"### {heading}", "", *[f"- {item}" for item in items], ""]
