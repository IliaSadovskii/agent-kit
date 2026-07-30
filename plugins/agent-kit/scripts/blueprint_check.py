#!/usr/bin/env python3
"""The mechanical half of the knowledge contract: `/agent-kit:blueprint --check`.

Reads `.agent-kit/knowledge/contract.yml` and answers in seconds, with no grader and no model in
the loop: does every slot carry a terminal verdict, does every source still resolve, does every
bound section still hash to what was recorded, and do the project's verification commands actually
run and return zero.

Three exit codes, because a later stage puts this in front of every build command:

    0  clean
    1  findings      — a slot in a forbidden state, an unresolved binding, a stale section
    2  structural    — the contract cannot be read, a source is gone, a verification command failed

Structural wins over findings; both are reported in full first, so one run shows everything that is
wrong rather than the first thing that is.

Importable as well as runnable: `check(root, run_commands=False)` is the structural half on its own,
which is how this repository's own contract is covered by a build that the contract itself names.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys

import kit_yaml

CONTRACT_PATH = os.path.join(".agent-kit", "knowledge", "contract.yml")
TEMPLATE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "project",
                 "contract.yml"))

# The slot list is fixed by the kit version. A slot the contract omits is reported exactly like an
# empty one: a slot a later kit version added shows up as needing a verdict, never as absent.
SINGULAR_SLOTS = ("north_star", "architecture_stance", "verification", "mvp_bounds", "scenarios",
                  "deferred_seams")
COLLECTION_SLOTS = ("actors", "entities", "actions", "screens", "integrations")

TERMINAL = ("filled", "not_applicable", "open_question")
FORBIDDEN = ("empty", "conflicts")

COMMAND_TIMEOUT = 300

# A closing run of `#` is only a closing sequence when a space precedes it, so a heading may end in
# one: `## Why C#` is titled "Why C#", and a slot bound to it must resolve.
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


class SectionError(Exception):
    """A binding that cannot be resolved: the heading is missing, or it is not unique."""


def headings(text):
    """Every ATX heading as (level, title, line index), ignoring anything inside a code fence."""
    found, fence = [], None
    for index, line in enumerate(text.splitlines()):
        marker = _FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif line.strip().startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        match = _HEADING.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2).strip(), index))
    return found


def section_body(text, heading):
    """The text between `heading` and the next heading of the same level or shallower.

    Line endings are normalized, so a CRLF checkout does not make every binding stale; nothing else
    is. Whitespace inside the section is part of it — the hash is meant to notice edits, and an edit
    that only moved whitespace is still an edit the owner made.
    """
    all_headings = headings(text)
    matches = [h for h in all_headings if h[1] == heading]
    if not matches:
        raise SectionError(f"no heading {heading!r}")
    if len(matches) > 1:
        lines = ", ".join(f"line {h[2] + 1}" for h in matches)
        raise SectionError(f"heading {heading!r} is not unique ({lines})")
    level, _, start = matches[0]
    end = len(text.splitlines())
    for other_level, _, other_start in all_headings:
        if other_start > start and other_level <= level:
            end = other_start
            break
    return "\n".join(text.splitlines()[start + 1:end])


def section_rev(text, heading):
    body = section_body(text, heading)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


class Report:
    def __init__(self):
        self.findings = []      # (where, message) — exit 1
        self.structural = []    # (where, message) — exit 2
        self.stale = []         # (where, source, recorded, actual)
        self.slot_counts = {}
        self.collection_counts = {}
        self.commands = []      # (name, command, ok)

    def finding(self, where, message):
        self.findings.append((where, message))

    def fault(self, where, message):
        self.structural.append((where, message))

    @property
    def exit_code(self):
        if self.structural:
            return 2
        return 1 if self.findings or self.stale else 0


def _count(counts, status):
    counts[status] = counts.get(status, 0) + 1


def _check_status(report, where, entry, kinds):
    """The half every slot shares: a terminal verdict, and a reason where one is owed."""
    status = entry.get("status")
    if status is None or status == "":
        report.finding(where, "no status recorded — every slot needs a deliberate verdict: "
                              "filled, not_applicable, or open_question")
        return None
    if status in FORBIDDEN:
        report.finding(where, f"{status} is not a verdict — resolve it to filled, not_applicable, "
                              "or open_question")
        _count(kinds, status)
        return None
    if status not in TERMINAL:
        report.finding(where, f"unknown status {status!r} — expected one of {', '.join(TERMINAL)}")
        _count(kinds, status)
        return None
    _count(kinds, status)
    if status == "not_applicable" and not entry.get("reason"):
        report.finding(where, "not_applicable with no reason — the reason is what keeps it from "
                              "being a shrug")
    return status


def _check_binding(report, root, where, entry):
    """Resolve `path#heading`, and compare the section's hash against the recorded rev."""
    source = entry.get("source")
    path, _, heading = str(source).partition("#")
    if not heading:
        report.fault(where, f"source {source!r} names no section — the form is path#heading")
        return
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        report.fault(where, f"source file is gone: {path}")
        return
    with open(full, encoding="utf-8") as handle:
        text = handle.read()
    try:
        actual = section_rev(text, heading)
    except SectionError as exc:
        report.fault(where, f"{path}: {exc} — a renamed heading reads as a missing section")
        return
    recorded = entry.get("rev")
    if not recorded:
        report.finding(where, f"bound to {source} but never verified — record rev: {actual}")
    elif recorded != actual:
        report.stale.append((where, source, recorded, actual))


def _run_commands(report, root, where, commands):
    for name, command in commands.items():
        # The template ships `commands:` as comments, so a half-filled slot — a name with nothing
        # after the colon — is the likeliest shape this ever meets. That is a structural failure to
        # report, not a traceback.
        if not isinstance(command, str) or not command.strip():
            report.commands.append((name, command, False))
            report.fault(where, f"{name}: {command!r} is not a command")
            continue
        try:
            done = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True,
                                  timeout=COMMAND_TIMEOUT)
        except subprocess.TimeoutExpired:
            report.commands.append((name, command, False))
            report.fault(where, f"{name}: `{command}` did not finish within {COMMAND_TIMEOUT}s")
            continue
        report.commands.append((name, command, done.returncode == 0))
        if done.returncode != 0:
            output = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
            tail = "".join(f"\n    {line}" for line in output[-3:])
            report.fault(where, f"{name}: `{command}` exited {done.returncode}{tail}")


def _check_verification(report, root, where, entry, run_commands):
    commands = entry.get("commands")
    if not isinstance(commands, dict) or not commands:
        report.finding(where, "filled, but names no commands — this is the one slot whose "
                              "readiness is proven by running it")
        return
    if run_commands:
        _run_commands(report, root, where, commands)


def check(root, run_commands=True):
    """Run the contract check against `root`. Returns a Report; raises nothing for a bad contract."""
    report = Report()
    path = os.path.join(root, CONTRACT_PATH)
    if not os.path.isfile(path):
        report.fault(CONTRACT_PATH, "no knowledge contract here — a project starts from the "
                                    f"template at {TEMPLATE_PATH}")
        return report
    try:
        contract = kit_yaml.load_path(path)
    except kit_yaml.KitYamlError as exc:
        report.fault(CONTRACT_PATH, f"{exc} — the kit reads a YAML subset and will not guess")
        return report
    except OSError as exc:
        report.fault(CONTRACT_PATH, str(exc))
        return report
    if not isinstance(contract, dict):
        report.fault(CONTRACT_PATH, "the contract is not a mapping")
        return report

    for kind, expected, counts in (("slots", SINGULAR_SLOTS, report.slot_counts),
                                   ("collections", COLLECTION_SLOTS, report.collection_counts)):
        block = contract.get(kind) or {}
        if not isinstance(block, dict):
            report.fault(kind, f"`{kind}` is not a mapping of slot id to slot")
            continue
        for name in sorted(set(block) - set(expected)):
            report.finding(f"{kind}/{name}", "not a slot this kit version knows")
        for name in expected:
            where = f"{kind}/{name}"
            entry = block.get(name)
            if entry is None:
                report.finding(where, "no slot recorded — this kit version expects it; give it a "
                                      "verdict")
                _count(counts, "missing")
                continue
            if not isinstance(entry, dict):
                report.fault(where, "the slot is not a mapping")
                continue
            status = _check_status(report, where, entry, counts)
            if status != "filled":
                continue
            if kind == "collections":
                _check_sources(report, root, where, entry)
            elif name == "verification":
                _check_verification(report, root, where, entry, run_commands)
            elif entry.get("source"):
                _check_binding(report, root, where, entry)
            else:
                report.finding(where, "filled, but nothing says where the answer is — bind it with "
                                      "source: path#heading")
    return report


def _check_sources(report, root, where, entry):
    """A collection binds to globs at this stage; its entries and anchors are stage 2's work."""
    sources = entry.get("sources")
    if not isinstance(sources, list) or not sources:
        report.finding(where, "filled, but names no sources — a collection binds to the documents "
                              "its entries live in")
        return
    for pattern in sources:
        if not glob.glob(os.path.join(root, str(pattern)), recursive=True):
            report.fault(where, f"source matches nothing: {pattern}")


def _summary(counts):
    order = list(TERMINAL) + list(FORBIDDEN) + ["missing"]
    parts = [f"{counts[status]} {status}" for status in order if counts.get(status)]
    parts += [f"{n} {status}" for status, n in sorted(counts.items()) if status not in order]
    return " · ".join(parts) or "none recorded"


def render(report):
    lines = [
        f"slots        {_summary(report.slot_counts)}",
        f"collections  {_summary(report.collection_counts)}",
    ]
    for name, command, ok in report.commands:
        lines.append(f"verification {name}: {command} → {'ok' if ok else 'FAILED'}")
    for where, message in report.structural:
        lines += ["", f"✗ {where}", f"  {message}"]
    for where, message in report.findings:
        lines += ["", f"⚠ {where}", f"  {message}"]
    for where, source, recorded, actual in report.stale:
        lines += ["", f"stale        {where}", f"  {source} changed since it was recorded "
                                               f"({recorded} → {actual})"]
    return "\n".join(lines)


def main(argv):
    mode = argv[1:] or ["--check"]
    if mode != ["--check"]:
        print(f"usage: {os.path.basename(argv[0])} [--check]", file=sys.stderr)
        return 2
    report = check(os.getcwd())
    print(render(report))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
