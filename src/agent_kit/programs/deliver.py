"""deliver — the branch, the commit, the pull request, all composed by the program.

Two reasons this is not a role. A pull request body assembled from what earlier
steps already recorded cannot describe work that did not happen; and a review
finding needs a consequence, or it is the second version's problem restated.
So `blocking` is read here, and it refuses.

Three refusals, and all three are final: a blocking finding, a verify that did
not pass, a build that never finished. None of them will have changed by the
next attempt, so none of them is worth a second session.

What the owner reads is in Russian, which is the project's rule for anything
addressed to them. The commit message is in English, which is the rule for
anything addressed to the history.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from ..logs import get_logger
from ..paths import project_paths
from ..project import require_project
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest
from ..state.store import keep_runs_out_of_git

#: git and gh are local commands; one that has hung for this long has hung.
DEFAULT_TIMEOUT = 300

BLOCKING = "blocking"

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
        design, build, verify, review = _read(request.prior)

        _refuse_unless_deliverable(build, verify, review)

        if not _changed(root, self.timeout):
            raise ExecutorFailed(
                "nothing-to-deliver",
                "the working tree holds no change, so there is nothing to put on a branch",
                retryable=False,
            )

        body = compose_body(request, design, build, verify, review)
        # It goes beside the run's own state, which means it must be kept out
        # of the commit this step is about to make.
        runs_dir = project_paths(root).runs_dir
        keep_runs_out_of_git(runs_dir)
        body_file = runs_dir / request.slug / "pull-request.md"
        body_file.parent.mkdir(parents=True, exist_ok=True)
        body_file.write_text(body, encoding="utf-8")

        title = subject_line(design, request)
        branch = request.branch

        self._git(root, "checkout", "-B", branch)
        self._git(root, "add", "-A")
        self._git(root, "commit", "-m", _message(title, build))
        commit = self._git(root, "rev-parse", "HEAD").strip()
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

    # --- the two commands it runs ----------------------------------------

    def _git(self, root: Path, *argv: str) -> str:
        return _run(["git", *argv], root, self.timeout, "git-failed")

    def _open_pull_request(self, root: Path, base: str, head: str, title: str, body_file: Path) -> str:
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


def _run(argv: Sequence[str], cwd: Path, timeout: int, code: str) -> str:
    try:
        finished = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except FileNotFoundError as missing:
        raise ExecutorFailed(
            "binary-missing", f"{argv[0]} is not on PATH, and delivery needs it", retryable=False
        ) from missing
    except subprocess.TimeoutExpired as expired:
        raise ExecutorFailed(code, f"{' '.join(argv)} said nothing for {timeout} seconds") from expired

    if finished.returncode != 0:
        raise ExecutorFailed(
            code,
            f"{' '.join(argv)} exited with {finished.returncode}: "
            f"{(finished.stderr or finished.stdout).strip()[:600] or 'and said nothing'}",
        )
    return finished.stdout


def _changed(root: Path, timeout: int) -> bool:
    return bool(_run(["git", "status", "--porcelain"], root, timeout, "git-failed").strip())


# --- what it reads, and what makes it refuse --------------------------------


def _read(prior: dict[str, dict[str, Any]]) -> tuple[dict, dict, dict, dict]:
    missing = [name for name in ("design", "build", "verify", "review") if not prior.get(name)]
    if missing:
        raise ExecutorFailed(
            "nothing-to-read",
            f"delivery composes itself from what earlier steps returned, and {', '.join(missing)} returned nothing",
            retryable=False,
        )
    return prior["design"], prior["build"], prior["verify"], prior["review"]


def _refuse_unless_deliverable(build: dict, verify: dict, review: dict) -> None:
    if not build.get("complete"):
        left = ", ".join(build.get("remaining") or []) or "it did not say what is left"
        raise ExecutorFailed(
            "build-unfinished", f"the build did not finish: {left}", retryable=False
        )

    if not verify.get("passed"):
        failed = [
            f"{command.get('name')} exited with {command.get('exit_code')}"
            for command in verify.get("commands") or []
            if not command.get("passed")
        ]
        raise ExecutorFailed(
            "not-verified",
            f"the project's own commands did not come back green: {', '.join(failed) or 'no command ran'}",
            retryable=False,
        )

    blocking = [finding for finding in review.get("findings") or [] if finding.get("severity") == BLOCKING]
    if blocking:
        raise ExecutorFailed(
            "blocked-by-review",
            "the review found something that blocks delivery: "
            + "; ".join(_where(finding) for finding in blocking),
            retryable=False,
        )


def _where(finding: dict) -> str:
    place = finding.get("where")
    return f"{finding.get('what')} ({place})" if place else str(finding.get("what"))


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


def compose_body(request: StepRequest, design: dict, build: dict, verify: dict, review: dict) -> str:
    """The pull request, written as a report to the owner rather than a dump.

    Three things are open, because they are the three the owner has to act on:
    what was done, what is wanted of them, and anything blocking. Everything
    else is the record — true, worth keeping, and folded away, because a body
    that opens with all of it is one nobody reads to the end.
    """
    findings = review.get("findings") or []
    blocking = [item for item in findings if item.get("severity") == BLOCKING]
    expensive = [item for item in (design.get("assumptions") or []) if item.get("expensive")]

    open_part = [
        "## Что сделано", "",
        (build.get("summary") or "").strip(), "",
        "**Задача:** " + (request.brief or "не записана").strip(), "",
    ]

    if blocking:
        open_part += ["## Что мешает выпуску", ""]
        open_part += [f"- {_where(item)}" for item in blocking]
        open_part.append("")

    open_part += ["## Что нужно от владельца", ""]
    if expensive:
        open_part.append("Дорогие допущения — если хоть одно неверно, работа сделана не та:")
        open_part.append("")
        open_part += [f"- **{item.get('what')}** — {item.get('because')}" for item in expensive]
    else:
        open_part.append("Ничего: дорогих допущений нет, ревью ничего не заблокировало.")
    open_part.append("")

    green = [f"`{item.get('command')}`" for item in (verify.get("commands") or []) if item.get("passed")]
    red = [
        f"`{item.get('command')}` — код {item.get('exit_code')}"
        for item in (verify.get("commands") or [])
        if not item.get("passed")
    ]
    open_part += [
        "## Проверка", "",
        ("Зелено: " + ", ".join(green) if green else "Ничего не запускалось") + ("" if not red else ""),
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
