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

        body = _body(request, design, build, verify, review)
        # It goes beside the run's own state, which means it must be kept out
        # of the commit this step is about to make.
        runs_dir = project_paths(root).runs_dir
        keep_runs_out_of_git(runs_dir)
        body_file = runs_dir / request.slug / "pull-request.md"
        body_file.parent.mkdir(parents=True, exist_ok=True)
        body_file.write_text(body, encoding="utf-8")

        title = _title(design, request)
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
            meta={"model": self.name, "pull_request": url},
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


def _title(design: dict, request: StepRequest) -> str:
    first = (design.get("summary") or request.brief or request.slug).strip().split("\n")[0]
    sentence = first.split(". ")[0].rstrip(".")
    return sentence if len(sentence) <= 72 else sentence[:69].rstrip() + "…"


def _message(title: str, build: dict) -> str:
    """The history reads English, and it reads what was built, not what was planned."""
    return f"{title}\n\n{(build.get('summary') or '').strip()}\n"


def _body(request: StepRequest, design: dict, build: dict, verify: dict, review: dict) -> str:
    lines = [
        "## Что сделано", "",
        (build.get("summary") or "").strip(), "",
        "**Задача:** " + (request.brief or "не записана").strip(), "",
        "## Замысел", "",
        (design.get("summary") or "").strip(), "",
    ]

    lines += _list("Что меняется", design.get("changes"))
    lines += _list("Швы", design.get("seams"))
    lines += _list("Чем это доказано — решено до кода", design.get("verification"))
    lines += _list("Файлы", build.get("files"))
    lines += _list("Тесты", build.get("tests"))

    departures = build.get("deviations") or []
    if departures:
        lines += ["## Отступления от замысла", ""]
        lines += [f"- {item.get('what')} — {item.get('because')}" for item in departures]
        lines.append("")

    expensive = [item for item in (design.get("assumptions") or []) if item.get("expensive")]
    other = [item for item in (design.get("assumptions") or []) if not item.get("expensive")]
    if expensive or other:
        lines += ["## Допущения", ""]
        lines += [f"- **дорогое:** {item.get('what')} — {item.get('because')}" for item in expensive]
        lines += [f"- {item.get('what')} — {item.get('because')}" for item in other]
        lines.append("")

    lines += ["## Проверка", "", "Команды проекта, запущенные китом:", ""]
    for command in verify.get("commands") or []:
        mark = "ok" if command.get("passed") else f"код {command.get('exit_code')}"
        lines.append(f"- `{command.get('command')}` — {mark}")
    lines.append("")

    findings = review.get("findings") or []
    lines += ["## Что нашло ревью", ""]
    if findings:
        lines += [f"- *{finding.get('severity')}* — {_where(finding)}" for finding in findings]
    else:
        lines.append("Ничего.")
    lines += [
        "",
        "---",
        "",
        f"Собрано китом, прогон `{request.slug}`. Каждый пункт выше — запись шага, а не пересказ.",
        "",
    ]
    return "\n".join(lines)


def _list(heading: str, items: Any) -> list[str]:
    if not items:
        return []
    return [f"## {heading}", "", *[f"- {item}" for item in items], ""]
