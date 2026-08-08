#!/usr/bin/env python3
"""Audit a project's knowledge documents, mechanically.

    check.py [project root] [--status] [--state] [--sync] [--offline]
    check.py . --run .agent-kit/runs/<slug>      what a run at step done may not leave behind

This is what `/agent-kit:blueprint --check` runs, and what every other command runs before it
starts. It exists as a program rather than as instructions because a skill cannot be invoked by
another skill: told to "run blueprint --check", a build command went looking for an executable,
found none, and carried on without the check — silently, in every autonomous run.

It reads. It judges nothing: no quality, no research, no opinion about the prose. The one thing it
writes is an entry's state line — only what a merged pull request already decided, and only when
asked with `--sync`. A preflight that writes is how a command that meant to read left the tree dirty
for the next one.

Silent when clean, except for tests marked `agent-kit:unmet`: those are listed whenever they exist,
because nothing else in a run ever mentions them, and they change no exit code — a recorded promise
is not a defect. `--status` always prints where the project stands, and names what is `planned`.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

KNOWLEDGE = "docs/knowledge"
MANIFEST = ".agent-kit/project.yml"
DEBT = "docs/technical_debt.md"
MARK = "agent-kit:unmet"
SCENARIO_MARK = "agent-kit:scenario"
DIGEST_LEN = 8
UNMET_SHOWN = 10

KEY_RE = re.compile(r"^`key:\s*([^`·]+?)\s*`(?:\s*·\s*`state:\s*([^`]+?)\s*`)?", re.M)
HEADING_RE = re.compile(r"^###\s+(.+)$", re.M)
FIELDS_RE = re.compile(r"^fields:\s*(.+)$", re.M)
SOURCE_RE = re.compile(r"`source:\s*([^#`]+)#([^@`]+?)\s*@([0-9a-f]+)`")
NOTE_RE = re.compile(r"^>\s*\*\*\[(assumed|found|stale)\b([^\]]*)\]\*\*\s*(.*)$", re.M)
REF_RE = re.compile(r"`([a-z][a-z0-9_]*\.[a-z0-9_]+)`")
# entities and actors are keys without a dot, so the entry part is one or more segments
MARK_RE = re.compile(re.escape(MARK) + r"[:\s]*([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*)?")
# A screen the product opens on is reached from nowhere by design; the entry says so in its own
# words, in the project's language, so this looks for the marker rather than for a sentence.
ENTRY_POINT_RE = re.compile(r"`entry_point`", re.I)
STATE_LINE_RE = re.compile(r"(`key:\s*%s\s*`\s*·\s*`state:\s*)building \(pr:\s*(\d+)\)(\s*`)")

SLOTS = ("product", "actors", "entities", "actions", "screens", "integrations", "scenarios", "stack")

# What `step` may hold. The first eight are a run's own; `building` and `closing` are written by the
# driver on a batch's file. Kept here rather than only in the template's prose, because a value
# nothing recognises leaves whatever is watching that field waiting for a state that never comes.
STEPS = ("queued", "design", "build", "verify", "deliver", "done", "blocked", "skipped",
         "building", "closing",
         # an mvp's own phases, written by `mvp` on its own file as it moves between them
         "gate", "auditing", "proving")

# What a dependency manifest is called, across the ecosystems a project here might use. Only their
# names are known — the check reads none of them, it just notices one nobody recorded.
MANIFEST_NAMES = ("composer.json", "package.json", "requirements.txt", "pyproject.toml", "go.mod",
                  "Gemfile", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts",
                  "Package.swift", "mix.exs", "pubspec.yaml")


def digest(text: str) -> str:
    """The hash recorded beside a `source:` and a dependency manifest.

    Defined here so that whoever writes it and whoever verifies it cannot disagree. Blueprint asks
    this program for the value instead of inventing one — an earlier version left the algorithm to
    whoever happened to be reading, which made every recorded hash unverifiable by anything else.
    """
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:DIGEST_LEN]


# --------------------------------------------------------------------------------------------
# the manifest
#
# A deliberately narrow reader for the shapes project.yml actually has: `key: value`, one level of
# nesting, and comments. Anything deeper is not read rather than half-read.


def read_manifest(path: Path) -> dict:
    data: dict = {}
    stack = [(-1, data)]
    if not path.is_file():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if ":" not in line:
            continue
        key, _, value = line.strip().partition(":")
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else data
        if value:
            parent[key.strip()] = value
        else:
            child: dict = {}
            parent[key.strip()] = child
            stack.append((indent, child))
    return data


# --------------------------------------------------------------------------------------------
# the documents


class Entry:
    def __init__(self, heading: str, key: str, state: str, body: str, line: int):
        self.heading, self.key, self.state, self.body, self.line = heading, key, state, body, line


class Doc:
    def __init__(self, path: Path):
        self.path = path
        self.slot = path.stem
        self.text = path.read_text(encoding="utf-8")
        found = FIELDS_RE.search(self.text)
        self.fields = [f.strip() for f in found.group(1).split(",")] if found else []
        self.entries = self._entries()

    def _entries(self) -> list:
        # An entry is a heading whose next non-empty line carries its machine key; a heading without
        # one is a section of prose (product.md is all of those) and is not an entry.
        out = []
        marks = [(m.start(), m.group(1)) for m in HEADING_RE.finditer(self.text)]
        for i, (start, heading) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(self.text)
            body = self.text[start:end]
            key = KEY_RE.search(body)
            if not key:
                continue
            out.append(Entry(heading.strip(), key.group(1).strip(), (key.group(2) or "").strip(),
                             body, self.text.count("\n", 0, start) + 1))
        return out

    def commented(self, entry: Entry) -> bool:
        """A template's example lives inside an HTML comment and is not a record."""
        before = self.text[:self.text.index(entry.body)]
        return before.count("<!--") > before.count("-->")


def field_content(body: str, field: str, fields: list) -> str:
    """A field runs until the next field or the next heading — its answer may be a list below it."""
    start = re.search(rf"^\*\*{re.escape(field)}:?\*\*[:：]?", body, re.M)
    if not start:
        return ""
    rest = body[start.end():]
    stops = [rest.find("\n###")]
    for other in fields:
        if other == field:
            continue
        found = re.search(rf"^\*\*{re.escape(other)}:?\*\*", rest, re.M)
        if found:
            stops.append(found.start())
    stops = [s for s in stops if s >= 0]
    return rest[:min(stops)].strip() if stops else rest.strip()


# --------------------------------------------------------------------------------------------
# the checks


class Report:
    def __init__(self):
        self.groups: dict = {}
        self.notes: list = []
        self.stale: list = []
        self.states: list = []
        self.unmet: list = []
        self.debt: list = []
        self.drift: list = []

    def add(self, group: str, line: str) -> None:
        self.groups.setdefault(group, []).append(line)

    @property
    def clean(self) -> bool:
        return not self.groups


def check_fields(docs: list, report: Report) -> None:
    for doc in docs:
        if not doc.fields:
            continue
        for entry in doc.entries:
            if doc.commented(entry):
                continue
            empty = [f for f in doc.fields if not field_content(entry.body, f, doc.fields)]
            if empty:
                report.add("Fields", f"{doc.path.name}:{entry.line} {entry.key} — {', '.join(empty)}")


def keys(docs: list) -> set:
    """Every entry key the knowledge declares, commented-out drafts aside."""
    return {entry.key for doc in docs for entry in doc.entries if not doc.commented(entry)}


def check_references(docs: list, report: Report) -> None:
    defined = keys(docs)
    actors = {k for k in defined if "." not in k}

    for doc in docs:
        for entry in doc.entries:
            if doc.commented(entry):
                continue
            if doc.slot == "actions":
                actor = entry.key.split(".", 1)[0]
                if actor not in actors and actors:
                    report.add("References", f"{doc.path.name}:{entry.line} {entry.key} — no actor {actor!r}")
            # A backticked `a.b` is a knowledge key only when `a` is a declared actor, or when it is
            # a screen. Everything else with a dot in it is prose — a config path, a class, a
            # filename — and guessing at those would bury the real findings.
            for ref in set(REF_RE.findall(entry.body)):
                if ref == entry.key or ref in defined:
                    continue
                if ref.split(".", 1)[0] in actors or ref.startswith("screen."):
                    report.add("References",
                               f"{doc.path.name}:{entry.line} {entry.key} → {ref} is not defined anywhere")


def check_orphans(docs: list, report: Report) -> None:
    """An orphan is something nothing leads to. A screen the product opens on leads from nowhere by
    definition, so a file that calls one an entry point takes it out of the count."""
    by_slot = {doc.slot: doc for doc in docs}
    everything = "\n".join(doc.text for doc in docs)

    actions = by_slot.get("actions")
    if actions and "actors" in by_slot:
        used = {e.key.split(".", 1)[0] for e in actions.entries}
        for entry in by_slot["actors"].entries:
            if by_slot["actors"].commented(entry):
                continue
            if entry.key not in used:
                report.add("Orphans", f"actors.md:{entry.line} {entry.key} — no action belongs to this actor")

    for slot in ("entities", "screens"):
        doc = by_slot.get(slot)
        if not doc:
            continue
        for entry in doc.entries:
            if doc.commented(entry):
                continue
            elsewhere = everything.count(f"`{entry.key}`") - entry.body.count(f"`{entry.key}`")
            if elsewhere == 0 and not ENTRY_POINT_RE.search(entry.body):
                report.add("Orphans", f"{doc.path.name}:{entry.line} {entry.key} — named nowhere else")


def check_sources(root: Path, docs: list, report: Report) -> None:
    stale_format = 0
    for doc in docs:
        for path_text, heading, recorded in SOURCE_RE.findall(doc.text):
            target = root / path_text.strip()
            if not target.is_file():
                report.add("Sources", f"{doc.path.name} → {path_text} does not exist")
                continue
            section = section_of(target.read_text(encoding="utf-8"), heading.strip())
            if section is None:
                report.add("Sources", f"{doc.path.name} → {path_text}#{heading.strip()} — no such heading")
            elif len(recorded) != DIGEST_LEN:
                # Before this program owned the algorithm, the rule said "the hash is that section
                # as you read it" — so the value was invented, and its length gives it away. It
                # cannot be compared with anything, and nothing follows about the document.
                stale_format += 1
            elif digest(section) != recorded:
                report.add("Sources", f"{doc.path.name} → {path_text}#{heading.strip()} changed "
                                      f"({recorded} → {digest(section)})")
    if stale_format:
        report.add("Sources", f"{stale_format} source hashes predate this program and mean nothing "
                              f"— re-record them with `check.py . --record`; no document changed")


def section_of(text: str, heading: str) -> str | None:
    marks = [(m.start(), m.group(0)) for m in re.finditer(r"^#{1,6}\s+.+$", text, re.M)]
    for i, (start, line) in enumerate(marks):
        if line.lstrip("#").strip().lower() == heading.lower():
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            return text[start:end]
    return None


def check_stack(root: Path, manifest: dict, report: Report) -> None:
    checks = manifest.get("checks") or {}
    researched = checks.get("stack_researched")
    if researched:
        try:
            when = dt.date.fromisoformat(str(researched))
            if (dt.date.today() - when).days > 182:
                report.add("Stack", f"researched {researched} — over six months ago")
        except ValueError:
            report.add("Stack", f"stack_researched is not a date: {researched}")
    recorded_deps = checks.get("deps") or {}
    for name, recorded in recorded_deps.items():
        target = root / name
        if not target.is_file():
            report.add("Stack", f"{name} is recorded but missing")
        elif digest(target.read_text(encoding="utf-8")) != recorded:
            report.add("Stack", f"{name} changed since the library map was written")

    # A manifest nobody wrote down is a whole ecosystem of dependencies under no watch at all —
    # the same failure as a stale hash, one level up, and invisible because the loop above only
    # ever visits what was already recorded.
    for name in tracked_manifests(root):
        if name not in recorded_deps:
            report.add("Stack", f"{name} is a dependency manifest that project.yml does not record "
                                f"— nothing watches it for changes")


def tracked_manifests(root: Path) -> list:
    listed = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files"],
                            cwd=root, capture_output=True, text=True)
    if listed.returncode != 0:
        return []
    return sorted(p for p in listed.stdout.splitlines() if Path(p).name in MANIFEST_NAMES)


def check_mvp(root: Path, manifest: dict, docs: list, report: Report) -> list:
    """What `mvp` cannot start without, and nothing more.

    An `mvp` with a thin blueprint has no stopping condition — a sprint with one still delivers five
    features. So these three are fatal at its gate and are checked here rather than remembered: two
    real MVP bounds, at least one scenario to prove the end against, and the two commands that start
    the application and run its suite. Everything smaller becomes an assumption instead of costing a
    whole run.

    What it does not check is which entries fall inside the bounds. Those are written in prose, in
    the project's own language, and mapping them to entry keys is judgement — which is exactly the
    one question the gate puts to the owner.
    """
    fatal = []
    product = next((d for d in docs if d.slot == "product"), None)
    text = product.text if product else ""
    section = section_of(text, "MVP bounds") or section_of(text, "Границы MVP")
    if section is None:
        found = re.search(r"^#{1,6}\s+.*\bMVP\b.*$", text, re.M | re.I)
        section = section_of(text, found.group(0).lstrip("# ").strip()) if found else None
    if not section:
        fatal.append("product.md has no MVP bounds section — an mvp with no bounds cannot know when "
                     "it is finished")
    else:
        sides = re.findall(r"^\*\*([^*]+):?\*\*[:：]?\s*(.*)$", section, re.M)
        filled = [name for name, rest in sides if len(rest.strip()) > 3]
        if len(filled) < 2:
            fatal.append("the MVP bounds are not two lists — an out-list is what stops a run from "
                         "helpfully building the rest of the product")

    scenarios = next((d for d in docs if d.slot == "scenarios"), None)
    body = re.sub(r"<!--.*?-->", "", scenarios.text, flags=re.S) if scenarios else ""
    if not HEADING_RE.findall(body):
        fatal.append("no scenarios are described — they are what an mvp proves itself against, and "
                     "without them its finish line is somebody's opinion")

    commands = manifest.get("commands") or {}
    for name, what in (("run", "start the application"), ("test", "run the suite")):
        if not (commands.get(name) or "").strip():
            fatal.append(f"project.yml has no `commands.{name}` — nothing says how to {what}, and "
                         f"the finish line is walked against a running application")

    for line in fatal:
        report.add("MVP", line)
    return fatal


def check_verdicts(manifest: dict, report: Report) -> None:
    verdicts = manifest.get("knowledge") or {}
    for slot in SLOTS:
        value = (verdicts.get(slot) or "").split()[0] if verdicts.get(slot) else ""
        if not value:
            report.add("Verdicts", f"{slot} — no verdict in project.yml")
        elif value == "open_question":
            report.add("Verdicts", f"{slot} — open question")


def collect_unmet(root: Path, manifest: dict, defined: set, report: Report) -> None:
    """Tests that prove a promise the product does not keep.

    They are green by design — the suite is told to expect them — so nothing else in a run will
    ever mention them again. This is the one place that does, which is why it prints on every
    command and not only when something is wrong.

    What is searched for is MARK, a constant of this kit written as a comment beside the test, and
    not whatever the suite uses to keep the test off the red. Frameworks differ, one project can
    have three suites in two languages, and a search for `->todo()` would find one of them at best.
    A constant is language-agnostic, so the search needs no list of test directories.

    The search is `git grep`, not a read of every tracked file: it skips binaries, does not follow
    symlinks into counting the same test twice, quotes nothing, and is an order of magnitude faster
    on a large repository. `docs/` is excluded because reports and entries quote the mark in prose,
    and a quotation is not a promise.
    """
    for path, number, line in grep(root, MARK):
        found = MARK_RE.search(line)
        if not found:
            continue
        key = found.group(1)
        if not key:
            report.unmet.append(f"{path}:{number} — no entry named beside the mark")
        elif defined and key not in defined:
            report.unmet.append(f"{path}:{number} {key} — no such entry")
        else:
            report.unmet.append(f"{path}:{number} {key}")

    form = (manifest.get("tests") or {}).get("unmet")
    if report.unmet and not form:
        report.unmet.append(f"project.yml has no tests.unmet — what keeps such a test green here")


def collect_debt(root: Path, report: Report) -> None:
    """Work a run decided not to do — the one thing no other record in the kit holds.

    Listed rather than counted, and without an exit code of its own: it is a statement about the
    project, like an unmet promise, and a run that stopped over it would be stopping over its own
    memory.
    """
    ledger = root / DEBT
    if not ledger.is_file():
        return
    fenced = False
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        item = line.strip()
        if item.startswith("```"):                 # the file explains its own format in a fence
            fenced = not fenced
        elif item.startswith("- [ ]") and not fenced:
            report.debt.append(f"{DEBT}:{number} {item[5:].strip()[:96]}")


def grep(root: Path, needle: str) -> list:
    """Every `path, line number, line` where the needle appears, outside `docs/`."""
    found = subprocess.run(
        # core.quotePath=false or a path with a non-ASCII character comes back escaped and unusable
        ["git", "-c", "core.quotePath=false", "grep", "-n", "-I", "--no-color", "-F",
         "-e", needle, "--", ":!docs"],
        cwd=root, capture_output=True, text=True)
    if found.returncode in (0, 1):                       # 1 is git grep for "no matches"
        hits = []
        for row in found.stdout.splitlines():
            path, _, rest = row.partition(":")
            number, _, line = rest.partition(":")
            if number.isdigit():
                hits.append((path, int(number), line))
        return hits

    skip = {".git", "docs", "node_modules", "vendor", "dist", "build", ".venv", "__pycache__"}
    hits = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        parts = set(path.relative_to(root).parts)
        if skip & parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if needle not in text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if needle in line:
                hits.append((str(path.relative_to(root)), number, line))
    return hits


def collect_notes(docs: list, report: Report) -> None:
    """Blocks a run left under an entry — and the two kinds are not equally urgent.

    `[assumed …]` and `[found …]` are questions the owner has not answered, so they are findings and
    they change the exit code. A `[stale …]` is not a question: the run wrote both what the entry
    still says and what is true now, and the block sits under the entry, so every later run reads
    the correction along with the prose it corrects. Nobody is misled while it is open. Reported as
    a statement, like a promise the product does not keep, or every command after a batch reports
    knowledge as broken and every `next` recommends the same command.
    """
    for doc in docs:
        for kind, tail, text in NOTE_RE.findall(doc.text):
            line = f"[{kind}{tail}] {doc.path.name}: {text.strip()[:90]}"
            (report.stale if kind == "stale" else report.notes).append(line)


def sync_states(docs: list, report: Report, sync: bool, offline: bool) -> None:
    """A merged pull request is the only thing that moves an entry to `built`.

    **Looking is free; writing is asked for.** Every run of this program compares an entry marked
    `building` against its pull request and says when the line is behind — so any command notices,
    including the batch being composed over that entry. Only `--sync` rewrites the line, because
    writing in a preflight leaves the tree dirty under a command that treats a dirty tree as a
    blocker, and because prose and its machine line have one owner between them.

    Without this split the two failure modes swapped places: it wrote silently until 0.41.0, and
    then went quiet altogether — a merged feature sat at `building` with nothing anywhere saying so.
    """
    if offline or not shutil.which("gh"):
        return
    for doc in docs:
        text = doc.text
        for entry in doc.entries:
            found = re.match(r"building \(pr:\s*(\d+)\)", entry.state or "")
            if not found:
                continue
            number = found.group(1)
            done = subprocess.run(["gh", "pr", "view", number, "--json", "state"],
                                  cwd=doc.path.parent, capture_output=True, text=True)
            if done.returncode != 0:
                report.add("States", f"{doc.path.name} {entry.key} — pull request {number} unreadable")
                continue
            state = (json.loads(done.stdout or "{}") or {}).get("state", "")
            if state == "MERGED":
                new = "built"
            elif state == "CLOSED":
                new = "planned"
            else:
                continue
            if not sync:
                report.states.append(
                    f"{entry.key}: pull request {number} has {state.lower()}, and the line still "
                    f"says building — /agent-kit:next moves it, or blueprint --check")
                continue
            text = text.replace(f"`key: {entry.key}` · `state: building (pr: {number})`",
                                f"`key: {entry.key}` · `state: {new}`")
            report.states.append(f"{entry.key}: building (pr: {number}) → {new}")
        if text != doc.text:
            doc.path.write_text(text, encoding="utf-8")
            doc.text = text
            # The entries were parsed from the text this just replaced, and `commented()` locates
            # one by finding its body in `doc.text` — so every check after this crashed on the day
            # a feature's pull request merged, which is the one day this branch ever runs.
            doc.entries = doc._entries()


def standing(docs: list) -> list:
    counts: dict = {}
    for doc in docs:
        for entry in doc.entries:
            if doc.commented(entry) or not entry.state:
                continue
            key = entry.state.split(" (")[0]
            counts[key] = counts.get(key, 0) + 1
    return [f"{state}: {count}" for state, count in sorted(counts.items())]


def planned(docs: list) -> list:
    """Entries described and not built — named, because a count is nothing to compose a batch from."""
    return [entry.key for doc in docs for entry in doc.entries
            if not doc.commented(entry) and (entry.state or "").split(" (")[0] == "planned"]


def record(root: Path, docs: list, manifest_path: Path) -> list:
    """Write every hash this program is able to compute, in place.

    Printing a value and letting a run copy it into a file leaves one hand in the loop, and a hand
    is what made every pre-4-August hash unverifiable. This closes that: `blueprint` calls one
    command instead of transcribing numbers.
    """
    written = []

    def rewrite(found: re.Match) -> str:
        # Substituting on the match keeps whatever spacing the line had; rebuilding the string from
        # the captured groups silently dropped the space before the `@`.
        path_text, heading, recorded = found.group(1), found.group(2), found.group(3)
        target = root / path_text.strip()
        if not target.is_file():
            return found.group(0)
        section = section_of(target.read_text(encoding="utf-8"), heading.strip())
        if section is None:
            return found.group(0)
        fresh = digest(section)
        if fresh == recorded:
            return found.group(0)
        written.append(f"{doc.path.name} → {path_text.strip()}#{heading.strip()} {recorded} → {fresh}")
        return found.group(0).replace(f"@{recorded}", f"@{fresh}")

    for doc in docs:
        text = SOURCE_RE.sub(rewrite, doc.text)
        if text != doc.text:
            doc.path.write_text(text, encoding="utf-8")
            doc.text = text

    if manifest_path.is_file():
        text = manifest_path.read_text(encoding="utf-8")
        for name in re.findall(r"^\s{4}([\w.\-]+):\s*([0-9a-f]*)\s*$", text, re.M):
            manifest_file, recorded = name
            target = root / manifest_file
            if not target.is_file():
                continue
            fresh = digest(target.read_text(encoding="utf-8"))
            if fresh == recorded:
                continue
            text = re.sub(rf"^(\s{{4}}{re.escape(manifest_file)}:\s*)[0-9a-f]*\s*$",
                          rf"\g<1>{fresh}", text, flags=re.M)
            written.append(f"project.yml → {manifest_file} {recorded or '(empty)'} → {fresh}")
        manifest_path.write_text(text, encoding="utf-8")

    return written


# --------------------------------------------------------------------------------------------
# the state of the work
#
# Where the checks above read what the project says about itself, this reads what has been happening
# to it: branches, pull requests, runs left mid-flight, when each lens last looked. Facts only —
# `/agent-kit:next` is what turns them into a recommendation.


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def default_branch(root: Path) -> str:
    """`origin/main` when there is one: the local copy of it is usually behind, and comparing a
    branch against a stale base reports work as unmerged long after it landed."""
    head = git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head:
        return head.split("refs/remotes/", 1)[-1]
    for name in ("origin/main", "origin/master", "main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", name):
            return name
    return ""


def work_branches(root: Path, base: str) -> list:
    """Branches a run would have made, and how far each has drifted from the base."""
    out = []
    listed = git(root, "for-each-ref", "--format=%(refname:short)\t%(upstream:short)", "refs/heads")
    for row in listed.splitlines():
        name, _, upstream = row.partition("\t")
        if not name.startswith(("claude/", "sprint/", "mvp/")):
            continue
        counts = git(root, "rev-list", "--left-right", "--count", f"{base}...{name}") if base else ""
        behind, _, ahead = counts.partition("\t")
        out.append({"branch": name, "pushed": bool(upstream),
                    "behind": int(behind or 0), "ahead": int(ahead or 0),
                    "last": git(root, "log", "-1", "--format=%cs", name)})
    return out


def run_template() -> dict:
    """The template that ships beside this program, so it and the checks cannot drift apart."""
    path = Path(__file__).resolve().parent.parent / "templates" / "run.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run_shape() -> set:
    """The fields a run file may carry."""
    return {k for k in run_template() if not k.startswith("_")}


def record_lists(shape: dict, prefix: str = "") -> dict:
    """Fields the template shows as a list of records, and the keys one record carries.

    A field whose shape the template draws as `[{...}]` is read by something as a record: `review.
    findings` by the closing check, `tasks` and `assumptions` by the reviewer and the pull request.
    Written as sentences instead, they still read like a filled-in field to a person and are opaque
    to every program — which is how a whole night of runs closed with the rule about open critical
    findings never once applied.
    """
    out: dict = {}
    for key, value in shape.items():
        if key.startswith("_"):
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            out[prefix + key] = set(value[0])
        elif isinstance(value, dict):
            out.update(record_lists(value, prefix + key + "."))
    return out


def stringly(run: dict, fields: dict) -> list:
    """Which of those fields this run filled with something other than records."""
    out = []
    for path in fields:
        value = run
        for step in path.split("."):
            value = value.get(step) if isinstance(value, dict) else None
        if isinstance(value, list) and any(not isinstance(item, dict) for item in value):
            out.append(path)
    return out


def check_runs(root: Path, report: Report) -> None:
    """Keys no reader knows about, and steps no reader expects.

    A run that needs somewhere to put something and invents a key has written to nobody: every
    reader — the resuming run, the closing session, this program — knows only the template. Free
    prose belongs in `notes`, and a field the whole kit needs is a finding about the kit. A step
    outside the vocabulary is the same failure in the one field everything watches.
    """
    template = run_template()
    known = {k for k in template if not k.startswith("_")}
    if not known:
        return
    records = record_lists(template)
    strays: dict = {}
    prose: dict = {}
    for path in sorted((root / ".agent-kit" / "runs").glob("*/run.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for field in stringly(run, records):
            prose.setdefault(field, 0)
            prose[field] += 1
        step = run.get("step")
        if step is not None and step not in STEPS:
            report.drift.append(f"{path.parent.name} is at step {step!r}, which no reader knows: "
                                f"a driver watches for a terminal step and would wait for ever")
        for key in run:
            if key not in known and not key.startswith("_"):
                strays.setdefault(key, 0)
                strays[key] += 1
    if strays:
        # Not a finding: a finished run's file is history, and nobody is going to edit it. It is
        # said so that the drift is visible while it is still happening, and so that a field the
        # kit keeps needing gets noticed — `deferred` was invented by three runs before it existed.
        named = ", ".join(f"{k} ({n})" for k, n in sorted(strays.items()))
        report.drift.append(f"run files carry fields the template does not: {named} — nothing reads "
                            f"them; prose goes in `notes`, and a field the kit needs is a finding")

    if prose:
        named = ", ".join(f"{k} ({n})" for k, n in sorted(prose.items()))
        report.drift.append(f"run files fill a field of records with sentences: {named} — the "
                            f"template draws each of these as `[{{…}}]`, and a program reading them "
                            f"gets nothing. `review.findings` is the one that costs: `severity` and "
                            f"`closed` are how a run is held to closing no critical finding open")


def run_defects(state: dict) -> list:
    """What a run may not close with.

    Two rules that held only as long as a run remembered them at the end of its longest step, and
    that a program can settle in a millisecond. They are asked at the moment of closing — by the run
    itself, and by the driver before it calls a feature built — and nowhere else: a finished run's
    file is history, and telling the next command about it reaches nobody who can act.

    Only `done` is judged. A run that stopped at `blocked` is already saying so.
    """
    if state.get("step") != "done":
        return []
    out = []

    review = state.get("review") or {}
    findings = (review.get("findings") or []) if isinstance(review, dict) else []
    if any(not isinstance(finding, dict) for finding in findings):
        # Reported instead of parsed out of the prose. A severity this program has to guess at is a
        # severity it cannot hold anyone to, and salvaging it would teach the next run that the
        # field's shape is a suggestion.
        out.append("a review finding is written as a sentence rather than as a record — `severity` "
                   "and `closed` are what says no critical one is open, and prose says nothing")
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "").strip().lower()
        if severity in ("critical", "major") and not finding.get("closed"):
            what = str(finding.get("what") or "").strip() or "unnamed"
            out.append(f"a {severity} review finding is open — {what[:70]}")

    suite = state.get("suite")
    if suite is None or (isinstance(suite, str) and not suite.strip()) or suite in ([], {}):
        out.append("`suite` is empty — nothing says what was run or what it returned, and the pull "
                   "request is written from that field rather than from memory")

    return out


def open_runs(root: Path) -> list:
    """Runs that never reached a terminal step — a feature somebody started and left."""
    out = []
    runs = root / ".agent-kit" / "runs"
    if not runs.is_dir():
        return out
    for path in sorted(runs.glob("*/run.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if run.get("step") in ("done", "blocked", "skipped"):
            continue
        out.append({"slug": run.get("slug") or path.parent.name,
                    "command": run.get("command", "?"), "step": run.get("step", "?"),
                    "branch": run.get("branch"), "waiting_on": run.get("waiting_on"),
                    "blockers": run.get("blockers") or []})
    return out


def scenarios(root: Path) -> tuple:
    """How many scenarios the knowledge describes, and how many a test says it walks.

    A scenario is proved by an end-to-end test carrying `agent-kit:scenario <its heading>`; without
    one it has only a trace through the code, which was true on the day somebody last looked.
    """
    path = root / KNOWLEDGE / "scenarios.md"
    if not path.is_file():
        return 0, [], []
    text = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)          # the template's example is commented
    described = [h.strip() for h in HEADING_RE.findall(body)]
    covered = set()
    for _path, _number, line in grep(root, SCENARIO_MARK):
        named = line.split(SCENARIO_MARK, 1)[1].strip(" :\"'*/#-\t")
        if named:
            covered.add(" ".join(named.split()).lower())
    known = {" ".join(h.split()).lower() for h in described}
    uncovered = [h for h in described if " ".join(h.split()).lower() not in known & covered]
    orphaned = sorted(c for c in covered if c not in known)
    return len(described), uncovered, orphaned


def audit_lenses(root: Path) -> list:
    """Each lens's work list: when it last ran, and how much of it is still unticked."""
    out = []
    audits = root / "docs" / "audits"
    if not audits.is_dir():
        return out
    for path in sorted(audits.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        found = re.search(r"(\d{4}-\d{2}-\d{2})", text[:400])
        out.append({"lens": path.stem, "date": found.group(1) if found else None,
                    "open": len(re.findall(r"^\s*- \[ \]", text, re.M))})
    return out


def pull_requests(root: Path, offline: bool) -> list:
    if offline or not shutil.which("gh"):
        return []
    done = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json",
         "number,title,headRefName,isDraft,mergeable,statusCheckRollup,updatedAt"],
        cwd=root, capture_output=True, text=True)
    if done.returncode != 0:
        return []
    try:
        rows = json.loads(done.stdout or "[]")
    except ValueError:
        return []
    out = []
    for row in rows:
        checks = row.get("statusCheckRollup") or []
        verdicts = {c.get("conclusion") or c.get("state") for c in checks if isinstance(c, dict)}
        if not checks:
            ci = "none"
        elif verdicts & {"FAILURE", "TIMED_OUT", "CANCELLED", "ERROR"}:
            ci = "failing"
        elif verdicts & {"PENDING", "IN_PROGRESS", "QUEUED", None}:
            ci = "pending"
        else:
            ci = "green"
        out.append({"number": row.get("number"), "branch": row.get("headRefName"),
                    "draft": row.get("isDraft"), "mergeable": row.get("mergeable"),
                    "ci": ci, "updated": (row.get("updatedAt") or "")[:10]})
    return out


def print_state(root: Path, offline: bool) -> None:
    """Runs and audits do not need git; everything about branches does, so it degrades in pieces."""
    base = default_branch(root)
    print("\nWork:")
    if base:
        dirty = git(root, "status", "--porcelain")
        print(f"  on {git(root, 'rev-parse', '--abbrev-ref', 'HEAD')}, "
              f"{'uncommitted changes present' if dirty else 'tree clean'}; "
              f"{base} last moved {git(root, 'log', '-1', '--format=%cs', base) or '?'}")
    elif (root / ".git").exists():
        print("  a repository with no commits yet — nothing to compare branches against")
    else:
        print("  no git repository here — branches and pull requests cannot be read")

    for run in open_runs(root):
        waiting = f", waiting on {run['waiting_on']}" if run.get("waiting_on") else ""
        blocked = f", blockers: {len(run['blockers'])}" if run["blockers"] else ""
        print(f"  run {run['slug']} left at step={run['step']} "
              f"({run['command']}, {run['branch'] or 'no branch'}{waiting}{blocked})")

    live = [b for b in work_branches(root, base) if b["ahead"]] if base else []
    for branch in live[:UNMET_SHOWN // 2]:
        pushed = "pushed" if branch["pushed"] else "**never pushed**"
        print(f"  branch {branch['branch']}: {branch['ahead']} ahead, {branch['behind']} behind "
              f"{base}, {pushed}, last commit {branch['last']}")
    if len(live) > UNMET_SHOWN // 2:
        print(f"  … and {len(live) - UNMET_SHOWN // 2} more unmerged branches")

    for pr in pull_requests(root, offline):
        print(f"  PR #{pr['number']} ({pr['branch']}): CI {pr['ci']}"
              f"{', draft' if pr['draft'] else ''}"
              f"{', conflicts' if pr['mergeable'] == 'CONFLICTING' else ''}, "
              f"updated {pr['updated']}")

    described, uncovered, orphaned = scenarios(root)
    if described:
        print(f"  scenarios: {described} described, {described - len(uncovered)} with an end-to-end "
              f"test" + (f" — uncovered: {', '.join(uncovered[:3])}" if uncovered else ""))
    for name in orphaned:
        print(f"  a test claims scenario \"{name}\" — no scenario by that heading exists")

    lenses = audit_lenses(root)
    if lenses:
        print("  audits: " + ", ".join(
            f"{l['lens']} {l['date'] or 'undated'}" + (f" ({l['open']} open)" if l["open"] else "")
            for l in lenses))
    else:
        print("  audits: none has ever run")


# --------------------------------------------------------------------------------------------


def print_planned(docs: list) -> None:
    waiting = planned(docs)
    if not waiting:
        return
    shown = ", ".join(waiting[:UNMET_SHOWN])
    rest = f", … and {len(waiting) - UNMET_SHOWN} more" if len(waiting) > UNMET_SHOWN else ""
    print(f"Planned: {shown}{rest}")


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--status", action="store_true", help="always print where the project stands")
    parser.add_argument("--offline", action="store_true",
                        help="ask gh about nothing — the state of the work is then read from git alone")
    parser.add_argument("--sync", action="store_true",
                        help="move an entry whose pull request has merged or closed. The only thing "
                             "this program writes into knowledge; `blueprint --check` asks for it")
    parser.add_argument("--record", action="store_true",
                        help="rewrite every source and dependency hash in place, so no run has to "
                             "copy one by hand")
    parser.add_argument("--state", action="store_true",
                        help="also print the state of the work: branches, pull requests, runs left "
                             "mid-flight, when each lens last ran")
    parser.add_argument("--hash", nargs="+", metavar="ARG",
                        help="print the digest of a file, or of one heading inside it: --hash FILE [HEADING]")
    parser.add_argument("--mvp", action="store_true",
                        help="the gate of /agent-kit:mvp: bounds, scenarios, and the commands that "
                             "start and test the application. Silent when it may start")
    parser.add_argument("--run", metavar="DIR",
                        help="judge one run file as it closes: what a run at step done may not "
                             "leave behind. Silent when there is nothing")
    options = parser.parse_args(argv)

    root = options.root.resolve()

    if options.run:
        target = Path(options.run)
        path = target if target.suffix == ".json" else target / "run.json"
        if not path.is_file():
            print(f"no run file: {path}", file=sys.stderr)
            return 2
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{path} cannot be read: {exc}", file=sys.stderr)
            return 2
        defects = run_defects(state if isinstance(state, dict) else {})
        if defects:
            print(f"This run cannot close as it stands ({len(defects)}):")
            for line in defects:
                print(f"  {line}")
        return 1 if defects else 0

    if options.hash:
        target = root / options.hash[0] if not Path(options.hash[0]).is_absolute() else Path(options.hash[0])
        if not target.is_file():
            print(f"no such file: {target}", file=sys.stderr)
            return 2
        text = target.read_text(encoding="utf-8")
        if len(options.hash) > 1:
            section = section_of(text, " ".join(options.hash[1:]))
            if section is None:
                print(f"no such heading: {' '.join(options.hash[1:])}", file=sys.stderr)
                return 2
            text = section
        print(digest(text))
        return 0

    knowledge = root / KNOWLEDGE
    if not knowledge.is_dir():
        if options.status or options.state:
            print(f"no {KNOWLEDGE}/ — this project has no blueprint yet")
        if options.state:
            print_state(root, options.offline)
        return 0

    docs = [Doc(p) for p in sorted(knowledge.glob("*.md"))]
    manifest = read_manifest(root / MANIFEST)
    report = Report()

    if options.record:
        written = record(root, docs, root / MANIFEST)
        print("\n".join(f"  {line}" for line in written) if written
              else "  every hash was already current")
        return 0

    if options.mvp:
        fatal = check_mvp(root, manifest, docs, report)
        if fatal:
            print("This project cannot start an mvp as it stands:")
            for line in fatal:
                print(f"  {line}")
        return 1 if fatal else 0

    sync_states(docs, report, options.sync, options.offline)
    check_fields(docs, report)
    check_references(docs, report)
    check_orphans(docs, report)
    check_sources(root, docs, report)
    check_stack(root, manifest, report)
    check_verdicts(manifest, report)
    check_runs(root, report)
    collect_unmet(root, manifest, keys(docs), report)
    collect_debt(root, report)
    collect_notes(docs, report)

    if report.states:
        print("Entries against their pull requests:")
        for line in report.states:
            print(f"  {line}")

    if report.unmet:
        print(f"\nPromises the product does not keep ({len(report.unmet)}) — the entry, and the "
              "test already written for it, waiting for the product to change or the entry to:")
        # Not cut: `ship` is told to read the marked test for the entry it is about to touch, and a
        # list trimmed to ten can drop exactly that one. The debt below is cut instead — nothing
        # reads it per-entry.
        for line in report.unmet:
            print(f"  {line}")
        print("  Not this run's work. They are offered as a batch by /agent-kit:sprint with no theme.")

    if report.stale:
        print(f"\nProse a feature has already outdated ({len(report.stale)}) — the entry carries "
              "the correction under it, so nothing is misled while it stands:")
        for line in report.stale:
            print(f"  {line}")
        print("  Applied by whoever next builds in that entry, with the owner present, or by "
              "/agent-kit:blueprint. Not a reason to run either.")

    for line in report.drift:
        print(f"\n  {line}")

    if report.debt:
        print(f"\nDebt ({len(report.debt)}) — work earlier runs decided not to do:")
        for line in report.debt[:UNMET_SHOWN]:
            print(f"  {line}")
        if len(report.debt) > UNMET_SHOWN:
            print(f"  … and {len(report.debt) - UNMET_SHOWN} more")

    if report.clean and not report.notes:      # `stale` is a statement, not a finding
        if options.status:
            print("Knowledge is clean. " + ", ".join(standing(docs)))
            print_planned(docs)
        if options.state:
            print_state(root, options.offline)
        return 0

    if options.status:
        print("Standing: " + ", ".join(standing(docs)))
        print_planned(docs)
    for group, lines in report.groups.items():
        print(f"\n{group}:")
        for line in lines:
            print(f"  {line}")

    sources = report.groups.get("Sources") or []
    if len(sources) > 2 and all("changed" in line for line in sources):
        print("\n  Every source looks changed — most likely they were recorded before this program "
              "owned the hash. Re-record them with blueprint rather than reading each document.")
    if report.notes:
        print(f"\nOpen notes ({len(report.notes)}) — each is a decision waiting for the owner:")
        for note in report.notes:
            print(f"  {note}")

    if options.state:
        print_state(root, options.offline)

    print("\nNot checked here: whether an answer is any good, whether a status an action sets is "
          "one the entity declares, and anything that needs the code read.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
