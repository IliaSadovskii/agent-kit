"""The lens that measures what a project declares against what it imports.

Six lenses are named in the plan — tests, dependencies, scenarios, security,
performance, conventions — and this is the first of them, chosen because its
findings are the ones a program can check. A finding nobody can check is prose
with a green tick, and an audit made of those is the second version's audit.

**The program measures, the session classifies, the program checks the answer
against the measurement.** The measurement is two lists: every distribution the
manifest declares, and every top-level module the code imports that is neither
the standard library's nor this project's own. The session cannot name anything
outside them, cannot leave one of them unanswered, and cannot call a package
unused while a module it names is imported on a line the inventory prints.

What is left to the session is the one thing arithmetic cannot do: the join.
A distribution is not imported under its own name — `PyYAML` arrives as `yaml`,
`python-dateutil` as `dateutil` — and some are never imported at all, because
they are plugins, linters or build backends. Naming the modules a distribution
puts on the import path, and saying which of the never-imported ones are real,
is the work; everything either side of it is counted.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ...errors import ConfigError, StateError
from ...steps.contract import Contract, Enum, Records, Text, TextList
from ...steps.definition import StepDefinition
from ..lens import Lens

MANIFEST = "pyproject.toml"

#: The three things a declared dependency can be. `imported` is the ordinary
#: one and the only one that costs the session nothing to say; the other two
#: both owe a reason, because otherwise the cheapest way past this lens is to
#: call the hard rows plugins and say nothing.
IMPORTED = "imported"
USED_WITHOUT_IMPORTING = "used-without-importing"
UNUSED = "unused"
VERDICTS = (IMPORTED, USED_WITHOUT_IMPORTING, UNUSED)

_REQUIREMENT = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)")


class AuditRefusal(StateError):
    """The answer satisfied its contract and is still not an answer.

    Refused like any other attempt: the reason goes into the next input and the
    session is asked again. It is not a failure of the audit until the attempts
    run out — the same shape `SittingRefusal` has, for the same reason.
    """


def normalise(name: str) -> str:
    """PEP 503: the one spelling two manifests of one package agree on."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


@dataclass(frozen=True)
class Declared:
    """One distribution this project declares, and where it declares it."""

    name: str
    groups: tuple[str, ...]

    @property
    def key(self) -> str:
        return normalise(self.name)

    @property
    def where(self) -> str:
        return ", ".join(self.groups)


@dataclass(frozen=True)
class Imported:
    """One top-level module this project's code imports, and where it first does."""

    module: str
    count: int
    #: `path:line`, relative to the commit. What a person disputing a finding
    #: opens, and what a refusal quotes back at a session that called it unused.
    first_seen: str


@dataclass(frozen=True)
class Inventory:
    """What the program measured before anybody was asked anything."""

    commit: str = ""
    branch: str = ""
    dirty: bool = False
    files: int = 0
    manifest: str = ""
    declared: tuple[Declared, ...] = ()
    imports: tuple[Imported, ...] = ()
    #: Measured and deliberately not asked about, so the counts have a
    #: denominator: a filter nobody prints is the silence this layer exists
    #: against.
    stdlib: tuple[str, ...] = ()
    own: tuple[str, ...] = ()
    #: Files the kit could not parse, so a module hiding in one is not counted
    #: as absent.
    unreadable: tuple[str, ...] = ()

    @property
    def keys(self) -> dict[str, Declared]:
        return {one.key: one for one in self.declared}

    @property
    def modules(self) -> dict[str, Imported]:
        return {one.module: one for one in self.imports}

    def as_json(self) -> dict:
        return {
            "commit": self.commit,
            "branch": self.branch,
            "dirty": self.dirty,
            "files": self.files,
            "manifest": self.manifest,
            "declared": [{"name": one.name, "groups": list(one.groups)} for one in self.declared],
            "imports": [
                {"module": one.module, "count": one.count, "first_seen": one.first_seen}
                for one in self.imports
            ],
            "not_asked_about": {"stdlib": list(self.stdlib), "this project's own": list(self.own)},
            "unreadable": list(self.unreadable),
        }


# --- measuring --------------------------------------------------------------


def measure(tree: Path, commit: str = "", branch: str = "", dirty: bool = False, files: int = 0) -> Inventory:
    """Both lists, from the unpacked commit and from nothing else."""
    declared = _declared(tree)
    found, unreadable, mine = _every_import(tree)
    imports = tuple(
        Imported(module=name, count=count, first_seen=first)
        for name, (count, first) in sorted(found.items())
        if name not in sys.stdlib_module_names
    )
    return Inventory(
        commit=commit,
        branch=branch,
        dirty=dirty,
        files=files,
        manifest=MANIFEST,
        declared=declared,
        imports=imports,
        stdlib=tuple(sorted(name for name in found if name in sys.stdlib_module_names)),
        own=tuple(sorted(mine)),
        unreadable=tuple(unreadable),
    )


def _declared(tree: Path) -> tuple[Declared, ...]:
    """Every requirement of the one manifest the kit reads, with its group.

    `[build-system].requires` is deliberately not among them, and this is where
    that is written down: what builds a wheel is installed by whoever builds
    one, and nothing in the project's own code can import it — so every entry
    of it would be measured as imported nowhere, and every one would be a
    finding that is not work.

    One parser and one file. The second version hand-rolled a YAML subset and a
    `#` inside a quoted value truncated a line; the answer to that is not a
    better hand-rolled parser, it is the reader the rest of the kit already
    uses. A project whose dependencies live somewhere else — `package.json`,
    `go.mod`, a requirements file — is told so by name rather than measured
    wrongly.
    """
    path = tree / MANIFEST
    if not path.is_file():
        raise ConfigError(
            "nothing-to-measure",
            f"эта линза читает {MANIFEST}, а в коммите, который она меряет, его нет",
            hint="этой линзе нужен pyproject.toml; другие экосистемы — другая линза",
        )
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as unreadable:
        raise ConfigError(
            "nothing-to-measure", f"{MANIFEST} не прочитался: {unreadable}"
        ) from unreadable

    found: dict[str, list[str]] = {}
    named: dict[str, str] = {}

    def take(where: str, requirements) -> None:
        if not isinstance(requirements, list):
            return
        for requirement in requirements:
            if not isinstance(requirement, str):
                # `{include-group = "..."}` and anything else that is not a
                # requirement. Skipped rather than guessed at.
                continue
            matched = _REQUIREMENT.match(requirement)
            if matched is None:
                continue
            name = matched.group("name")
            key = normalise(name)
            named.setdefault(key, name)
            if where not in found.setdefault(key, []):
                found[key].append(where)

    project = document.get("project") if isinstance(document.get("project"), dict) else {}
    take("project.dependencies", project.get("dependencies"))
    optional = project.get("optional-dependencies")
    if isinstance(optional, dict):
        for extra, requirements in optional.items():
            take(f"project.optional-dependencies.{extra}", requirements)
    groups = document.get("dependency-groups")
    if isinstance(groups, dict):
        for group, requirements in groups.items():
            take(f"dependency-groups.{group}", requirements)

    return tuple(
        Declared(name=named[key], groups=tuple(where))
        for key, where in sorted(found.items())
    )


def _every_import(tree: Path) -> tuple[dict[str, tuple[int, str]], list[str], set[str]]:
    """Every top-level module the code imports, with a count and a first sighting.

    A name is this project's own when it really would resolve to a file of this
    project *from the file that imports it*: a module beside it, or one at a
    root Python puts on the path — the top of the tree and `src/`. Asked per
    occurrence, because that is how the language answers it.

    The first form of this was the stem of any `.py` file anywhere, and it was
    too wide by exactly the amount that matters: `tests/yaml.py` does not shadow
    `yaml` for `src/pkg/foo.py`, but it took `yaml` out of the inventory — and
    the declared `PyYAML` then had nothing importing it, which is an invented
    *remove PyYAML* going straight into the candidate list. The narrow rule is
    the rule, and what it filtered is printed by name either way.
    """
    found: dict[str, tuple[int, str]] = {}
    unreadable: list[str] = []
    mine: set[str] = set()
    roots = [where for where in (tree, tree / "src") if where.is_dir()]
    for path in sorted(tree.rglob("*.py")):
        relative = path.relative_to(tree).as_posix()
        try:
            parsed = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError, ValueError):
            # Counted and named. A file nobody could read is not a file with no
            # imports in it, and saying the second would make a used dependency
            # look like work.
            unreadable.append(relative)
            continue
        for node in ast.walk(parsed):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                # `from . import x` is this project's own by construction, and
                # it names no module to look up.
                names = [node.module.split(".")[0]]
            for name in names:
                if _resolves_locally(name, [path.parent, *roots]):
                    mine.add(name)
                    continue
                count, first = found.get(name, (0, f"{relative}:{getattr(node, 'lineno', 0)}"))
                found[name] = (count + 1, first)
    return found, unreadable, mine


def _resolves_locally(name: str, where: list[Path]) -> bool:
    """Whether an import of `name` from here lands on a file of this project."""
    return any(
        (place / f"{name}.py").is_file() or (place / name / "__init__.py").is_file()
        for place in where
    )


# --- what the session is shown ----------------------------------------------


def enclosures(inventory: Inventory) -> list[tuple[str, str]]:
    """Both lists, enclosed. Reading is never an instruction.

    The tree is there to be read — whether `pytest-cov` is a plugin is a
    question about a file — but no fact the answer is checked against comes
    from it. Everything the judge compares to is here.
    """
    return [
        ("what this project declares as dependencies", _declared_as_text(inventory)),
        ("every module it imports that is neither the standard library nor its own", _imports_as_text(inventory)),
    ]


def _declared_as_text(inventory: Inventory) -> str:
    if not inventory.declared:
        return f"{inventory.manifest} declares no dependencies at all."
    return "\n".join(f"- {one.name} — {one.where}" for one in inventory.declared)


def _imports_as_text(inventory: Inventory) -> str:
    if not inventory.imports:
        return "nothing outside the standard library and this project's own packages is imported."
    return "\n".join(
        f"- {one.module} — imported {one.count} time(s), first at {one.first_seen}"
        for one in inventory.imports
    )


def denominator(inventory: Inventory) -> str:
    """The line that keeps the counts from reading as *your whole repository*."""
    said = (
        f"объявлено: {len(inventory.declared)}; "
        f"измерено импортов: {len(inventory.imports)}; "
        f"не спрашивали — стандартная библиотека: {len(inventory.stdlib)}, "
        f"своё: {len(inventory.own)}"
    )
    if inventory.unreadable:
        said += f"; не разобрано файлов: {len(inventory.unreadable)}"
    return said


# --- judging what came back --------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One piece of work the lens found, in the shape a candidate line is made of."""

    #: `remove` — declared and not imported; `declare` — imported and not
    #: declared. The two directions, and the wording of the line.
    kind: str
    name: str
    why: str
    where: str


@dataclass
class Judged:
    """The answer, once it has been checked against what was measured."""

    declared: list[dict] = field(default_factory=list)
    undeclared: list[dict] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    #: Rows that say a distribution is used without ever being imported. Not
    #: findings, and counted anyway: an audit that called everything a plugin
    #: must not read as an audit that found nothing.
    unimported: list[dict] = field(default_factory=list)
    #: Rows holding a measured module under a name that is not the package's
    #: own. The second thing no program can check, and the one that can hide a
    #: finding rather than invent one — so it is counted beside the first.
    attached: list[dict] = field(default_factory=list)


def judge(output: dict, inventory: Inventory) -> Judged:
    """Every row against the inventory, and every entry of the inventory against the rows."""
    rows = list(output.get("declared") or [])
    others = list(output.get("undeclared") or [])
    keys = inventory.keys
    modules = inventory.modules

    judged = Judged()
    seen: set[str] = set()
    #: Measured module -> the dependency that says it provides it.
    claimed: dict[str, str] = {}

    for index, row in enumerate(rows):
        where = f"declared[{index}]"
        key = normalise(str(row.get("name") or ""))
        standing = keys.get(key)
        if standing is None:
            raise AuditRefusal(
                "not-declared",
                f"{where}.name: {row.get('name')!r} is not one of the {len(keys)} dependencies "
                f"{inventory.manifest} declares",
            )
        if key in seen:
            raise AuditRefusal(
                "named-twice", f"{where}.name: {standing.name} already has a row above this one"
            )
        seen.add(key)

        names = [str(one).strip() for one in (row.get("imports") or []) if str(one).strip()]
        occurring = [modules[name] for name in names if name in modules]
        verdict = str(row.get("verdict") or "")

        # A measured module belongs to one dependency. Two rows claiming one
        # module is a module accounted for twice and found once.
        for name in names:
            if name in modules and name in claimed:
                raise AuditRefusal(
                    "named-twice",
                    f"{where}.imports: {name} is already claimed by {claimed[name]} above, and a "
                    "module the inventory measured comes from one dependency",
                )
        if verdict == IMPORTED:
            # An `imported` row is about modules that really are imported. A
            # name here that the inventory never measured does no work and
            # cannot be checked, so it is not a place to put one.
            unmeasured = [name for name in names if name not in modules]
            if unmeasured:
                raise AuditRefusal(
                    "not-declared",
                    f"{where}.imports: {', '.join(unmeasured)} — {standing.name} is called "
                    f"{IMPORTED}, and these are not among the {len(modules)} modules the "
                    "inventory measured",
                )
        claimed.update({name: standing.name for name in names if name in modules})

        # What the program cannot check, printed instead of hidden. A module
        # whose name is the package's own needs nobody's word — `tabulate`
        # comes from `tabulate`. A module under another name is the session
        # saying so: `PyYAML` really does arrive as `yaml`, and an undeclared
        # `requests` attached to `PyYAML` would look exactly the same and would
        # vanish from the findings. It owes a reason and it is counted openly.
        attached = [one.module for one in occurring if normalise(one.module) != standing.key]
        # There is no second refusal for `imported` with nothing occurring: the
        # check above already requires every name on such a row to be a
        # measured module, and the contract requires at least one name. Two
        # codes for one error leave one of them unreachable, which is what a
        # review caught in S8b and what a test then cannot tell apart.
        if verdict != IMPORTED and occurring:
            first = occurring[0]
            raise AuditRefusal(
                "verdict-against-the-inventory",
                f"{where}: {standing.name} is called {verdict}, and {first.module} is imported "
                f"{first.count} time(s), first at {first.first_seen}",
            )
        if (verdict != IMPORTED or attached) and not str(row.get("why") or "").strip():
            raise AuditRefusal(
                "no-reason-to-remove",
                f"{where}: {standing.name} gives no reason for "
                + (f"holding {', '.join(attached)}" if attached else f"being called {verdict}")
                + ", so the line about it would stand in the report on nobody's word",
            )

        row = {**row, "name": standing.name, "where": standing.where, "imports": names,
               "attached": attached}
        judged.declared.append(row)
        if attached:
            judged.attached.append(row)
        if verdict == UNUSED:
            judged.findings.append(
                Finding(kind="remove", name=standing.name, why=str(row.get("why")), where=standing.where)
            )
        elif verdict == USED_WITHOUT_IMPORTING:
            judged.unimported.append(row)

    missing = [one.name for one in inventory.declared if one.key not in seen]
    if missing:
        raise AuditRefusal(
            "not-accounted-for",
            f"declared: {len(missing)} of {len(inventory.declared)} dependencies have no row: "
            + ", ".join(missing),
        )

    named: set[str] = set()
    for index, row in enumerate(others):
        where = f"undeclared[{index}]"
        module = str(row.get("module") or "").strip()
        standing = modules.get(module)
        if standing is None:
            raise AuditRefusal(
                "not-declared",
                f"{where}.module: {module!r} is not one of the {len(modules)} modules the "
                "inventory measured this project importing",
            )
        if module in named:
            raise AuditRefusal(
                "named-twice", f"{where}.module: {module} already has a row above this one"
            )
        named.add(module)
        judged.undeclared.append({**row, "first_seen": standing.first_seen, "count": standing.count})
        judged.findings.append(
            Finding(
                kind="declare",
                name=module,
                why=str(row.get("why") or ""),
                where=f"{standing.first_seen}, {standing.count} раз(а)",
            )
        )

    unanswered = [one.module for one in inventory.imports if one.module not in set(claimed) | named]
    if unanswered:
        raise AuditRefusal(
            "not-accounted-for",
            f"undeclared: {len(unanswered)} measured module(s) are claimed by no dependency and "
            "have no row of their own: " + ", ".join(unanswered),
        )
    return judged


# --- what the session must return --------------------------------------------

#: Every field has a reader, and they are three: the judge that checks a row
#: against the inventory, the report the person reads, and the candidate line a
#: sitting composes from. Nothing here is printed and left at that.
_DECLARED = Records(
    "declared",
    help="one row for every dependency the enclosed manifest declares — all of them, "
         "including the ones that are plainly in use. Nothing else may be named here",
    shape=(
        Text("name", help="the dependency, spelled the way the manifest spells it"),
        Enum(
            "verdict",
            choices=VERDICTS,
            help="imported — at least one of the modules below is imported somewhere the "
                 "inventory measured; used-without-importing — it is a plugin, a linter, a "
                 "build backend or anything else that is never imported and is still needed; "
                 "unused — nothing in this project needs it",
        ),
        TextList(
            "imports",
            empty_is_an_answer=False,
            help="every module name this distribution puts on the import path. `PyYAML` is "
                 "imported as `yaml`, `python-dateutil` as `dateutil`. This is the join no "
                 "program can do, and the program checks your verdict against it",
        ),
        # Required by the judge for two of the three verdicts, and not by the
        # contract: `required_when` reads a sibling for truth and `verdict` is
        # never empty, so the contract cannot express *unless it says imported*.
        # One enforcer, and it is the judge.
        Text(
            "why",
            required=False,
            help="required for `unused` and for `used-without-importing`, and not read at all "
                 "for `imported`: one line the person acting on this can read. Without it the "
                 "cheapest way past this lens is to call the hard rows plugins and say nothing",
        ),
    ),
)

_UNDECLARED = Records(
    "undeclared",
    help="one row for every measured module that no row above claims. A module nobody claims "
         "and nobody explains is a dependency this project uses and does not declare — it works "
         "on the machine it was written on and breaks on a clean install. Empty is a real answer",
    shape=(
        Text("module", help="the module, spelled as the inventory spells it"),
        Text("why", help="one line: what it is and what declaring it would mean"),
    ),
)

DEPENDENCIES = StepDefinition(
    name="dependencies",
    role="dependencies",
    method="roles/dependencies.md",
    title="what this project declares, against what it imports",
    contract=Contract(fields=(_DECLARED, _UNDECLARED)),
)


# --- what the person reads ---------------------------------------------------


def render_report(inventory: Inventory, judged: Judged, name: str) -> str:
    """The report: what was measured, what was found, and the rest folded away.

    The same shape the pull request keeps, and for the same reason: three things
    open and everything else under a spoiler. What is open here is the work and
    the two counts that could hide it — a lens that called every hard row a
    plugin must not read as a lens that found nothing.
    """
    remove = [one for one in judged.findings if one.kind == "remove"]
    declare = [one for one in judged.findings if one.kind == "declare"]
    lines = [
        f"# Аудит зависимостей — {name}",
        "",
        f"Измерено на коммите `{inventory.commit[:7]}` (ветка `{inventory.branch}`), "
        f"файлов в коммите: {inventory.files}.",
        "",
        denominator(inventory),
        "",
        f"**Найдено: {len(judged.findings)}** — убрать {len(remove)}, объявить {len(declare)}. "
        f"Используется без импорта: {len(judged.unimported)}. "
        f"Привязано по слову сессии: {sum(len(row.get('attached') or []) for row in judged.attached)}.",
    ]
    lines += _warnings(inventory)

    if remove:
        lines += ["", "## Убрать", ""]
        lines += [f"- `{one.name}` — {one.where}. {one.why}" for one in remove]
    if declare:
        lines += ["", "## Объявить", ""]
        lines += [f"- `{one.name}` — {one.where}. {one.why}" for one in declare]
    if judged.unimported:
        lines += [
            "",
            "## Используется без импорта",
            "",
            "Это то, чего программа проверить не может: строка стоит на слове сессии.",
            "",
        ]
        lines += [
            f"- `{row.get('name')}` — {row.get('where')}. {row.get('why')}"
            for row in judged.unimported
        ]

    if judged.attached:
        lines += [
            "",
            "## Привязано по слову сессии",
            "",
            "Модуль, чьё имя расходится с именем пакета. Программа этого не проверяет — и именно "
            "так находку можно спрятать, а не выдумать: чужой импорт, подвешенный к чужому пакету, "
            "выглядит отсюда так же, как настоящий `PyYAML` → `yaml`.",
            "",
        ]
        lines += [
            f"- `{row.get('name')}` → {', '.join(row.get('attached') or [])} — {row.get('why')}"
            for row in judged.attached
        ]

    accounted = [row for row in judged.declared if row.get("verdict") == IMPORTED]
    lines += [
        "",
        f"<details><summary>Учтено и в работу не идёт ({len(accounted)})</summary>",
        "",
    ]
    lines += [
        f"- `{row.get('name')}` → {', '.join(row.get('imports') or []) or '—'} — {row.get('where')}"
        for row in accounted
    ] or ["Ни одной."]
    lines += ["", "</details>", ""]

    # The names, not the number. A filter that is wrong about one of them turns
    # a real dependency into silence, and a count cannot be argued with.
    lines += [
        "",
        f"<details><summary>Не спрашивали ({len(inventory.stdlib) + len(inventory.own)})</summary>",
        "",
        f"Стандартная библиотека: {', '.join(f'`{one}`' for one in inventory.stdlib) or '—'}",
        "",
        f"Своё — модуль лежит рядом с тем, кто его импортирует, или в корне пакета: "
        f"{', '.join(f'`{one}`' for one in inventory.own) or '—'}",
        "",
        "`[build-system].requires` эта линза не читает: сборочные зависимости ставит не тот, "
        "кто запускает проект, и импортов у них здесь быть не может.",
        "",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def _warnings(inventory: Inventory) -> list[str]:
    """What the person has to know before they act on a count.

    None of these refuses anything. A person mid-work is entitled to audit what
    is committed, and a directory taken out of the archive is a fact about the
    repository rather than a fault of the audit — but a used dependency whose
    only importer was excluded looks exactly like work, so it is said before the
    counts are believed.
    """
    said: list[str] = []
    if inventory.dirty:
        said.append(
            "Рабочая копия грязная: измерен последний коммит, а не то, что лежит в файлах."
        )
    if inventory.unreadable:
        said.append(
            "Не разобрано файлов: "
            + ", ".join(f"`{one}`" for one in inventory.unreadable[:5])
            + ". Импорты из них не посчитаны."
        )
    said.append(
        "Каталог, помеченный `export-ignore`, в архив не попадает: если единственный "
        "импортёр зависимости лежал там, она выглядит здесь ненужной."
    )
    return ["", "> " + " ".join(said)] if said else []


def render_candidates(inventory: Inventory, judged: Judged, today: str) -> str:
    """The work, as lines somebody can hand to a composing sitting.

    A telling, not a schema: `agent-kit batch compose` reads a telling and every
    feature it returns points at the line it came from. So the seam needs no
    code on the sitting's side — and the first line says whose words these are,
    because in that sitting `said` means *the owner said this* and here nobody
    did.
    """
    if not judged.findings:
        return ""
    remove = [one for one in judged.findings if one.kind == "remove"]
    declare = [one for one in judged.findings if one.kind == "declare"]
    lines = [
        f"Это измерил кит: аудит зависимостей, {today}, коммит {inventory.commit[:7]} "
        f"(ветка {inventory.branch}). Не слова владельца — прочитайте и поправьте, "
        "прежде чем отдавать в `agent-kit batch compose`.",
        f"Объявлено {len(inventory.declared)}; убрать {len(remove)}; объявить {len(declare)}; "
        f"используется без импорта {len(judged.unimported)}.",
        "",
    ]
    for one in remove:
        lines.append(f"- Убрать `{one.name}` из {one.where}: не импортируется нигде. {one.why}")
    for one in declare:
        lines.append(f"- Объявить `{one.name}`: импортируется ({one.where}) и не объявлен. {one.why}")
    return "\n".join(lines) + "\n"


class DependencyLens(Lens):
    """The first of the six, and the one whose findings arithmetic can check."""

    name = "dependencies"
    title = "что проект объявляет против того, что он импортирует"
    definition = DEPENDENCIES

    def measure(self, tree: Path, unpacked) -> Inventory:
        return measure(
            tree,
            commit=unpacked.commit,
            branch=unpacked.branch,
            dirty=unpacked.dirty,
            files=unpacked.files,
        )

    def enclose(self, measured: Inventory) -> list[tuple[str, str]]:
        return enclosures(measured)

    def inventory(self, measured: Inventory) -> dict:
        return measured.as_json()

    def judge(self, output: dict, measured: Inventory) -> Judged:
        return judge(output, measured)

    def report(self, measured: Inventory, judged: Judged, name: str) -> str:
        return render_report(measured, judged, name)

    def candidates(self, measured: Inventory, judged: Judged, today: str) -> str:
        return render_candidates(measured, judged, today)

    def said(self, measured: Inventory, judged: Judged) -> list[str]:
        remove = sum(1 for one in judged.findings if one.kind == "remove")
        declare = len(judged.findings) - remove
        return [
            f"  коммит {measured.commit[:7]} ({measured.branch}), {denominator(measured)}",
            f"  убрать: {remove}; объявить: {declare}; "
            f"используется без импорта: {len(judged.unimported)}",
        ]
