"""Reading a run file written by an older kit.

A file says which schema wrote it. Older is migrated on the way in; newer is
refused, because guessing at a shape you have not seen is how a night ends with
a record nobody can trust.
"""

from __future__ import annotations

from typing import Any, Callable

from ..errors import StateError
from .schema import SCHEMA_VERSION

#: schema version -> what turns it into the next one.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}

OLDEST_SCHEMA = SCHEMA_VERSION


def migrate(data: dict[str, Any], *, where: str = "run.json") -> dict[str, Any]:
    version = data.get("schema", SCHEMA_VERSION)
    if not isinstance(version, int) or isinstance(version, bool):
        raise StateError("bad-field: schema", f"{where}: schema must be a whole number")
    if version > SCHEMA_VERSION:
        raise StateError(
            "schema-too-new",
            f"{where} was written by a newer kit (schema {version}, this kit reads {SCHEMA_VERSION})",
            hint="upgrade agent-kit",
        )
    if version < OLDEST_SCHEMA:
        raise StateError("schema-too-old", f"{where}: schema {version} is older than this kit can migrate")

    while version < SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise StateError("no-migration", f"{where}: nothing turns schema {version} into {version + 1}")
        data = step(dict(data))
        version += 1
        data["schema"] = version
    return data
