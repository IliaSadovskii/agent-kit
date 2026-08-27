"""The hour in which somebody says what tonight builds.

`agent-kit batch new <file>` reads a declaration. This is that declaration
written in front of the person whose evening it is, and the two things a child
of the night cannot supply are the whole of why it exists: the batch is visible
at once, and the owner is here. So the questions the night would have nobody to
ask are answered while somebody is standing there, and then it gets out of the
way — the artefact is the same file, and `batch new` is still the one door onto
a graph.

It reuses the sitting's shape whole (`sitting/room.py`) and lives here rather
than there, which keeps the arrow pointing one way: a batch may know what a
sitting is, and nothing about a sitting knows what a batch is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from ..knowledge import FRAME, Knowledge, KnowledgeError
from ..logs import get_logger
from ..project import require_project
from ..sitting.room import Sitting as Held
from ..sitting.telling import SittingRefusal, Telling
from ..state.store import write_whole
from .declaration import (
    Declaration,
    Feature,
    Frame,
    Scenario,
    refuse_a_graph_that_cannot_run,
    render_declaration,
)
from .gate import refuse_unless_answered, unanswered_about_the_project
from .steps import COMPOSING, SETTLING

log = get_logger("batch.composing")

DECLARATIONS = "declarations"


@dataclass
class Composing:
    """What the sitting came to, for the person who is standing here."""

    name: str
    declaration: Declaration | None = None
    #: Where the file went, and where each frame's block went. Printed, because
    #: the kit does not commit and the owner reads a diff.
    written: list[Path] = field(default_factory=list)
    asked: list[tuple[str, str]] = field(default_factory=list)
    #: True when this project keeps no knowledge, so no frame got a block. Said
    #: out loud rather than left to be noticed by its absence.
    blocks_had_nowhere_to_go: bool = False


class ComposingSitting(Held):
    """One telling about an evening, from the terminal to a declaration."""

    held_for = "batch compose"

    def __init__(self, name: str, *args, out: Path | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        #: Where the declaration is written. None takes the kit's own place for
        #: them, which is inside the project and not ignored by git: it is what
        #: the owner composed, and it is theirs to keep.
        self.out = out

    def _sit(self, telling: Telling) -> Composing:
        # Before a single session is paid for. A project with no way to run its
        # own checks cannot start a night whatever is composed, and finding that
        # out after two turns is finding it out at the owner's expense.
        said = unanswered_about_the_project(require_project(self.root))
        if said:
            raise said[0].refusal()

        opened = self._open(telling)
        knowledge = opened.knowledge
        keeps = knowledge.declared
        outcome = Composing(name=self.name, blocks_had_nowhere_to_go=not keeps)

        enclosures = [
            ("what the owner said, with a number on every line", telling.numbered()),
            ("the project's knowledge, as an index", knowledge.index()),
        ]
        contract = COMPOSING.contract_in(keeps)
        composed = self._turn(
            opened, COMPOSING, 0, enclosures,
            judge=lambda output: read(output, telling, self.name, keeps),
            contract=contract,
        )
        declaration = read(composed, telling, self.name, keeps)
        self._print(declaration)

        asked = self.ask(
            [(one.slug, one.question) for one in _questions(composed)], opened.room
        )
        outcome.asked = asked
        if asked:
            settled = self._turn(
                opened, SETTLING, 1,
                enclosures
                + [
                    ("the evening you composed", _as_json(composed)),
                    (
                        "what the owner answered, and nothing else was asked",
                        "\n".join(f"{slug}: {answer}" for slug, answer in asked),
                    ),
                ],
                judge=lambda output: _settled(output, telling, self.name, keeps),
                contract=SETTLING.contract_in(keeps),
            )
            declaration = _settled(settled, telling, self.name, keeps)
            self._print(declaration)

        # The gate over what came out. It cannot fire against a contract that
        # already makes every one of its fields non-empty — and it is asked
        # anyway, because the day somebody loosens one of those fields is the
        # day a night with no bounds starts without anything noticing.
        refuse_unless_answered(declaration, require_project(self.root))

        declaration, files = self._write(declaration, knowledge)
        outcome.declaration = declaration
        outcome.written = files
        self._told(outcome)
        return outcome

    # --- writing, and nothing is written until all of it resolves ----------

    def _write(self, declaration: Declaration, knowledge: Knowledge) -> tuple[Declaration, list[Path]]:
        """The blocks first, then the file that names them.

        In that order because the file carries the identifiers: a declaration on
        disk whose frames name blocks nobody wrote is a batch that will try to
        close what is not there. Every address resolves before anything is
        edited, which is the rule `record` already keeps.
        """
        touched: list[Path] = []
        frames = list(declaration.frames)
        if knowledge.exists:
            for frame in frames:
                knowledge.resolve(frame.at)
            claimed: set[str] = set()
            settled: list[Frame] = []
            for frame in frames:
                # `claimed` is what keeps two frames worded the same from being
                # one block: the second cannot be handed the name the first is
                # already using, and the salt walks on the same way every time.
                id = knowledge.free_id(self.name, frame.what, self.name, claimed)
                claimed.add(id)
                touched.extend(
                    knowledge.write(
                        at=frame.at, run=self.name, body=frame.what, id=id,
                        date=self.today, kind=FRAME,
                    )
                )
                settled.append(Frame(what=frame.what, at=frame.at, id=id))
            frames = settled

        declaration = Declaration(
            name=declaration.name,
            features=declaration.features,
            inside=declaration.inside,
            outside=declaration.outside,
            scenarios=declaration.scenarios,
            frames=tuple(frames),
        )
        path = self.out or (self.root / ".agent-kit/v3" / DECLARATIONS / f"{self.name}.toml")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, render_declaration(declaration))
        log.info("%s composed: %s features, %s frames", self.name, len(declaration.features), len(frames))
        return declaration, [path, *dict.fromkeys(touched)]

    # --- what the person standing here is shown ---------------------------

    def _print(self, declaration: Declaration) -> None:
        self.say("")
        for feature in declaration.features:
            waits = f"  после {feature.needs[0]}" if feature.needs else ""
            self.say(f"  фича   {feature.slug:<20}{waits}")
        for line in declaration.inside:
            self.say(f"  внутри {line}")
        for line in declaration.outside:
            self.say(f"  снаружи {line}")
        for scenario in declaration.scenarios:
            self.say(f"  сценарий  {scenario.what} → {scenario.ends}")
        for frame in declaration.frames:
            self.say(f"  рамка  {frame.what}  ({frame.at})")
        self.say("")

    def _told(self, outcome: Composing) -> None:
        self.say(f"  фич: {len(outcome.declaration.features)}; рамок: {len(outcome.declaration.frames)}")
        for path in outcome.written:
            self.say(f"  {path}")
        if outcome.blocks_had_nowhere_to_go:
            self.say("  Проект знания не держит, поэтому блоков рамок не написано.")
        self.say("")
        self.say("  Кит не коммитит: прочитайте diff и закоммитьте сами.")
        self.say(f"  Дальше: agent-kit batch new {outcome.written[0]}")


# --- what an answer has to be before it is one ------------------------------


def read(output: dict[str, Any], telling: Telling, name: str, keeps_knowledge: bool) -> Declaration:
    """The composition, judged and turned into the declaration a program writes.

    The graph is refused by the same three names `batch new` refuses it by, and
    from the same function: a cycle found here and a cycle found there is one
    fault, and giving it two codes would make a reader tell them apart to do the
    same thing about both.
    """
    features = [_feature(one, index, telling) for index, one in enumerate(output.get("features") or [])]
    slugs = [one.slug for one in features]
    if len(set(slugs)) != len(slugs):
        raise SittingRefusal(
            "feature-named-twice",
            "two features of this evening carry one name: " + ", ".join(sorted(slugs)),
        )
    try:
        refuse_a_graph_that_cannot_run(features)
    except ConfigError as refused:
        raise SittingRefusal(refused.code, refused.detail) from refused

    return Declaration(
        name=name,
        features=tuple(features),
        inside=tuple(_lines(output.get("inside"), "inside")),
        outside=tuple(_lines(output.get("outside"), "outside")),
        scenarios=tuple(
            _scenario(one, index, telling) for index, one in enumerate(output.get("scenarios") or [])
        ),
        frames=tuple(
            _frame(one, index, telling, keeps_knowledge)
            for index, one in enumerate(output.get("frames") or [])
        ),
    )


def _settled(output: dict[str, Any], telling: Telling, name: str, keeps_knowledge: bool) -> Declaration:
    """The second turn, and it may not ask anything.

    One round, and a settling that asks again is a settling that did not settle.
    Refused rather than ignored: a question nobody will ever be shown is worse
    than a question refused, because the session goes on believing it asked.
    """
    still = [one.get("slug") for one in (output.get("features") or []) if str(one.get("question") or "").strip()]
    if still:
        raise SittingRefusal(
            "still-asking",
            "the owner has answered and there is no second round; these still carry a question: "
            + ", ".join(str(one) for one in still),
        )
    return read(output, telling, name, keeps_knowledge)


def _questions(output: dict[str, Any]):
    for one in output.get("features") or []:
        question = " ".join(str(one.get("question") or "").split())
        if question:
            yield _Asked(slug=str(one.get("slug") or ""), question=question)


@dataclass(frozen=True)
class _Asked:
    slug: str
    question: str


def _feature(one: dict[str, Any], index: int, telling: Telling) -> Feature:
    where = f"features[{index}]"
    telling.said(str(one.get("said") or "").strip(), where)
    needs = " ".join(str(one.get("needs") or "").split())
    return Feature(
        slug=_slug(one.get("slug"), f"{where}.slug"),
        brief=_text(one.get("brief"), f"{where}.brief"),
        needs=[_slug(needs, f"{where}.needs")] if needs else [],
    )


def _scenario(one: dict[str, Any], index: int, telling: Telling) -> Scenario:
    where = f"scenarios[{index}]"
    telling.said(str(one.get("said") or "").strip(), where)
    return Scenario(what=_text(one.get("what"), f"{where}.what"), ends=_text(one.get("ends"), f"{where}.ends"))


def _frame(one: dict[str, Any], index: int, telling: Telling, keeps_knowledge: bool) -> Frame:
    where = f"frames[{index}]"
    telling.said(str(one.get("said") or "").strip(), where)
    at = " ".join(str(one.get("at") or "").split())
    if keeps_knowledge and not at:
        # Where the project keeps knowledge the block has to go somewhere a
        # person can find again, and an address the writer guessed is the thing
        # an address exists to prevent.
        raise SittingRefusal(
            "no-address", f"{where} names no record of the knowledge to stand under"
        )
    return Frame(what=_text(one.get("what"), f"{where}.what"), at=at)


def _lines(value: Any, where: str) -> list[str]:
    if not isinstance(value, list):
        raise SittingRefusal("bad-field", f"{where} must be a list of lines")
    return [_text(one, where) for one in value]


def _text(value: Any, where: str) -> str:
    said = " ".join(str(value or "").split())
    if not said:
        raise SittingRefusal("nothing-was-said", f"{where} is empty, and it is one of the things this decides")
    return said


def _slug(value: Any, where: str) -> str:
    from ..state.schema import check_slug
    from ..errors import StateError

    try:
        return check_slug(" ".join(str(value or "").split()))
    except StateError as refused:
        raise SittingRefusal("bad-slug", f"{where}: {refused.detail}") from refused


def _as_json(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)
