#!/usr/bin/env python3
"""Mechanically check a project's knowledge contract.

Reads `<root>/.agent-kit/knowledge/contract.yml` and reports, without a grader:

- every slot and collection has a terminal verdict (`filled`, `not_applicable`
  with a reason, `open_question`) — `empty`, `conflicts`, and any other status
  are findings;
- every `source` a slot binds to resolves to a file and a section — a missing
  file, an unreadable contract, or a missing/ambiguous heading is structural.
  A collection's `sources` globs are not resolved here; that is stage 2's work,
  along with the entries themselves;
- every binding with a `source` carries a `rev` that still matches the
  section's current hash — a mismatch or a missing `rev` is a finding;
- unless `--skip-verification`, every command under `verification.commands`
  runs from `<root>` and must exit 0 — a non-zero exit or a timeout is
  structural.

Exit 0 clean, 1 on findings, 2 on a structural failure. Stdlib only.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kit_markdown  # noqa: E402
import kit_yaml  # noqa: E402

TERMINAL_STATUSES = ("filled", "not_applicable", "open_question")
VERIFICATION_TIMEOUT = 300


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="do not run verification.commands (avoids self-invocation from within them)",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    contract_path = os.path.join(root, ".agent-kit", "knowledge", "contract.yml")
    try:
        with open(contract_path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        print("✗ contract")
        print("  no contract at {}".format(contract_path))
        print("  start one by copying the kit's template:")
        print("    ${CLAUDE_PLUGIN_ROOT}/templates/project/contract.yml")
        print("    → .agent-kit/knowledge/contract.yml")
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print("✗ contract\n  cannot read {}: {}".format(contract_path, exc))
        return 2

    try:
        data = kit_yaml.load(text, contract_path)
    except kit_yaml.KitYamlError as exc:
        print("✗ contract\n  {}".format(exc))
        return 2

    if not isinstance(data, dict):
        print("✗ contract\n  {} does not contain a mapping at the top level".format(contract_path))
        return 2

    slots = data.get("slots") or {}
    collections = data.get("collections") or {}

    for label, group in (("slots", slots), ("collections", collections)):
        if not isinstance(group, dict):
            print("✗ contract")
            print(
                "  `{}` is not a mapping of names to entries in {}".format(
                    label, contract_path
                )
            )
            return 2

    findings = []
    structural = []

    for name, item in slots.items():
        _check_item(name, item, root, findings, structural)
    for name, item in collections.items():
        _check_item(name, item, root, findings, structural)

    verification = slots.get("verification")
    if (
        isinstance(verification, dict)
        and verification.get("status") in TERMINAL_STATUSES
        and not args.skip_verification
    ):
        _check_verification(verification, root, structural)

    _report(slots, collections, findings, structural)

    if structural:
        return 2
    if findings:
        return 1
    return 0


def _check_item(name, item, root, findings, structural):
    if not isinstance(item, dict):
        structural.append((name, "entry is not a mapping"))
        return

    status = item.get("status")
    if status not in TERMINAL_STATUSES:
        findings.append((name, "status is {!r}, not a terminal verdict".format(status)))
    elif status == "not_applicable" and not item.get("reason"):
        findings.append((name, "status is not_applicable with no reason recorded"))

    source = item.get("source")
    if status == "filled" and not source and not item.get("commands"):
        findings.append(
            (name, "status is filled but nothing backs it — no source and no commands")
        )
    if not source:
        return

    try:
        path, heading = source.split("#", 1)
    except ValueError:
        structural.append((name, "source {!r} is not of the form file#heading".format(source)))
        return

    file_path = os.path.join(root, path)
    if not os.path.isfile(file_path):
        structural.append((name, "source file does not exist: {}".format(path)))
        return

    try:
        with open(file_path, encoding="utf-8") as fh:
            doc_text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        structural.append((name, "cannot read source file {}: {}".format(path, exc)))
        return

    try:
        _level, _title, body = kit_markdown.section(doc_text, heading)
    except kit_markdown.MissingSection:
        structural.append((name, "no section {!r} in {}".format(heading, path)))
        return
    except kit_markdown.AmbiguousSection:
        structural.append((name, "more than one section {!r} in {}".format(heading, path)))
        return

    current_rev = kit_markdown.rev(body)
    stored_rev = item.get("rev")
    if not stored_rev:
        # The current hash is printed so a fresh binding can be completed by
        # copying it; there is no --resolve until stage 5.
        findings.append(
            (
                name,
                "bound to {} but has no rev recorded — current rev is {}".format(
                    source, current_rev
                ),
            )
        )
    elif stored_rev != current_rev:
        findings.append(
            (
                name,
                "stale — {} changed since rev was recorded ({} != {})".format(
                    source, stored_rev, current_rev
                ),
            )
        )


def _check_verification(verification, root, structural):
    for command in verification.get("commands") or []:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=root,
                timeout=VERIFICATION_TIMEOUT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except subprocess.TimeoutExpired:
            structural.append(
                ("verification", "command timed out after {}s: {}".format(VERIFICATION_TIMEOUT, command))
            )
            continue
        if result.returncode != 0:
            structural.append(
                ("verification", "command exited {}: {}".format(result.returncode, command))
            )


def _status_summary(items):
    counts = {}
    other = 0
    for item in items.values():
        status = item.get("status") if isinstance(item, dict) else None
        if status in TERMINAL_STATUSES:
            counts[status] = counts.get(status, 0) + 1
        else:
            other += 1
    parts = []
    for status in TERMINAL_STATUSES:
        if counts.get(status):
            parts.append("{} {}".format(counts[status], status))
    if other:
        parts.append("{} needs verdict".format(other))
    return " · ".join(parts) if parts else "none"


def _report(slots, collections, findings, structural):
    print("slots        {}".format(_status_summary(slots)))
    print("collections  {}".format(_status_summary(collections)))

    for name, message in structural:
        print()
        print("✗ {}".format(name))
        print("  {}".format(message))

    for name, message in findings:
        print()
        print("⚠ {}".format(name))
        print("  {}".format(message))

    stale = [name for name, message in findings if message.startswith("stale ")]
    print()
    if stale:
        print("stale        {}".format(", ".join(stale)))
    else:
        print("stale        none")


if __name__ == "__main__":
    sys.exit(main())
