"""What a case is: what it plants, and what must fire.

A case is a directory. Everything in it is optional except the declaration:

    case.toml     what this plants and what must fire
    repo/         files laid over the baseline project before its first commit
    plant.sh      run in the repository afterwards, to put the trap in place
    replies/      what the fake provider answers, one file per attempt, in name
                  order; a `.sh` of the same name is what that session did
    judge.sh      read the run and say whether the mechanism fired

Nothing here names a provider. Every case runs on `providers/fake/`, which
answers from files, so the whole set costs nothing and runs on every change.
Cases that drive a real provider wait for a second adapter to compare against —
see the note for S5.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import StateError

CASE_FILE = "case.toml"

#: The run every case makes, unless it says otherwise.
DEFAULT_SLUG = "add-vat"
DEFAULT_BRIEF = "Money should be able to quote a price with VAT on it"

_TOP_KEYS = {"case", "expect"}
_CASE_KEYS = {"title", "fires", "slug", "brief"}
_EXPECT_KEYS = {"exit_code", "status", "refusal", "steps"}

_STATUSES = ("created", "running", "done", "failed", "stopped")
_STEP_STATUSES = ("pending", "running", "passed", "failed")


class CaseError(StateError):
    """The case itself is wrong. Nothing was judged, and nothing can be."""


@dataclass(frozen=True)
class Expect:
    """What must be true of the run afterwards, if the mechanism fired."""

    exit_code: int
    status: str
    #: A substring of the reason the run recorded. Usually the refusal's code.
    refusal: str = ""
    #: Step name -> the status it must have ended on.
    steps: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    name: str
    root: Path
    title: str
    fires: str
    expect: Expect
    slug: str = DEFAULT_SLUG
    brief: str = DEFAULT_BRIEF

    @property
    def branch(self) -> str:
        from ..state.schema import BRANCH_PREFIX

        return f"{BRANCH_PREFIX}{self.slug}"

    @property
    def overlay(self) -> Path | None:
        return self.root / "repo" if (self.root / "repo").is_dir() else None

    @property
    def plant(self) -> Path | None:
        return self.root / "plant.sh" if (self.root / "plant.sh").is_file() else None

    @property
    def judge(self) -> Path | None:
        return self.root / "judge.sh" if (self.root / "judge.sh").is_file() else None

    @property
    def replies(self) -> list[Path]:
        folder = self.root / "replies"
        return sorted(folder.glob("*.json")) if folder.is_dir() else []


@lru_cache(maxsize=1)
def cases_root() -> Path:
    """Where the cases live: the repository, not the wheel.

    The bench is the instrument that compares one version of the kit against the
    next, and it is run from a checkout. A tool installed with `uv tool install`
    has no cases, and says so by name rather than reporting an empty suite.
    """
    checkout = Path(__file__).resolve().parents[3] / "bench" / "cases"
    if checkout.is_dir():
        return checkout
    raise StateError(
        "no-cases",
        f"the bench's cases are not in this installation: nothing at {checkout}",
        hint="run the bench from a checkout of the kit",
    )


def case_names(root: Path) -> list[str]:
    if not root.is_dir():
        raise StateError("no-cases", f"{root} is not a directory of cases")
    return sorted(entry.name for entry in root.iterdir() if (entry / CASE_FILE).is_file())


def read_case(root: Path, name: str) -> Case:
    path = root / name / CASE_FILE
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise CaseError("unreadable-case", f"{path} is not valid TOML: {error}") from error
    except OSError as error:
        raise CaseError("unreadable-case", f"{path} could not be read: {error}") from error

    _refuse_unknown(document, _TOP_KEYS, "")
    block = _table(document.get("case", {}), "case")
    _refuse_unknown(block, _CASE_KEYS, "case.")
    wanted = _table(document.get("expect", {}), "expect")
    _refuse_unknown(wanted, _EXPECT_KEYS, "expect.")

    return Case(
        name=name,
        root=root / name,
        title=_text(block.get("title"), "case.title"),
        fires=_text(block.get("fires"), "case.fires"),
        slug=_text(block.get("slug", DEFAULT_SLUG), "case.slug"),
        brief=_text(block.get("brief", DEFAULT_BRIEF), "case.brief"),
        expect=Expect(
            exit_code=_number(wanted.get("exit_code"), "expect.exit_code"),
            status=_one_of(wanted.get("status"), _STATUSES, "expect.status"),
            refusal=_optional_text(wanted.get("refusal"), "expect.refusal"),
            steps={
                name: _one_of(value, _STEP_STATUSES, f"expect.steps.{name}")
                for name, value in _table(wanted.get("steps", {}), "expect.steps").items()
            },
        ),
    )


# --- field checks, each naming what it refused ------------------------------


def _refuse_unknown(table: dict[str, Any], known: set[str], prefix: str) -> None:
    for key in table:
        if key not in known:
            raise CaseError("unknown-key", f"{prefix}{key} is not something a case declares")


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseError("bad-value", f"{where} must be a table")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseError("bad-value", f"{where} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, where: str) -> str:
    return "" if value is None else _text(value, where)


def _number(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CaseError("bad-value", f"{where} must be a whole number")
    return value


def _one_of(value: Any, choices: tuple[str, ...], where: str) -> str:
    if value not in choices:
        raise CaseError("bad-value", f"{where} must be one of {', '.join(choices)}, not {value!r}")
    return value
