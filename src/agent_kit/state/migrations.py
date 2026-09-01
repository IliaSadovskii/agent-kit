"""Reading a run file written by an older kit.

A file says which schema wrote it. Older is migrated on the way in; newer is
refused, because guessing at a shape you have not seen is how a night ends with
a record nobody can trust.
"""

from __future__ import annotations

from typing import Any, Callable

from .. import __version__
from ..errors import StateError
from .schema import SCHEMA_VERSION, release

#: schema version -> what turns it into the next one.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def _brief_arrives(data: dict[str, Any]) -> dict[str, Any]:
    """Schema 2 — a run says what it is for.

    Schema 1 predates the feature steps, so nothing it holds was ever built
    from a brief. An older run gets an empty one rather than an invented one.
    """
    data.setdefault("brief", None)
    return data


MIGRATIONS[1] = _brief_arrives


def _a_step_may_be_asking(data: dict[str, Any]) -> dict[str, Any]:
    """Schema 3 — a step may be waiting for a person.

    Nothing in a schema 2 file changes: no run written before this could have
    held `asking`. What the number buys is the refusal in the other direction —
    a kit that does not know the status must say `schema-too-new` rather than
    read a waiting step as a broken one.
    """
    return data


MIGRATIONS[2] = _a_step_may_be_asking


def _a_run_may_have_a_tree(data: dict[str, object]) -> dict[str, object]:
    """Schema 4 — a run says what it builds on, where it builds, and what it waits for.

    A schema 3 file gains none of the three: it was built in the project itself,
    off the project's default branch, waiting for nothing. What the number buys
    is the refusal in the other direction — a kit that does not know `tree`
    would run such a file in the project, which is two runs in one working copy.
    """
    return data


MIGRATIONS[3] = _a_run_may_have_a_tree


def _a_run_may_carry_a_frame(data: dict[str, object]) -> dict[str, object]:
    """Schema 5 — a run carries what the work it belongs to builds alike.

    A schema 4 file gains nothing: there were no frames to carry, and a run
    started by hand has none in any schema. What the number buys is the refusal
    in the other direction — a kit that does not know `frame` would run a
    feature of a batch without the one thing every feature of it shares, and
    nothing in its record would say the line was dropped.
    """
    return data


MIGRATIONS[4] = _a_run_may_carry_a_frame


def oldest_schema() -> int:
    """The oldest file this kit can read: whatever the migrations reach back to.

    Two constants that must be kept in step are one constant too many — the
    first real migration would have been refused before the loop ever saw it.
    """
    return min(MIGRATIONS) if MIGRATIONS else SCHEMA_VERSION


def migrate(data: dict[str, Any], *, where: str = "run.json") -> dict[str, Any]:
    version = data.get("schema", SCHEMA_VERSION)
    if not isinstance(version, int) or isinstance(version, bool):
        raise StateError("bad-field: schema", f"{where}: schema must be a whole number")
    if version > SCHEMA_VERSION:
        raise StateError(
            "schema-too-new",
            f"{where} написан китом новее (схема {version}, этот кит читает {SCHEMA_VERSION})",
            hint="обновите agent-kit",
        )
    if version < oldest_schema():
        raise StateError("schema-too-old", f"{where}: схема {version} старше того, что этот кит умеет мигрировать")

    _check_kit(data.get("kit"), where)

    while version < SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise StateError("no-migration", f"{where}: ничто не превращает схему {version} в {version + 1}")
        data = step(dict(data))
        version += 1
        data["schema"] = version
    return data


def _check_kit(kit: object, where: str) -> None:
    """Open question 3: a file says which kit wrote it, and a newer one is refused.

    The schema number is the compatibility contract, but a kit of the same
    schema can still have learned to write things this one would misread. A file
    from a newer kit is refused rather than guessed at.
    """
    if kit is None:
        return
    if not isinstance(kit, str) or not release(kit):
        raise StateError("bad-field: kit", f"{where}: kit must be a version string")
    if release(kit) > release(__version__):
        raise StateError(
            "kit-too-new",
            f"{where} написан agent-kit {kit}, а этот — {__version__}",
            hint="обновите agent-kit",
        )
