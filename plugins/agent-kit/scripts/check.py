#!/usr/bin/env python3
"""Audit a project's knowledge documents, mechanically.

    check.py [project root] [--status] [--offline]

This is what `/agent-kit:blueprint --check` runs, and what every other command runs before it
starts. It exists as a program rather than as instructions because a skill cannot be invoked by
another skill: told to "run blueprint --check", a build command went looking for an executable,
found none, and carried on without the check — silently, in every autonomous run.

It reads. It judges nothing: no quality, no research, no opinion about the prose. The one thing it
writes is an entry's state line, and only what a merged pull request already decided.

Silent when clean. `--status` always prints where the project stands.

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
MARK = "agent-kit:unmet"

KEY_RE = re.compile(r"^`key:\s*([^`·]+?)\s*`(?:\s*·\s*`state:\s*([^`]+?)\s*`)?", re.M)
HEADING_RE = re.compile(r"^###\s+(.+)$", re.M)
FIELDS_RE = re.compile(r"^fields:\s*(.+)$", re.M)
SOURCE_RE = re.compile(r"`source:\s*([^#`]+)#([^@`]+?)\s*@([0-9a-f]+)`")
NOTE_RE = re.compile(r"^>\s*\*\*\[(assumed|found)\b([^\]]*)\]\*\*\s*(.*)$", re.M)
REF_RE = re.compile(r"`([a-z][a-z0-9_]*\.[a-z0-9_]+)`")
MARK_RE = re.compile(re.escape(MARK) + r"[:\s]*([a-z][a-z0-9_]*\.[a-z0-9_]+)?")
STATE_LINE_RE = re.compile(r"(`key:\s*%s\s*`\s*·\s*`state:\s*)building \(pr:\s*(\d+)\)(\s*`)")

SLOTS = ("product", "actors", "entities", "actions", "screens", "integrations", "scenarios", "stack")


def digest(text: str) -> str:
    """The hash recorded beside a `source:` and a dependency manifest.

    Defined here so that whoever writes it and whoever verifies it cannot disagree. Blueprint asks
    this program for the value instead of inventing one — an earlier version left the algorithm to
    whoever happened to be reading, which made every recorded hash unverifiable by anything else.
    """
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:8]


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
        self.states: list = []
        self.unmet: list = []

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


def check_references(docs: list, report: Report) -> None:
    defined = set()
    for doc in docs:
        for entry in doc.entries:
            if not doc.commented(entry):
                defined.add(entry.key)
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
            if elsewhere == 0:
                report.add("Orphans", f"{doc.path.name}:{entry.line} {entry.key} — named nowhere else")


def check_sources(root: Path, docs: list, report: Report) -> None:
    for doc in docs:
        for path_text, heading, recorded in SOURCE_RE.findall(doc.text):
            target = root / path_text.strip()
            if not target.is_file():
                report.add("Sources", f"{doc.path.name} → {path_text} does not exist")
                continue
            section = section_of(target.read_text(encoding="utf-8"), heading.strip())
            if section is None:
                report.add("Sources", f"{doc.path.name} → {path_text}#{heading.strip()} — no such heading")
            elif digest(section) != recorded:
                report.add("Sources", f"{doc.path.name} → {path_text}#{heading.strip()} changed "
                                      f"({recorded} → {digest(section)})")


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
    for name, recorded in (checks.get("deps") or {}).items():
        target = root / name
        if not target.is_file():
            report.add("Stack", f"{name} is recorded but missing")
        elif digest(target.read_text(encoding="utf-8")) != recorded:
            report.add("Stack", f"{name} changed since the library map was written")


def check_verdicts(manifest: dict, report: Report) -> None:
    verdicts = manifest.get("knowledge") or {}
    for slot in SLOTS:
        value = (verdicts.get(slot) or "").split()[0] if verdicts.get(slot) else ""
        if not value:
            report.add("Verdicts", f"{slot} — no verdict in project.yml")
        elif value == "open_question":
            report.add("Verdicts", f"{slot} — open question")


def collect_unmet(root: Path, manifest: dict, report: Report) -> None:
    """Tests that prove a promise the product does not keep.

    They are green by design — the suite is told to expect them — so nothing else in a run will
    ever mention them again. This is the one place that does, which is why it prints on every
    command and not only when something is wrong.

    What is searched for is MARK, a constant of this kit written as a comment beside the test, and
    not whatever the suite uses to keep the test off the red. Frameworks differ, one project can
    have three suites in two languages, and a search for `->todo()` would find one of them at best.
    A constant is language-agnostic, so the search needs no list of test directories either: every
    tracked file is fair game and the mark can only be where someone put it deliberately.
    """
    files = tracked_files(root)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if MARK not in text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            found = MARK_RE.search(line)
            if found:
                key = found.group(1) or "no entry named"
                report.unmet.append(f"{path.relative_to(root)}:{number} {key}")

    form = ((manifest.get("tests") or {}).get("unmet") or "").strip().strip("\"'")
    if report.unmet and not form:
        report.add("Manifest", f"{len(report.unmet)} tests carry {MARK} but project.yml has no "
                               "tests.unmet — the form this project uses to keep such a test green")


def tracked_files(root: Path) -> list:
    listed = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if listed.returncode == 0:
        return sorted(root / p for p in listed.stdout.splitlines() if (root / p).is_file())
    skip = {".git", "node_modules", "vendor", "dist", "build", ".venv", "__pycache__"}
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and not skip & set(p.relative_to(root).parts))


def collect_notes(docs: list, report: Report) -> None:
    for doc in docs:
        for kind, tail, text in NOTE_RE.findall(doc.text):
            report.notes.append(f"[{kind}{tail}] {doc.path.name}: {text.strip()[:90]}")


def sync_states(docs: list, report: Report, offline: bool) -> None:
    """A merged pull request is the only thing that moves an entry to `built`."""
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
            text = text.replace(f"`key: {entry.key}` · `state: building (pr: {number})`",
                                f"`key: {entry.key}` · `state: {new}`")
            report.states.append(f"{entry.key}: building (pr: {number}) → {new}")
        if text != doc.text:
            doc.path.write_text(text, encoding="utf-8")
            doc.text = text


def standing(docs: list) -> list:
    counts: dict = {}
    for doc in docs:
        for entry in doc.entries:
            if doc.commented(entry) or not entry.state:
                continue
            key = entry.state.split(" (")[0]
            counts[key] = counts.get(key, 0) + 1
    return [f"{state}: {count}" for state, count in sorted(counts.items())]


# --------------------------------------------------------------------------------------------


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--status", action="store_true", help="always print where the project stands")
    parser.add_argument("--offline", action="store_true", help="do not ask gh about pull requests")
    parser.add_argument("--hash", nargs="+", metavar="ARG",
                        help="print the digest of a file, or of one heading inside it: --hash FILE [HEADING]")
    options = parser.parse_args(argv)

    root = options.root.resolve()

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
        if options.status:
            print(f"no {KNOWLEDGE}/ — this project has no blueprint yet")
        return 0

    docs = [Doc(p) for p in sorted(knowledge.glob("*.md"))]
    manifest = read_manifest(root / MANIFEST)
    report = Report()

    sync_states(docs, report, options.offline)
    check_fields(docs, report)
    check_references(docs, report)
    check_orphans(docs, report)
    check_sources(root, docs, report)
    check_stack(root, manifest, report)
    check_verdicts(manifest, report)
    collect_unmet(root, manifest, report)
    collect_notes(docs, report)

    if report.states:
        print("Moved by their pull requests:")
        for line in report.states:
            print(f"  {line}")

    if report.unmet:
        print(f"\nPromises the product does not keep ({len(report.unmet)}) — the entry, and the "
              "test already written for it, waiting for the product to change or the entry to:")
        for line in report.unmet:
            print(f"  {line}")
        print("  Not this run's work. They are offered as a batch by /agent-kit:sprint with no theme.")

    if report.clean and not report.notes:
        if options.status:
            print("Knowledge is clean. " + ", ".join(standing(docs)))
        return 0

    if options.status:
        print("Standing: " + ", ".join(standing(docs)))
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

    print("\nNot checked here: whether an answer is any good, whether a status an action sets is "
          "one the entity declares, and anything that needs the code read.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
