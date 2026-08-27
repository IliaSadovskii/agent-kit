"""What a case is: what it plants, and what must fire.

A case is a directory. Everything in it is optional except the declaration:

    case.toml     what this plants and what must fire
    repo/         files laid over the baseline project before its first commit
    plant.sh      run in the repository afterwards, to put the trap in place
    replies/      what the fake provider answers, one file per attempt, in name
                  order; a `.sh` of the same name is what that session did
    judge.sh      read the run and say whether the mechanism fired

The first three are the trap, and `disarm.py` takes all three away to ask
whether the case is reading them or the night around them. `case.toml` is the
question the case asks and is never touched.

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

_TOP_KEYS = {"case", "expect", "batch", "sitting"}
_CASE_KEYS = {"title", "fires", "slug", "brief", "wait", "no_disarm"}
_EXPECT_KEYS = {"exit_code", "status", "refusal", "steps", "features"}
_BATCH_KEYS = {"name", "features"}
_SITTING_KEYS = {"telling", "answers"}
_FEATURE_KEYS = {"slug", "brief", "needs"}

_STATUSES = ("created", "running", "done", "failed", "stopped")
_STEP_STATUSES = ("pending", "running", "asking", "passed", "failed")
_FEATURE_STATUSES = ("pending", "running", "done", "failed", "stopped", "skipped")


class CaseError(StateError):
    """The case itself is wrong. Nothing was judged, and nothing can be."""


@dataclass(frozen=True)
class Expect:
    """What must be true of the run afterwards, if the mechanism fired."""

    exit_code: int
    status: str = ""
    #: A substring of the reason the run recorded. Usually the refusal's code.
    refusal: str = ""
    #: Step name -> the status it must have ended on.
    steps: dict[str, str] = field(default_factory=dict)
    #: Feature name -> the status it must have ended on. A batch case only:
    #: several runs have no one status between them.
    features: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SittingCase:
    """A case that drives an hour with the owner rather than a run.

    The one thing the bench learns for S8a, and it is the same kind of thing it
    learned for S8: a second way in, and nothing below it changes. The telling
    comes from a file, because that is where a telling comes from; the answers
    come down the standard input, because that is where an answer comes from and
    a sitting is with somebody. Empty answers is a real case — it is the world
    in which there is nobody to ask.
    """

    telling: str
    answers: tuple[str, ...] = ()


@dataclass(frozen=True)
class BatchFeature:
    slug: str
    brief: str
    needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class BatchCase:
    """A case that drives a batch rather than one run.

    The one thing the bench learns for S8. Everything else — the world, the
    fake provider, the judges, the `gh` that is a script — is untouched: a
    batch is several ordinary runs, which is the whole claim S8 makes.
    """

    name: str
    features: tuple[BatchFeature, ...]

    def declaration(self) -> str:
        lines = [f'name = "{self.name}"']
        for feature in self.features:
            lines += ["", f"[features.{feature.slug}]", f'brief = "{feature.brief}"']
            if feature.needs:
                lines.append("needs = [" + ", ".join(f'"{one}"' for one in feature.needs) + "]")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class Case:
    name: str
    root: Path
    title: str
    fires: str
    expect: Expect
    slug: str = DEFAULT_SLUG
    brief: str = DEFAULT_BRIEF
    #: How long this case's run waits for the machine. `None` leaves it to the
    #: configuration, which is what every case about something else wants.
    wait: int | None = None
    #: The batch this case drives, where it drives one instead of a single run.
    batch: BatchCase | None = None
    #: The sitting this case drives, where it drives one instead of a run.
    sitting: SittingCase | None = None
    #: Why nothing can honestly be taken away from this case, where that is so.
    #: Empty means the mechanical disarm applies — see `disarm.py`. A case that
    #: fills this in is exempt from being measured, so it is printed every time
    #: the check runs rather than being agreed to once in a note.
    no_disarm: str = ""

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

    def replies_for(self, slug: str) -> list[Path]:
        """A batch case answers per feature: `replies/<feature>/*.json`."""
        folder = self.root / "replies" / slug
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
    if "batch" in document and "sitting" in document:
        # Two ways in, and the runner picks one. A case declaring both would be
        # measuring whichever the runner happens to try first, which is a case
        # that cannot say what it measures.
        raise CaseError(
            "two-ways-in", "a case drives a batch or a sitting, and a case declaring both drives neither"
        )
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
        wait=None if "wait" not in block else _number(block["wait"], "case.wait"),
        no_disarm=_prose(block.get("no_disarm"), "case.no_disarm"),
        batch=_batch(document.get("batch")),
        sitting=_sitting(document.get("sitting")),
        expect=Expect(
            exit_code=_number(wanted.get("exit_code"), "expect.exit_code"),
            status=(
                ""
                if ("batch" in document or "sitting" in document) and "status" not in wanted
                else _one_of(wanted.get("status"), _STATUSES, "expect.status")
            ),
            refusal=_optional_text(wanted.get("refusal"), "expect.refusal"),
            steps={
                name: _one_of(value, _STEP_STATUSES, f"expect.steps.{name}")
                for name, value in _table(wanted.get("steps", {}), "expect.steps").items()
            },
            features={
                name: _one_of(value, _FEATURE_STATUSES, f"expect.features.{name}")
                for name, value in _table(wanted.get("features", {}), "expect.features").items()
            },
        ),
    )


def _sitting(block: Any) -> SittingCase | None:
    if block is None:
        return None
    block = _table(block, "sitting")
    _refuse_unknown(block, _SITTING_KEYS, "sitting.")
    answers = block.get("answers", [])
    if not isinstance(answers, list):
        raise CaseError("bad-value", "sitting.answers must be a list of lines the owner types")
    return SittingCase(
        telling=_text(block.get("telling"), "sitting.telling"),
        answers=tuple(_text(one, "sitting.answers[]") for one in answers),
    )


def _batch(block: Any) -> BatchCase | None:
    if block is None:
        return None
    block = _table(block, "batch")
    _refuse_unknown(block, _BATCH_KEYS, "batch.")
    declared = block.get("features")
    if not isinstance(declared, list) or not declared:
        raise CaseError("bad-value", "batch.features must be a non-empty list of features")
    features = []
    for feature in declared:
        feature = _table(feature, "batch.features[]")
        _refuse_unknown(feature, _FEATURE_KEYS, "batch.features[].")
        needs = feature.get("needs", [])
        if not isinstance(needs, list):
            raise CaseError("bad-value", "batch.features[].needs must be a list")
        features.append(
            BatchFeature(
                slug=_text(feature.get("slug"), "batch.features[].slug"),
                brief=_text(feature.get("brief", DEFAULT_BRIEF), "batch.features[].brief"),
                needs=tuple(_text(one, "batch.features[].needs") for one in needs),
            )
        )
    return BatchCase(name=_text(block.get("name"), "batch.name"), features=tuple(features))


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


def _prose(value: Any, where: str) -> str:
    """A sentence that may be wrapped in the file and is one line when printed."""
    return " ".join(_optional_text(value, where).split())


def _number(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CaseError("bad-value", f"{where} must be a whole number")
    return value


def _one_of(value: Any, choices: tuple[str, ...], where: str) -> str:
    if value not in choices:
        raise CaseError("bad-value", f"{where} must be one of {', '.join(choices)}, not {value!r}")
    return value
