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
AUDITS = "docs/audits"
MANIFEST = ".agent-kit/project.yml"
DEBT = "docs/technical_debt.md"
MARK = "agent-kit:unmet"
SCENARIO_MARK = "agent-kit:scenario"
DIGEST_LEN = 8
UNMET_SHOWN = 10
HANDOFF_MAX = 2000
# A child's prompt is a command and a run directory. The longest legitimate one this kit writes is
# about a hundred characters; the ceiling is generous on purpose, because what it exists to catch
# came in at two to five thousand.
PROMPT_MAX = 400
# What a pull request may put in front of a reader who has not decided to read it yet. Budgets, not
# measurements — see `pr_body_defects`. Chosen against one run's 45 000-character body, whose
# seventy-row table of assumptions was the part that made the rest unusable.
PR_OPEN_MAX = 12000
PR_TABLE_MAX = 15

KEY_RE = re.compile(r"^`key:\s*([^`·]+?)\s*`(?:\s*·\s*`state:\s*([^`]+?)\s*`)?", re.M)
HEADING_RE = re.compile(r"^###\s+(.+)$", re.M)
FIELDS_RE = re.compile(r"^fields:\s*(.+)$", re.M)
SOURCE_RE = re.compile(r"`source:\s*([^#`]+)#([^@`]+?)\s*@([0-9a-f]+)`")
NOTE_RE = re.compile(r"^>\s*\*\*\[(assumed|found|stale|accepted|frame)\b([^\]]*)\]\*\*\s*(.*)$", re.M)
REF_RE = re.compile(r"`([a-z][a-z0-9_]*\.[a-z0-9_]+)`")
# A path into an installed plugin, with the version in it. What a session expanded for itself is
# what the child then reads, three weeks out of date and silently.
PINNED_PLUGIN = re.compile(r"[^\s\"']*plugins/[^\s\"']*?/\d+\.\d+\.\d+/[^\s\"',)]*")
# entities and actors are keys without a dot, so the entry part is one or more segments
MARK_RE = re.compile(re.escape(MARK) + r"[:\s]*([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*)?")
# A screen the product opens on is reached from nowhere by design; the entry says so in its own
# words, in the project's language, so this looks for the marker rather than for a sentence.
ENTRY_POINT_RE = re.compile(r"`entry_point`", re.I)
# The product's parts, and whether the owner ever walked one. Same reasoning as the marker above:
# the names are in the project's language and the mark is not, so this counts marks rather than
# reading a heading that may say anything.
WALKED_RE = re.compile(r"^\s*[-*]\s+.*\bwalked:\s*(\d{4}-\d{2}-\d{2})", re.M)
DERIVED_RE = re.compile(r"^\s*[-*]\s+.*\bderived\b", re.M | re.I)
# What a lens says it walked, and how that broke down. Same reasoning again: the counts are in
# English and countable, the report around them is in the project's language.
TALLY_RE = re.compile(r"<!--\s*agent-kit:audit\s+([^>]*?)-->")
TALLY_PAIR_RE = re.compile(r"([a-z_]+)=(\d+)")
# A ticked item that records a refusal rather than closed work. Backticked, so the English word
# appearing in a sentence is not mistaken for the mark.
DECLINED_RE = re.compile(r"`declined`")
LENSES = ("tests", "deps", "scenarios", "security", "performance", "conventions")
# What else may sit in `docs/audits/` and is not a lens. The baseline is two comparisons that belong
# to no lens and run once per invocation, so it has no scope to walk and no counters to add up.
# Declared here rather than skipped by shape, because a file this program cannot place is either
# this one or a lens nobody wired in, and going quiet on both makes them one thing.
NON_LENSES = ("baseline",)
STATE_LINE_RE = re.compile(r"(`key:\s*%s\s*`\s*·\s*`state:\s*)building \(pr:\s*(\d+)\)(\s*`)")

SLOTS = ("product", "actors", "entities", "actions", "screens", "integrations", "scenarios", "stack")

# What `step` may hold. The first eight are a run's own; `building` and `closing` are written by the
# driver on a batch's file. Kept here rather than only in the template's prose, because a value
# nothing recognises leaves whatever is watching that field waiting for a state that never comes.
STEPS = ("queued", "design", "build", "verify", "deliver", "done", "blocked", "skipped",
         "building", "closing",
         # an epic's own phases, written by `epic` on its own file as it moves between them
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
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # The driver calls this after every child, all night, with no `try` above it. A manifest
        # saved in the wrong encoding would have taken the whole batch down between two features.
        return data
    for raw in text.splitlines():
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
        self.assumed: list = []
        self.stale: list = []
        self.accepted: list = []
        self.frame: list = []
        self.states: list = []
        self.unmet: list = []
        self.debt: list = []
        self.drift: list = []
        self.shape: list = []
        self.audits: list = []

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


def check_epic(root: Path, manifest: dict, docs: list, report: Report) -> list:
    """What `epic` cannot start without, and nothing more.

    An `epic` with a thin blueprint has no stopping condition — a sprint with one still delivers five
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
        fatal.append("product.md has no MVP bounds section — an epic with no bounds cannot know when "
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
        fatal.append("no scenarios are described — they are what an epic proves itself against, and "
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
    """Blocks a run left under an entry — and the four kinds are not equally urgent.

    `[assumed …]` and `[found …]` are questions the owner has not answered, so they are findings and
    they change the exit code. A `[stale …]` is not a question: the run wrote both what the entry
    still says and what is true now, and the block sits under the entry, so every later run reads
    the correction along with the prose it corrects. Nobody is misled while it is open. Reported as
    a statement, like a promise the product does not keep, or every command after a batch reports
    knowledge as broken and every `next` recommends the same command.

    An `[accepted …]` is not a question either, and for the opposite reason: it is already answered.
    The owner accepted a proposal in front of `advise` and left the record's fields for later, so
    what is outstanding is an interview, not a decision. Nothing downstream is misled — there is no
    entry yet to be wrong about — so it is a statement too, and only `blueprint` turns it into one.

    A `[frame …]` under `stack.md` is a statement for a third reason: it is working, and it is
    working *now*. It holds what a batch's features agreed to build alike, it is read by every
    `ship` that opens the map, and every batch leaves one. A finding raised on each of them would
    have every command after every sprint report the knowledge as broken.
    """
    for doc in docs:
        # Which entry a block sits under is what a command needs: it only settles the ones on the
        # entries it is about to build. Blocks outside any entry — `[found …]` under the library
        # map — are named by their file, which is the whole address they have.
        under = {}
        for entry in doc.entries:
            for found in NOTE_RE.finditer(entry.body):
                under[found.group(0)] = entry.key
        for found in NOTE_RE.finditer(doc.text):
            kind, tail, text = found.groups()
            where = under.get(found.group(0), doc.path.name)
            line = f"[{kind}{tail}] {where}: {text.strip()[:90]}"
            bucket = {"stale": report.stale, "accepted": report.accepted, "frame": report.frame,
                      "assumed": report.assumed}.get(kind, report.notes)
            bucket.append((where, line, quoted_block(doc.text, found.start())))


def quoted_block(text: str, start: int) -> str:
    """A block runs until the quoting stops, and the summary line above keeps only its first 90
    characters — enough to tell two blocks apart in a list, useless to answer one. What a decision
    was, and what was taken instead, is usually three lines further down."""
    kept = []
    for raw in text[start:].splitlines():
        if not raw.lstrip().startswith(">"):
            break
        kept.append(raw.lstrip()[1:].strip())
    return "\n".join(kept).strip()


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


def parts(docs: list) -> tuple:
    """How many parts the product is described in, and how many of them the owner never walked.

    The interview is shaped by the product's own parts, and each is recorded in `product.md` as
    either walked on a date or derived from the code and never confirmed. Two commands read that:
    a plain `blueprint` offers the walk, and an `epic`'s gate says how much of the description
    nobody has ever seen. Both were told to read it and neither had anything to read it with.

    Counted, never named: what a part is called is the owner's language, the mark is not. The
    template's own examples are inside an HTML comment and are dropped first, or a file copied and
    not yet filled in would report three parts nobody has.
    """
    product = next((d for d in docs if d.slot == "product"), None)
    if product is None:
        return 0, 0
    body = re.sub(r"<!--.*?-->", "", product.text, flags=re.S)
    return len(WALKED_RE.findall(body)), len(DERIVED_RE.findall(body))


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
        if not name.startswith(("claude/", "sprint/", "epic/")):
            continue
        counts = git(root, "rev-list", "--left-right", "--count", f"{base}...{name}") if base else ""
        behind, _, ahead = counts.partition("\t")
        out.append({"branch": name, "pushed": bool(upstream),
                    "behind": int(behind or 0), "ahead": int(ahead or 0),
                    "last": git(root, "log", "-1", "--format=%cs", name)})
    return out


def merged_prs(root: Path, numbers: set, offline: bool) -> set:
    """Which of these pull request numbers have merged. Empty when nothing can be asked."""
    if offline or not numbers or not shutil.which("gh"):
        return set()
    out = set()
    for number in sorted(numbers):
        done = subprocess.run(["gh", "pr", "view", str(number), "--json", "state"],
                              cwd=root, capture_output=True, text=True)
        if done.returncode != 0:
            continue
        try:
            if (json.loads(done.stdout or "{}") or {}).get("state") == "MERGED":
                out.add(int(number))
        except ValueError:
            continue
    return out


def delivered_branches(root: Path, base: str, offline: bool) -> tuple:
    """Branches whose work is in the default branch, and the ones nothing here can judge.

    **Two tests, because either one alone leaves half the branches undecided.** Ancestry answers it
    when the pull request was merged with a merge commit. It cannot answer at all when the pull
    request was squashed: the branch's commits are then nowhere in the base and never will be, so
    `--merged` says no for ever. Measured on one project — 99 branches after two runs, 47 answered
    by ancestry and 51 unanswerable, because the run's one pull request was squashed.

    What answers those is the record. `docs/runs/<batch>.json` carries the batch's pull request and,
    since 2.13.0, the branches of its children — so a merged number retires them by name, on any
    machine, under any merge strategy, long after `.agent-kit/runs/` is gone.

    A branch that neither test reaches is returned separately and named rather than assumed either
    way. Deleting on a guess costs work nobody can get back; leaving one is a line in a listing.
    """
    names = [row["branch"] for row in work_branches(root, base)]
    remote = git(root, "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    for row in remote.splitlines():
        name = row.partition("/")[2]
        if name.startswith(("claude/", "sprint/", "epic/")) and name not in names:
            names.append(name)
    if not names:
        return [], []

    owned = {}                                    # branch -> the pull request that carried it
    for path in sorted((root / "docs" / "runs").glob("*.json")):
        try:
            written = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # A file that parses into a list or a string is JSON and is not a record. Skipped here and
        # named by `check_batches`, which is the one that may speak: this runs inside `--state`,
        # where an exception would take down the whole reading of the work over one bad file.
        if not isinstance(written, dict):
            continue
        number = written.get("pr")
        if not isinstance(number, int):
            continue
        for branch in written.get("branches") or []:
            owned[branch] = number
    merged = merged_prs(root, set(owned.values()), offline)

    def inside(name: str) -> bool:
        return bool(base) and subprocess.run(
            ["git", "merge-base", "--is-ancestor", name, base],
            cwd=root, capture_output=True).returncode == 0

    delivered, unknown = [], []
    for name in sorted(names):
        if owned.get(name) in merged:
            delivered.append((name, f"pull request {owned[name]} merged"))
        elif inside(name):
            delivered.append((name, f"in {base}"))
        elif name in owned:
            unknown.append((name, f"pull request {owned[name]} is not merged"))
        else:
            unknown.append((name, "no run record names it"))
    return delivered, unknown


def brief(root: Path, docs: list, key: str) -> int:
    """Everything a feature needs before it designs, printed in one call.

    `ship` reads four or five things at the start of every run: the project's corner, the entry, the
    entities the entry names, the library map. Read one at a time that is four or five turns, and a
    turn costs the whole context again — measured on a live run, not one assistant turn in 6443 ever
    carried two tool calls, though both the harness and the command ask for it. An instruction that
    is followed nought times out of 6443 is not an instruction, so this is a command instead.

    Prints what it could not find rather than leaving it out: a brief that silently drops the entity
    an entry depends on reads exactly like one where the entry depends on nothing.
    """
    entries = {entry.key: (doc, entry) for doc in docs for entry in doc.entries
               if not doc.commented(entry)}
    if key not in entries:
        near = sorted(k for k in entries if key.split(".")[-1] in k)
        print(f"no entry with key {key!r} in {KNOWLEDGE}/", file=sys.stderr)
        if near:
            print("did you mean: " + ", ".join(near[:5]), file=sys.stderr)
        return 2

    doc, entry = entries[key]
    sections = [(f"{MANIFEST}", (root / MANIFEST).read_text(encoding="utf-8")
                 if (root / MANIFEST).is_file() else None),
                (f"{doc.path.name} — {entry.heading}", entry.body.strip())]

    # The actor is in the key itself — `developer.create_offer` is the developer's — and the rest is
    # whatever the entry names in backticks and the knowledge defines: the entities it stores in,
    # the screens it is reached from, the actions it hands to. Its own key is not one of them.
    named = [key.split(".")[0]] if "." in key else []
    named += re.findall(r"`([a-z][a-z0-9_.]*)`", entry.body)
    candidates = [k for k in dict.fromkeys(named) if k != key]
    named = [k for k in candidates if k in entries]

    # What the entry names and the knowledge does not define. Held to the same rule as
    # `check_references`, and for the same reason: a backticked `a.b` is a key only when `a` is a
    # declared actor or it is a screen. Everything else with a dot is prose — a column, a config
    # path, a filename — and a dotless one is as likely to be a status or a field as an entity.
    # Measured on a real project: this rule names nothing false across 52 entries, and guessing
    # more widely named twenty-two innocents in one entry.
    actors = {k for k in entries if "." not in k}
    missing = [k for k in candidates if k not in entries
               and (k.split(".", 1)[0] in actors or k.startswith("screen."))]
    for other in named:
        other_doc, other_entry = entries[other]
        sections.append((f"{other_doc.path.name} — {other_entry.heading}",
                         other_entry.body.strip()))

    stack = root / KNOWLEDGE / "stack.md"
    sections.append(("stack.md", stack.read_text(encoding="utf-8") if stack.is_file() else None))

    absent = []
    for title, body in sections:
        print(f"\n{'=' * 78}\n== {title}\n{'=' * 78}")
        if body is None:
            absent.append(title)
            print(f"[not in this project — {title} does not exist]")
        else:
            print(body)

    # The boundary of this brief, said out loud. Without it a brief that quietly dropped the entry
    # its entry depends on reads exactly like one where the entry depends on nothing, and the run
    # designs the missing half itself.
    print(f"\n{'=' * 78}")
    print(f"== pulled in: {', '.join(named) if named else 'nothing — this entry names no other'}")
    print("== a name in backticks that is neither an actor's key nor a screen is not looked up: "
          "a status, a column and a config path all look the same here")
    if missing:
        print(f"== named by this entry and defined nowhere in {KNOWLEDGE}/: {', '.join(missing)}")
    print('=' * 78)
    if absent:
        print(f"\nnot found, and read nowhere else: {', '.join(absent)}", file=sys.stderr)
    return 0


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


def batch_template() -> dict:
    """The batch record's shape, from the template that ships beside this program."""
    path = Path(__file__).resolve().parent.parent / "templates" / "batch.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def number(value) -> bool:
    """A count, and not `true` wearing one — `isinstance(True, int)` is the trap here."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def batch_defects(state: dict) -> list:
    """What a batch's durable record may not be written as.

    `docs/runs/<slug>.json` is the only part of a batch that outlives the machine, and until now the
    only thing asked of it was that it exist. Its shape lived as an example inside `sprint`'s closing
    prose, which meant every closing session re-derived it — and on the one project that has run
    batches for real, eleven of them left one hand-written file in a shape nothing reads.

    Two of its fields are read by a program and are the reason this is not a matter of taste:
    `spent` is what the next epic's gate prices a scope from, and `branches` is what `next` clears
    delivered branches from. A count written as a sentence — *about six hours*, *all of them* —
    reads as a filled-in field to a person and is nothing to either. The rest are counts a person
    reads, and they are judged the same way for one reason: a field that may be prose is a field
    that will be.

    Judged as the batch closes, by the session that is still there to fix it, and reported as drift
    project-wide afterwards, because a merged batch's record is history and nobody will edit it.
    """
    out = []
    # `branches` is the one that may legitimately be empty — a batch every child of which was
    # parked has none — so it is required to be *present*, and `[]` is an answer. The rest are
    # missing when they are empty, because none of them has a meaning at zero.
    readers = {"slug": "nothing names which batch this is",
               "command": "nothing says what wrote it",
               "pr": "nothing ties it to the pull request that delivered it",
               "branches": "`/agent-kit:next` clears delivered branches from this field; a batch "
                           "that left none writes `[]`, and leaving it out says nobody looked",
               "spent": "the gate of the next epic prices a scope from it"}
    for field, reader in readers.items():
        empty = state.get(field) is None if field == "branches" \
            else state.get(field) in (None, "", [], {})
        if empty:
            out.append(f"the batch record has no `{field}` — {reader}")

    # Whole, not merely numeric: `delivered_branches` matches this against what `gh` returns for a
    # pull request, and 21.0 is not 21 to that reader. A record that passed here and was skipped
    # there would leave exactly the branches this field exists to retire.
    if state.get("pr") is not None and not (isinstance(state.get("pr"), int)
                                            and not isinstance(state.get("pr"), bool)):
        out.append("`pr` in the batch record is not a whole number — the branches of this batch are "
                   "retired by asking gh about that number, and it is matched as it is written")

    spent = state.get("spent")
    if spent is not None:
        if not isinstance(spent, dict):
            out.append("`spent` in the batch record is written as prose rather than as hours, "
                       "features and sessions — a gate that prices a scope out of prose was "
                       "measured four times under, with nothing to correct it")
        else:
            wrong = [k for k in ("hours", "features", "sessions") if not number(spent.get(k))]
            if wrong:
                out.append(f"`spent` in the batch record does not carry {', '.join(wrong)} as "
                           f"numbers — that is what the next gate prices its scope from")

    # The three lists, and then every count. A field left out is not judged — a batch that had no
    # blocked child may say so by writing `[]` or by saying nothing — but a field that is there is
    # held to its shape, all of them and not the two with a program behind them: a field that may
    # be prose is a field that will be, and the next reader of this file is a year away.
    for field in ("branches", "entries", "blocked"):
        value = state.get(field)
        if value is not None and (not isinstance(value, list)
                                  or any(not isinstance(item, str) for item in value)):
            named = {"branches": "`/agent-kit:next` reads this to know which branches a merged pull "
                                 "request already delivered, and a branch nobody can account for is "
                                 "one nobody ever removes",
                     "entries": "these are entry keys, and a key is what every other reader of the "
                                "knowledge matches on",
                     "blocked": "these are the slugs of the children that did not finish"}[field]
            out.append(f"`{field}` in the batch record is not a list of names — {named}")

    for field in ("children", "assumptions", "unmet"):
        if state.get(field) is not None and not number(state.get(field)):
            out.append(f"`{field}` in the batch record is not a number — a count written as a "
                       f"sentence reads as answered to a person and says nothing to anyone reading "
                       f"this a year from now")

    for field in ("debt", "review", "per_feature"):
        value = state.get(field)
        if value is None:
            continue
        if not isinstance(value, dict):
            out.append(f"`{field}` in the batch record is written as prose rather than as counts — "
                       f"the template draws it as a record of numbers")
        else:
            loose = sorted(k for k, v in value.items() if not number(v))
            if loose:
                out.append(f"`{field}` in the batch record does not carry {', '.join(loose)} as "
                           f"numbers — every value under it is a count")
    return out


def check_batches(root: Path, report: Report) -> None:
    """Batch records this project already has: what cannot be read, and keys nothing knows.

    A statement rather than a finding, for the same reason a finished run's file is one — it is
    history, and telling a command about it reaches nobody who can act. What it does buy is that
    drift is visible while it is still happening.
    """
    runs = root / "docs" / "runs"
    if not runs.is_dir():
        return
    known = {k for k in batch_template() if not k.startswith("_")}
    if not known:
        return
    unreadable, strays = [], {}
    for path in sorted(runs.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreadable.append(path.name)
            continue
        if not isinstance(record, dict):
            unreadable.append(path.name)
            continue
        for key in record:
            if key not in known and not key.startswith("_"):
                strays[key] = strays.get(key, 0) + 1
    if unreadable:
        report.drift.append(f"batch records that cannot be read as a record ({len(unreadable)}): "
                            f"{', '.join(unreadable)} — the shape is in "
                            f"`templates/batch.json`, and a file nothing can parse is a batch that "
                            f"left nothing, which must not read like a batch that left a record")
    if strays:
        named = ", ".join(f"{k} ({n})" for k, n in sorted(strays.items()))
        report.drift.append(f"batch records carry fields the template does not: {named} — nothing "
                            f"reads them, and a field the kit keeps needing is a finding about the "
                            f"kit rather than a key invented per batch")


def check_shape(root: Path, docs: list, manifest: dict, report: Report) -> None:
    """What this project's knowledge is missing against the kit that ships today.

    Every other check asks whether the knowledge agrees with itself and with the code. This one asks
    a question nobody could answer without remembering release notes: **was this written by an older
    kit?** A project carried across a year of versions has files whose shape stopped matching what
    the commands now expect — a field the templates gained, a section that did not exist — and
    nothing anywhere says so, because each file declares its own `fields:` line and is checked
    against that.

    Structure, never text: the templates are in English and a project's files are in its own
    language, so what compares is how many fields a record declares and how many sections a file
    has, and in what order. That survives translation and catches exactly what a version gained.

    A statement, not a finding. An older project is not broken — it is behind, and only `blueprint`
    can move it, with the owner there.
    """
    templates = Path(__file__).resolve().parent.parent / "templates"
    for doc in docs:
        model = templates / "knowledge" / doc.path.name
        if not model.is_file():
            # Three checks key off the template: fields, shape, and the verdict this slot needs in
            # the manifest. A file the kit ships no template for slips all three at once, and the
            # silence reads as a clean file. The product template itself invites one — endpoints
            # for an API, commands for a CLI — so this is a road the kit points at and does not pave.
            report.drift.append(f"{doc.path.name} has no template in this kit — its fields, its "
                                f"shape and its verdict are all unchecked, and a check that cannot "
                                f"read a file has to say so rather than pass it")
            continue
        text = model.read_text(encoding="utf-8")
        found = FIELDS_RE.search(text)
        wanted = [f.strip() for f in found.group(1).split(",")] if found else []
        if wanted and len(doc.fields) < len(wanted):
            # Which of them is missing is not said: the names here are in the project's language and
            # the template's are in English, so pairing them is a guess — and a guessed value holds
            # nobody to anything. The two lists are printed instead, and blueprint pairs them with
            # the owner in the room.
            report.shape.append(f"{doc.path.name} declares {len(doc.fields)} fields per record, the "
                                f"kit's template {len(wanted)}. Template: {', '.join(wanted)}. "
                                f"Here: {', '.join(doc.fields)}")
        theirs = re.findall(r"^##\s+(.+)$", doc.text, re.M)
        ours = re.findall(r"^##\s+(.+)$", text, re.M)
        if ours and len(theirs) < len(ours):
            report.shape.append(f"{doc.path.name} has {len(theirs)} sections, the kit's template "
                                f"{len(ours)}. Template: {', '.join(ours)}")

    model = read_manifest(templates / "project.yml")
    for key, value in model.items():
        if key not in manifest:
            report.shape.append(f"{MANIFEST} has no `{key}` — the template does, so nothing here "
                                f"answers what it records")
        elif isinstance(value, dict) and isinstance(manifest.get(key), dict):
            gone = [k for k in value if k not in manifest[key]]
            if gone:
                report.shape.append(f"{MANIFEST} → `{key}` is missing {', '.join(gone)}")


def check_channels(root: Path, report: Report) -> None:
    """The two ways a channel of this kit goes wrong that a program can see.

    Every record here has a writer, a reader and somebody allowed to close it — the table is in
    `rules/channels.md`, and only what this can check is in it, so the table cannot quietly drift
    from what is true. These two were both paid for:

    - a live run needed to start a command the driver could not, so it wrote itself a shell script
      into a run directory and told a session to execute it. A mechanism with no writer named, no
      reader named and nothing tracking it, in the one directory nothing tracks;
    - an audit's box is ticked by the batch that closed the work, by `next` and by `accept` when
      either verified one, and all three are required to name the pull request. A tick with no number is a claim nobody can
      check, on the list `sprint` composes its next batch from.
    """
    runs = root / ".agent-kit" / "runs"
    strays = []
    if runs.is_dir():
        for directory in sorted(p for p in runs.iterdir() if p.is_dir()):
            for path in sorted(directory.iterdir()):
                if path.name not in ("run.json", "run.log", "control"):
                    strays.append(f"{directory.name}/{path.name}")
    if strays:
        named = ", ".join(strays[:5]) + (f" … and {len(strays) - 5} more" if len(strays) > 5 else "")
        report.drift.append(f"run directories carry files that are not a run's own ({len(strays)}): "
                            f"{named} — a run keeps run.json, run.log and control, and anything else "
                            f"there is a mechanism nothing declared and nothing tracks")

    # A ticked item leaves every future list: `sprint` reads the unticked half and nothing else,
    # `next` never raises it again. So the number is not there to protect the next batch — it is
    # the only way anyone can later check that the work behind a tick was really done. A tick on a
    # guess is work lost silently, which is why the tick is signed.
    #
    # `declined` is not a tick of that kind: it is the lens recording that an item was refused, and
    # no pull request will ever close it. The word stays English wherever the file is written, like
    # every other mark of this kit.
    audits = root / AUDITS
    blind: dict = {}
    if audits.is_dir():
        for path in sorted(audits.glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not re.match(r"\s*[-*]\s*\[[xX]\]", line):
                    continue
                if re.search(r"#\d+", line) or DECLINED_RE.search(line):
                    continue
                blind[path.name] = blind.get(path.name, 0) + 1
    if blind:
        where = ", ".join(f"{name} ({count})" for name, count in sorted(blind.items()))
        report.drift.append(f"audit items are ticked without naming the pull request that closed "
                            f"them ({sum(blind.values())}): {where} — a tick takes an item off every "
                            f"list there is, and the number is what lets anyone check it was really "
                            f"done. Items ticked before this rule existed are in this count")


def check_audits(root: Path, docs: list, report: Report) -> None:
    """What each lens says it walked, and whether that adds up.

    Every lens defends against the same failure in prose — *a lens that quietly narrows its own
    scope produces a clean report about five actions and says nothing about the thirty it never
    looked at, and nobody can tell which happened* — and three of them go further and call the
    completeness *countable*. Counting it was then left to the same agent that wrote the report.

    So the lens writes one line of counters and this adds them up. What the buckets are called is
    the lens's own business — `covered`/`gaps` for tests, `walks`/`breaks` for scenarios — and this
    knows none of them: it checks that they sum to `walked`, which is arithmetic and survives
    translation.

    The number of entries is printed beside it rather than compared against. The right total
    differs by lens — the tests lens has nothing to walk in an actor, the security lens walks its
    *must never* lines — and a program that picked one of those would have called the one real
    audit in existence wrong.
    """
    audits = root / AUDITS
    if not audits.is_dir():
        return
    entries = len([e for doc in docs for e in doc.entries if not doc.commented(e)])
    uncounted, unplaced = [], []
    for path in sorted(audits.glob("*.md")):
        if path.stem in NON_LENSES:
            continue
        if path.stem not in LENSES:
            # Skipped in silence until now, which made a lens nobody wired in read exactly like the
            # baseline: no counters added up, and nothing said so. A report whose scope is added up
            # by nobody is the failure every lens is written to prevent.
            unplaced.append(path.name)
            continue
        found = TALLY_RE.search(path.read_text(encoding="utf-8"))
        if not found:
            uncounted.append(path.stem)
            continue
        counts = {k: int(v) for k, v in TALLY_PAIR_RE.findall(found.group(1))}
        walked = counts.pop("walked", None)
        if walked is None:
            report.add("Audits", f"{path.name} counts nothing as `walked` — the other numbers "
                                 f"have nothing to add up to")
            continue
        total = sum(counts.values())
        if total != walked:
            named = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            report.add("Audits", f"{path.name} says it walked {walked} and accounts for {total} "
                                 f"({named}) — a report whose own header does not add up is one "
                                 f"nobody can use to tell coverage from silence")
        else:
            report.audits.append(f"{path.stem}: walked {walked}, and the knowledge has {entries} "
                                 f"entries")
    if unplaced:
        report.drift.append(
            f"files in {AUDITS}/ that are neither a lens this kit runs nor the baseline "
            f"({len(unplaced)}): {', '.join(unplaced)} — the lenses are "
            f"{', '.join(LENSES)}, and nothing adds up the scope of a file outside them. Rename it "
            f"to the lens that wrote it, or it is a report nobody can tell coverage from silence in")
    if uncounted:
        report.drift.append(
            f"audit files carry no `agent-kit:audit` counters ({len(uncounted)}): "
            f"{', '.join(uncounted)} — how much of its scope a lens walked is then its own claim, "
            f"and narrowing that scope quietly is the one failure every lens warns about. Files "
            f"written before the counters existed are in this count")


def run_defects(state: dict, root: Path | None = None) -> list:
    """What a run may not close with.

    Rules that held only as long as a run remembered them at the end of its longest step, and that a
    program can settle in a millisecond. They are asked at the moment of closing — by the run
    itself, and by the driver before it calls a feature built — and nowhere else: a finished run's
    file is history, and telling the next command about it reaches nobody who can act.

    Mostly `done` is judged — and three other moments a run file has to stand on its own: the
    handoff to the session that continues this run, the shape of its record fields, and a child
    still `queued`, whose `prompt` is the one thing here that can be fixed before it costs anything.
    A run that stopped at `blocked` is already saying so.

    `root` is the project, and only the rules that have to look at the repository need it: without
    one they are skipped rather than guessed at.

    Three of them are asked of features and not of errands — `suite`, `proved_at` and `mutation`. A
    child carrying its own `prompt` is not a `ship` — the frame child of a batch, an audit between
    two waves — and it has no suite to run and no code to mutate. Asked anyway, every batch of three
    or more would close with defects that are not defects, in the pull request, every night: exactly
    the noise that makes a real one unfindable.
    """
    out = []
    prompt = str(state.get("prompt") or "").strip()
    errand = bool(prompt)

    # A child that is not a `ship` is started by whatever this field says, and the field is a
    # command. Both rules below were paid for on one live run: thirteen of sixteen children were
    # started by two to five kilobytes of prose composed on the spot, and three of those pinned a
    # different version of this kit, so its children read rules three weeks apart. Judged whenever
    # this file is judged and not only as it closes — the session that can still fix it is the one
    # that wrote it.
    #
    # Judged while the child is still queued, and not afterwards. The session that can act on this
    # is the one that wrote the file; a child that has already run is history, and a batch written
    # before this rule existed — which `--resume` is required to carry on with — would otherwise
    # close every errand it holds with a defect nobody can now fix, straight into the pull request.
    if prompt and state.get("step") == "queued":
        if not prompt.lstrip().startswith("/"):
            out.append("`prompt` does not start with a command — a child is started by naming one, "
                       "and a slash command resolves whatever kit is installed. Prose here reaches "
                       "one session once; what the child must know goes in `entries` and `task`")
        if len(prompt) > PROMPT_MAX:
            out.append(f"`prompt` is {len(prompt)} characters against a ceiling of {PROMPT_MAX} — "
                       f"it is a command and this directory, not a briefing. What the child must "
                       f"know goes in `entries` and `task`, which are read by whoever resumes it; "
                       f"prose here is read once and is gone")
        pinned = PINNED_PLUGIN.search(prompt)
        if pinned:
            out.append(f"`prompt` points into a plugin cache pinned to a version — {pinned.group(0)}"
                       f" — so this child reads whatever kit the session that wrote it happened to "
                       f"be running. Name the command instead; a slash command resolves the kit "
                       f"that is installed")

    note = state.get("handoff")
    if isinstance(note, str) and note.strip():
        # Everything the next session gets, it gets from this file. The three ways it arrives
        # useless are all countable, so none of them is left to the outgoing session to notice.
        if len(note) > HANDOFF_MAX:
            out.append(f"`handoff` is {len(note)} characters against a ceiling of {HANDOFF_MAX} — "
                       f"the next session re-reads it on every step it takes, and what belongs to "
                       f"a field of its own is not a note")
        if not str(state.get("approach") or "").strip():
            out.append("`approach` is empty and this run is being handed over — the session that "
                       "takes it skips Design because the file carries one, so it would design this "
                       "feature a second time")
        if not (state.get("tasks") or []):
            out.append("`tasks` is empty and this run is being handed over — nothing says which "
                       "task the handoff stopped after, or what is left")
        # Its shape is judged below, on every run and not only the ones being handed over.

    # A field of records filled with sentences reads as answered to a person and is empty to the
    # closing session, the reviewer and this program. Checked whenever this file is judged and not
    # only as it closes — measured on one run, `tasks` is tested before every handoff and never
    # drifted all night, while `assumptions`, tested only at `done`, drifted twice in two different
    # batches. Same rule, same shape, different moment: at `done` there is nothing to do but report
    # it, and a session that hears it at its first handoff fixes it in a minute. Shape is safe to
    # test early — an empty field passes, and only prose already written can fail.
    for field in ("tasks", "assumptions", "manual"):
        value = state.get(field) or []
        if isinstance(value, list) and any(not isinstance(item, dict) for item in value):
            out.append(f"`{field}` is written as sentences rather than as records — the template "
                       f"says so at its head, and the pull request is composed from it by a "
                       f"session that reads run files and never the code")

    if state.get("step") != "done":
        return out

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
    recorded = not (suite is None or (isinstance(suite, str) and not suite.strip())
                    or suite in ([], {}))
    if not errand and not recorded:
        out.append("`suite` is empty — nothing says what was run or what it returned, and the pull "
                   "request is written from that field rather than from memory")

    # What a suite result is worth is what it is bound to. Every other field here is the run's own
    # account of itself, and a green suite measured three commits ago reads exactly like one
    # measured on what is being delivered — which is the difference between evidence and narration.
    # Presence is asked always; whether the tree exists is asked only where there is a repository to
    # ask it of, because a check that cannot reach its input must say nothing rather than guess.
    #
    # Asked of the runs that ran a suite, and of no others. A batch's own file carries what its
    # children reported, measured on trees it never stood on; asked for one tree of its own it would
    # have to invent one, which is the opposite of what this field is for.
    if not errand and recorded and state.get("command") in ("ship", "fix"):
        at = str(state.get("proved_at") or "").strip()
        if not at:
            out.append("`suite` says what the tests returned and `proved_at` says nothing about "
                       "which tree they ran on — `git rev-parse HEAD` at the moment the suite ran. "
                       "Unbound, a result that predates the last fix and one that does not read the "
                       "same")
        elif root is not None and git(root, "rev-parse", "--git-dir"):
            branch = str(state.get("branch") or "").strip()
            if git(root, "cat-file", "-t", at) != "commit":
                out.append(f"`proved_at` names {at[:12]}, which is not a commit in this repository "
                           f"— the suite's result is bound to a tree nobody can reach, which is the "
                           f"one thing the field exists to prevent")
            # And on the branch being delivered. A commit that exists somewhere is not evidence
            # about what is being handed over: a suite run on a branch that was then abandoned, or
            # before a rebase, passes the test above and says nothing. Asked only where the branch
            # itself can be resolved, because a run whose branch is gone is a different report.
            elif branch and git(root, "rev-parse", "--verify", "--quiet", branch) and \
                    subprocess.run(["git", "merge-base", "--is-ancestor", at, branch],
                                   cwd=root, capture_output=True, timeout=5).returncode != 0:
                out.append(f"`proved_at` names {at[:12]}, which is not in {branch} — the suite ran "
                           f"on a tree this branch does not contain, so nothing it returned is "
                           f"about what is being delivered")

    # The one piece of evidence in the kit that a test can fail, asked for only where the project
    # has declared a way to produce it. Judged on the field being answered, never on the numbers:
    # what a survivor means is the run's call, and a program that failed a run over a count would be
    # holding it to a threshold nobody set.
    if root is not None and state.get("command") in ("ship", "fix") and not errand:
        commands = read_manifest(root / MANIFEST).get("commands")
        declared = commands.get("mutate") if isinstance(commands, dict) else None
        mutation = state.get("mutation")
        mutation = mutation if isinstance(mutation, dict) else {}
        counted = any(mutation.get(key) is not None for key in ("killed", "survived"))
        # `why` alone is the cheap path out of this whole mechanism: not running the tool and
        # writing "it would not start" costs nothing and reads like a result. The command that was
        # actually run is the smallest artefact that path does not produce for free.
        excused = str(mutation.get("why") or "").strip() and str(mutation.get("command") or "").strip()
        if str(declared or "").strip() and not (counted or excused):
            out.append("`mutation` is empty and this project declares `commands.mutate` — a suite "
                       "nothing tried to break is the word of whoever wrote it, and a run that "
                       "skipped the step must not read like one that passed it. Not run? "
                       "`why` **and** the `command` you ran")

    # A run whose own job was to open a pull request, closing without its number. `deliver` is what
    # decides that and not `command`: a feature inside a batch pushes a branch and stops, and a
    # batch's own file has no `deliver` at all, so both fall outside this by construction. A run
    # that hit a blocker is allowed to end without one — it is already saying what went wrong.
    if state.get("deliver") == "pr" and not state.get("pr") and not (state.get("blockers") or []):
        out.append("`pr` is empty on a run that delivers one — the branch is pushed and nothing "
                   "records what it was opened as, so no later command can find it")

    # The batch's own durable record. `.agent-kit/runs/` is git-ignored, so what a batch cost lives
    # on one machine until this file is written; the gate of the next epic prices its scope from it.
    # Existence was all this asked for a long time, and existence is what it got: a file that parses
    # is not a record, and the shape is judged here because this session is the last one that could
    # fix it.
    if root is not None and state.get("command") == "sprint":
        slug = str(state.get("slug") or "").strip()
        path = root / "docs" / "runs" / f"{slug}.json" if slug else None
        if path is not None and not path.is_file():
            out.append(f"docs/runs/{slug}.json was never written — it is the only record of this "
                       f"batch that outlives the machine, and the next gate prices a scope from it")
        elif path is not None:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                out.append(f"docs/runs/{slug}.json cannot be read as a record ({exc}) — write it "
                           f"from `${{CLAUDE_PLUGIN_ROOT}}/templates/batch.json`")
            else:
                out.extend(batch_defects(record) if isinstance(record, dict) else
                           [f"docs/runs/{slug}.json is not a record — the template is "
                            f"`${{CLAUDE_PLUGIN_ROOT}}/templates/batch.json`"])

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

    # A branch a merged pull request already delivered is not work in flight, and printing it as
    # though it were is how one project reached 99 of them: every listing said "unmerged", nobody
    # could tell which were finished, so none was ever removed. Delivered ones are counted and
    # named to whoever may remove them; the rest are listed as before.
    delivered, unjudged = delivered_branches(root, base, offline) if base else ([], [])
    done_names = {name for name, _ in delivered}
    live = [b for b in work_branches(root, base) if b["ahead"] and b["branch"] not in done_names] \
        if base else []
    for branch in live[:UNMET_SHOWN // 2]:
        pushed = "pushed" if branch["pushed"] else "**never pushed**"
        print(f"  branch {branch['branch']}: {branch['ahead']} ahead, {branch['behind']} behind "
              f"{base}, {pushed}, last commit {branch['last']}")
    if len(live) > UNMET_SHOWN // 2:
        print(f"  … and {len(live) - UNMET_SHOWN // 2} more unmerged branches")
    if delivered:
        print(f"  {len(delivered)} branch(es) their pull request already delivered — "
              f"/agent-kit:next removes them: {', '.join(sorted(done_names)[:3])}"
              f"{', …' if len(delivered) > 3 else ''}")
    for name, why in unjudged[:3]:
        if name not in {b["branch"] for b in live}:
            print(f"  branch {name}: nothing says it is finished — {why}")

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

    # Silence here means the project can measure whether its tests are able to fail. Said at the
    # gate because that is where a scope is priced and somebody is present: without it the fact
    # surfaces per feature, at the end, as one line of a report nobody reads twice — and a suite
    # nothing has ever tried to break is the word of whoever wrote it.
    #
    # Three states and three sentences, because two of them are *this program* failing to read and
    # must never be said as a fact about the project. `commands` arrives as a string when somebody
    # wrote `commands: make all`, which is the shape that took `--state` down entirely — and
    # `--state` is what an epic's gate, `next` and `accept` all run.
    manifest_path = root / MANIFEST
    commands = read_manifest(manifest_path).get("commands")
    if not manifest_path.is_file():
        print(f"  tests: no {MANIFEST} here, so nothing says whether this project can prove its "
              f"tests able to fail — /agent-kit:blueprint writes that file")
    elif commands is not None and not isinstance(commands, dict):
        print(f"  tests: `commands` in {MANIFEST} is not a map this program can read, so whether "
              f"the tests can be proved able to fail is unknown — /agent-kit:blueprint owns that "
              f"file")
    elif not str((commands or {}).get("mutate") or "").strip():
        print("  tests: nothing measures whether they can fail — project.yml declares no "
              "`commands.mutate`, so every run reports the step as not run. Adding one is "
              "/agent-kit:blueprint's; until then no run may claim its tests would notice a defect")

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


def print_audits(report: Report) -> None:
    """How much of its own scope each lens says it walked. A statement: what the right number is
    differs by lens, and only a person can tell a narrow scope from a narrow project."""
    for line in report.audits:
        print(f"Audit {line}")


def print_parts(docs: list) -> None:
    """A statement, like the standing above it: an unwalked part is not a defect, it is a fact
    about how much of the description the owner has actually seen."""
    walked, derived = parts(docs)
    if not walked and not derived:
        print("Parts: none recorded — no line in product.md carries `walked: <date>` or `derived`, "
              "so nothing says which of this product the owner has ever walked")
        return
    print(f"Parts: {walked + derived} recorded, {walked} walked with the owner, {derived} derived "
          f"from the code and never confirmed")


def unreachable(docs: list, report: Report) -> tuple:
    """Decisions taken without the owner that no run will arrive at, and how many entries hold them.

    The kit's answer to an open block is that the next run building in that entry settles it in
    passing, with the owner there. That holds for an entry something is still planned to build in.
    Under a `built` entry it is false: nothing arrives, and the block stands for the life of the
    project — the same reasoning the ladder already applies to `[accepted …]`, which is raised
    because nothing else will ever reach it.

    Measured on one project after two autonomous runs: 47 of 58 standing decisions were in that
    position. Counted here rather than judged, because *which of them are expensive* is written in
    the block's own prose, in the project's language, and guessing a value out of prose is the one
    thing this program never does.
    """
    states = {entry.key: (entry.state or "") for doc in docs for entry in doc.entries}
    where = [at for at, _line, _body in report.assumed if states.get(at, "").startswith("built")]
    return len(where), len(set(where))


def print_entry_blocks(report: Report, docs: list, keys: list) -> None:
    """Every open block under the entries a command names, in full — and which of them it misread.

    The summary above prints entry names and nothing else, because one `epic` leaves dozens and
    printing all of them before every command buries the findings that are real. That leaves the
    *choosing* to the command, and a gate that chose wrong is what this exists for: told to read
    "the entries you are about to build", a live run took that to mean the entries with no code yet,
    and never opened the twenty-one built ones its scope was about to change. Fifty-one decisions
    taken without the owner stayed shut while the owner sat there answering other questions.

    So the caller says which entries it means and the program does the reading. A key that matches
    no entry is named, loudly: this is a filter, and a filter that quietly matches nothing looks
    exactly like an entry with nothing to answer.
    """
    known = {entry.key for doc in docs for entry in doc.entries}
    seen, wanted = set(), []
    for key in keys:
        if key not in seen:
            seen.add(key)
            wanted.append(key)

    print(f"\nOpen blocks under the {len(wanted)} "
          f"{'entry' if len(wanted) == 1 else 'entries'} this command named:")
    for key in wanted:
        if key not in known:
            continue
        blocks = [(line, body) for bucket in (report.assumed, report.notes, report.stale)
                  for at, line, body in bucket if at == key]
        if not blocks:
            print(f"  {key}: none")
            continue
        print(f"  {key}:")
        for line, body in blocks:
            for text in (body or line).splitlines():
                print(f"    {text}")
            print()

    missing = [key for key in wanted if key not in known]
    if missing:
        print(f"\n  Not an entry in this project's knowledge ({len(missing)}): "
              f"{', '.join(missing)} — nothing above covers them, so their silence means the key is "
              f"wrong and not that they are clear.")


def pr_body_defects(path: Path) -> int:
    """What a reader has to walk through before they can decide, measured before it is published.

    Two numbers, and both are **budgets somebody chose**, not measurements — which is the honest
    thing to say about them, because this kit has twice carried a number nobody could account for.
    What they were chosen against is real: one run's pull request came to 45 000 characters with a
    seventy-row table uncollapsed, and nothing in the kit noticed, because the rule it broke was a
    sentence asking for restraint. A sentence cannot count. Raise or lower these the day a real body
    says they are wrong, and say so in the changelog when you do.

    Collapsed content is not counted at all: `<details>` is the whole mechanism by which a body can
    be complete and short at once, and a rule that punished it would push writers to delete evidence
    instead of folding it. What is counted is what the reader cannot avoid.
    """
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"{path} cannot be read: {exc}", file=sys.stderr)
        return 2

    open_text = re.sub(r"<details\b.*?</details>", "", text, flags=re.S | re.I)
    rows, worst, current = 0, 0, 0
    for line in open_text.splitlines():
        if line.lstrip().startswith("|"):
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    rows = worst

    print(f"  {len(text)} characters, {len(open_text)} of them the reader cannot collapse; "
          f"biggest uncollapsed table: {max(0, rows - 2)} rows")

    defects = []
    if len(open_text) > PR_OPEN_MAX:
        defects.append(f"{len(open_text)} characters stand uncollapsed against a budget of "
                       f"{PR_OPEN_MAX} — the owner decides in the first lines whether this merges, "
                       f"and everything past that either serves the decision or folds into "
                       f"`<details>`")
    if rows - 2 > PR_TABLE_MAX:
        defects.append(f"an uncollapsed table runs to {rows - 2} rows against a budget of "
                       f"{PR_TABLE_MAX} — a table nobody can finish reading is one nobody reads, "
                       f"so keep the expensive rows open by name and fold the rest with their count")
    for line in defects:
        print(f"  {line}")
    return 1 if defects else 0


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
    parser.add_argument("--epic", action="store_true",
                        help="the gate of /agent-kit:epic: bounds, scenarios, and the commands that "
                             "start and test the application. Silent when it may start")
    parser.add_argument("--entries", nargs="+", metavar="KEY",
                        help="every open block under these entries, in full, instead of their "
                             "names: the entries a run is about to build or to change. Names any "
                             "key that matches no entry")
    parser.add_argument("--brief", metavar="KEY",
                        help="everything a run reads before it designs, in one call: the project's "
                             "corner, the entry, the entries it names, the library map")
    parser.add_argument("--run", metavar="DIR",
                        help="judge one run file as it closes: what a run at step done may not "
                             "leave behind. Silent when there is nothing")
    parser.add_argument("--pr-body", metavar="FILE",
                        help="measure a pull request's body before it is opened: how much of it a "
                             "reader must walk past, and the biggest table they cannot collapse")
    options = parser.parse_args(argv)

    root = options.root.resolve()

    if options.pr_body:
        return pr_body_defects(Path(options.pr_body))

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
        defects = run_defects(state if isinstance(state, dict) else {}, root)
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

    if options.brief:
        return brief(root, docs, options.brief.strip())

    if options.record:
        written = record(root, docs, root / MANIFEST)
        print("\n".join(f"  {line}" for line in written) if written
              else "  every hash was already current")
        return 0

    if options.epic:
        fatal = check_epic(root, manifest, docs, report)
        if fatal:
            print("This project cannot start an epic as it stands:")
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
    check_batches(root, report)
    check_channels(root, report)
    check_audits(root, docs, report)
    check_shape(root, docs, manifest, report)
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
        for _where, line, _body in report.stale:
            print(f"  {line}")
        print("  Applied by whoever next builds in that entry, with the owner present, or by "
              "/agent-kit:blueprint. Not a reason to run either.")

    if report.accepted:
        print(f"\nAccepted and not yet written up ({len(report.accepted)}) — the owner said yes and "
              "the record's fields are outstanding:")
        for _where, line, _body in report.accepted:
            print(f"  {line}")
        print("  Written up by /agent-kit:blueprint, which interviews the fields and deletes the "
              "block. Already decided — do not ask again whether it is wanted.")

    if report.frame:
        print(f"\nWhat a batch agreed to build alike ({len(report.frame)}) — binding on every run "
              "that touches the same ground, and in force as it stands:")
        for _where, line, _body in report.frame:
            print(f"  {line}")
        print("  Folded into the map by /agent-kit:blueprint once the batch has merged. Not a "
              "reason to run it.")

    for line in report.drift:
        print(f"\n  {line}")

    if report.debt:
        print(f"\nDebt ({len(report.debt)}) — work earlier runs decided not to do:")
        for line in report.debt[:UNMET_SHOWN]:
            print(f"  {line}")
        if len(report.debt) > UNMET_SHOWN:
            print(f"  … and {len(report.debt) - UNMET_SHOWN} more")

    # `stale` and `accepted` are statements; an `[assumed …]` is still a finding, because the run
    # that took it had nobody to ask and the owner has still not seen it.
    if report.shape:
        print(f"\nWritten by an older kit ({len(report.shape)}) — the shape the commands expect has "
              f"moved on, and only /agent-kit:blueprint can bring this forward, with you there:")
        for line in report.shape:
            print(f"  {line}")

    if report.clean and not report.notes and not report.assumed:
        if options.status:
            print("Knowledge is clean. " + ", ".join(standing(docs)))
            print_planned(docs)
            print_parts(docs)
            print_audits(report)
        # A `[stale …]` is a statement and leaves the report clean, so a run that asked about its
        # own entries is answered here too — otherwise the one call it makes goes silent on exactly
        # the entries it named.
        if options.entries:
            print_entry_blocks(report, docs, options.entries)
        if options.state:
            print_state(root, options.offline)
        return 0

    if options.status:
        print("Standing: " + ", ".join(standing(docs)))
        print_planned(docs)
        print_parts(docs)
        print_audits(report)
    for group, lines in report.groups.items():
        print(f"\n{group}:")
        for line in lines:
            print(f"  {line}")

    sources = report.groups.get("Sources") or []
    if len(sources) > 2 and all("changed" in line for line in sources):
        print("\n  Every source looks changed — most likely they were recorded before this program "
              "owned the hash. Re-record them with blueprint rather than reading each document.")
    if report.assumed:
        # Not "waiting for the owner": a run took the decision, and every later run in that entry
        # follows it — that is what keeps features consistent with each other. One `epic` leaves
        # dozens, and printing each of them before every command buries the findings that are real.
        # The entries are what a command needs — and *which* entries those are is the mistake this
        # line used to invite, so it names both kinds and hands the reading to `--entries`.
        where = sorted({at for at, _line, _body in report.assumed})
        entries = f"{len(where)} entry" if len(where) == 1 else f"{len(where)} entries"
        print(f"\nDecisions taken without the owner ({len(report.assumed)}) in {entries} — every "
              f"later run in them follows the block as written; only `blueprint` rewrites one. "
              f"Read the ones under the entries you are about to build **or to change**, with "
              f"--entries; a built entry whose behaviour this run moves is one of them:")
        print("  " + ", ".join(where))

        stuck, entries_stuck = unreachable(docs, report)
        if stuck:
            print(f"  of those, {stuck} in {entries_stuck} entries already `built` — nothing is "
                  f"planned there, so no run arrives to settle them in passing and only "
                  f"`blueprint` ever will.")

    if report.notes:
        print(f"\nOpen notes ({len(report.notes)}) — each is a decision waiting for the owner:")
        for _where, note, _body in report.notes:
            print(f"  {note}")

    if options.entries:
        print_entry_blocks(report, docs, options.entries)

    if options.state:
        print_state(root, options.offline)

    print("\nNot checked here: whether an answer is any good, whether a status an action sets is "
          "one the entity declares, and anything that needs the code read.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
