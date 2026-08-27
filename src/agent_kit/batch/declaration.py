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

_TOP_KEYS = {"name", "features", "mvp", "scenarios", "frames"}
_FEATURE_KEYS = {"brief", "needs"}
_MVP_KEYS = {"inside", "outside"}
_SCENARIO_KEYS = {"what", "ends"}
_FRAME_KEYS = {"what", "id"}


@dataclass(frozen=True)
class Feature:
    """One feature of the batch: it becomes an ordinary run."""

    slug: str
    brief: str
    needs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Scenario:
    """One pass through the product, and how it ends.

    The ending is the half a night cannot invent: it is what *finished* means
    for work nobody is watching. The gate is its reader, and the person reading
    the declaration is the other.
    """

    what: str
    ends: str


@dataclass(frozen=True)
class Frame:
    """What every feature of this work builds alike.

    `what` reaches each feature's sessions through the run's own field.
    `id` names the block `agent-kit batch compose` wrote into the knowledge, so
    the batch that wrote it can close it when the work is over. A declaration
    somebody wrote by hand carries no identifier, and there is no block to
    close — said out loud rather than papered over.
    """

    what: str
    id: str = ""
    #: Where in the knowledge the block stands. Read by the writer in
    #: `composing.py` and by nothing else, so it is **not** rendered into the
    #: file: by the time a declaration is on disk the block is written, and a
    #: second copy of the address would be a field the reader is a check for.
    at: str = ""


@dataclass(frozen=True)
class Declaration:
    name: str
    features: tuple[Feature, ...]
    #: The two lists the gate reads: what this work is, and what it is not. The
    #: second is the one nobody writes unasked, and it is the only thing that
    #: keeps a session from widening its own brief at 03:00.
    inside: tuple[str, ...] = ()
    outside: tuple[str, ...] = ()
    scenarios: tuple[Scenario, ...] = ()
    frames: tuple[Frame, ...] = ()
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

    refuse_a_graph_that_cannot_run(features)

    mvp = document.get("mvp") or {}
    if not isinstance(mvp, dict):
        raise ConfigError("bad-value", "mvp must be a table")
    _refuse_unknown(mvp, _MVP_KEYS, "mvp.")

    return Declaration(
        name=_name(name),
        features=tuple(features),
        inside=_lines(mvp.get("inside", []), "mvp.inside"),
        outside=_lines(mvp.get("outside", []), "mvp.outside"),
        scenarios=_scenarios(document.get("scenarios", [])),
        frames=_frames(document.get("frames", [])),
        source=path,
    )


def _scenarios(value: Any) -> tuple[Scenario, ...]:
    said = []
    for index, block in enumerate(_list(value, "scenarios")):
        where = f"scenarios[{index}]"
        if not isinstance(block, dict):
            raise ConfigError("bad-value", f"{where} must be a table")
        _refuse_unknown(block, _SCENARIO_KEYS, f"{where}.")
        # `ends` is read and not required here: an ending nobody wrote is what
        # the gate refuses by name, and refusing it as a malformed field would
        # give the same fault two codes.
        said.append(
            Scenario(what=_text(block.get("what"), f"{where}.what"), ends=_said(block.get("ends"), f"{where}.ends"))
        )
    return tuple(said)


def _frames(value: Any) -> tuple[Frame, ...]:
    said = []
    for index, block in enumerate(_list(value, "frames")):
        where = f"frames[{index}]"
        if not isinstance(block, dict):
            raise ConfigError("bad-value", f"{where} must be a table")
        _refuse_unknown(block, _FRAME_KEYS, f"{where}.")
        said.append(
            Frame(what=_text(block.get("what"), f"{where}.what"), id=_said(block.get("id"), f"{where}.id"))
        )
    return tuple(said)


def _lines(value: Any, where: str) -> tuple[str, ...]:
    return tuple(_text(one, where) for one in _list(value, where))


def _said(value: Any, where: str) -> str:
    """A string that may be empty, and may not be anything else."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigError("bad-value", f"{where} must be a string")
    return value.strip()


def render_declaration(declaration: Declaration) -> str:
    """The declaration as the file the owner reads, written by the program.

    The same act as `sitting/write.py`: the session returns fields and the
    program writes the artefact. What comes out here is read straight back by
    `read_declaration`, which is the only claim this function makes.
    """
    lines = [f"name = {_quoted(declaration.name)}", ""]
    if declaration.inside or declaration.outside:
        lines += ["[mvp]", f"inside = {_quoted_list(declaration.inside)}",
                  f"outside = {_quoted_list(declaration.outside)}", ""]
    for scenario in declaration.scenarios:
        lines += ["[[scenarios]]", f"what = {_quoted(scenario.what)}",
                  f"ends = {_quoted(scenario.ends)}", ""]
    for frame in declaration.frames:
        lines += ["[[frames]]", f"what = {_quoted(frame.what)}"]
        if frame.id:
            lines.append(f"id = {_quoted(frame.id)}")
        lines.append("")
    for feature in declaration.features:
        lines += [f"[features.{feature.slug}]", f"brief = {_quoted(feature.brief)}"]
        if feature.needs:
            lines.append(f"needs = {_quoted_list(feature.needs)}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _quoted(value: str) -> str:
    """TOML's basic string, and the four characters that would break out of it."""
    said = " ".join(str(value).split())
    for what, into in (("\\", "\\\\"), ('"', '\\"')):
        said = said.replace(what, into)
    return f'"{said}"'


def _quoted_list(values) -> str:
    return "[" + ", ".join(_quoted(one) for one in values) + "]"


def refuse_a_graph_that_cannot_run(features: list[Feature]) -> None:
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
