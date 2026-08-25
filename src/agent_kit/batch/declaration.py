"""The file the owner writes: what this evening builds, and in what order.

A batch of five features with a brief each does not fit on a command line, and
the hour it is composed in is the one hour the owner spends on the kit. So it is
a file, and `agent-kit batch new <file>` reads it. There is no `--feature` flag
beside this: nine doors with nine checks is the defect the plan measured, and a
second spelling of one act is how it starts.

Everything is refused before anything is created. A half-made batch is a graph
somebody has to repair by hand.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from ..state.schema import check_slug

_TOP_KEYS = {"name", "features"}
_FEATURE_KEYS = {"brief", "needs"}


@dataclass(frozen=True)
class Feature:
    """One feature of the batch: it becomes an ordinary run."""

    slug: str
    brief: str
    needs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Declaration:
    name: str
    features: tuple[Feature, ...]
    source: Path | None = None


def read_declaration(path: Path | str) -> Declaration:
    path = Path(path)
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError("unreadable-batch", f"{path} is not valid TOML: {error}") from error
    except OSError as error:
        raise ConfigError("unreadable-batch", f"{path} could not be read: {error}") from error

    _refuse_unknown(document, _TOP_KEYS, "")
    name = _text(document.get("name"), "name")
    table = document.get("features")
    if not isinstance(table, dict) or not table:
        raise ConfigError("no-features", f"{path} declares no features, and a batch is what it builds")

    features = []
    for slug, block in table.items():
        where = f"features.{slug}"
        if not isinstance(block, dict):
            raise ConfigError("bad-value", f"{where} must be a table")
        _refuse_unknown(block, _FEATURE_KEYS, f"{where}.")
        features.append(
            Feature(
                slug=_slug(slug, where),
                brief=_text(block.get("brief"), f"{where}.brief"),
                needs=[_slug(one, f"{where}.needs") for one in _list(block.get("needs", []), f"{where}.needs")],
            )
        )

    _refuse_a_graph_that_cannot_run(features)
    return Declaration(name=_name(name), features=tuple(features), source=path)


def _refuse_a_graph_that_cannot_run(features: list[Feature]) -> None:
    """Two refusals, and both are about a batch that could never start.

    A need naming nothing is a feature waiting for something that will never
    happen; a cycle is a set of features each waiting for the next. Neither can
    be found later by watching — the batch would simply sit there — so both are
    read out of the file before a single run is created.
    """
    known = {feature.slug for feature in features}
    for feature in features:
        for name in feature.needs:
            if name not in known:
                raise ConfigError(
                    "no-such-feature",
                    f"{feature.slug} needs {name}, which this batch does not declare",
                )
        if len(feature.needs) > 1:
            # A feature is built on the branch of what it needs and opens its
            # pull request against it, and a pull request has one base. Two
            # would mean merging two branches into a third — the kit writing a
            # merge nobody reviewed, which is the one thing §7 of the note
            # refuses. Named here rather than picked silently from the list.
            raise ConfigError(
                "needs-more-than-one",
                f"{feature.slug} needs {', '.join(feature.needs)}; a feature is built on one branch"
                " and opens against it, so it may wait for one thing",
            )

    waiting = {feature.slug: list(feature.needs) for feature in features}
    settled: set[str] = set()
    while True:
        ready = [slug for slug, needs in waiting.items() if slug not in settled and set(needs) <= settled]
        if not ready:
            break
        settled.update(ready)
    left = [slug for slug in waiting if slug not in settled]
    if left:
        raise ConfigError(
            "needs-a-cycle",
            "these features wait for each other and none of them could ever start: " + ", ".join(sorted(left)),
        )


# --- field checks, each naming what it refused ------------------------------


def _refuse_unknown(table: dict[str, Any], known: set[str], prefix: str) -> None:
    for key in table:
        if key not in known:
            raise ConfigError("unknown-key", f"{prefix}{key} is not something the kit reads about a batch")


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("bad-value", f"{where} must be a non-empty string")
    return value.strip()


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError("bad-value", f"{where} must be a list of feature names")
    return value


def _slug(value: Any, where: str) -> str:
    from ..errors import StateError

    try:
        return check_slug(value)
    except StateError as refused:
        raise ConfigError("bad-value", f"{where}: {refused.detail}") from refused


def _name(value: str) -> str:
    """A batch is a directory, so its name is checked the way a run's is."""
    return _slug(value, "name")
