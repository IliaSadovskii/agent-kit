#!/usr/bin/env python3
"""What a run cost. Development tool for the kit itself; it does not ship with the plugin.

    scripts/measure.py /projects/realest              every session of that project
    scripts/measure.py /projects/realest --by-branch  grouped by git branch — one ship run each

Context re-reading is the cost that matters, so `cache_read` is the headline number: a session pays
it again on every step. Records are deduplicated by message id, because a transcript repeats the
same `usage` block once per content block and reads ~1.7x too high without it.
"""
import argparse
import collections
import glob
import json
import os
import sys

FIELDS = ("cache_read_input_tokens", "cache_creation_input_tokens", "input_tokens", "output_tokens")


def transcripts(project_dir):
    """Every session file of a project, plus the subagent transcripts under each session."""
    slug = "-" + project_dir.strip("/").replace("/", "-")
    root = os.path.expanduser(f"~/.claude/projects/{slug}")
    if not os.path.isdir(root):
        sys.exit(f"no transcripts for {project_dir} (looked in {root})")
    return sorted(glob.glob(f"{root}/*.jsonl") + glob.glob(f"{root}/*/subagents/*.jsonl"))


def collect(paths, key_of):
    totals = collections.defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    steps = collections.Counter()
    seen = set()
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                message = record.get("message") or {}
                usage = message.get("usage")
                if not usage:
                    continue
                mid = message.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                key = key_of(record, path)
                for field in FIELDS:
                    totals[key][field] += usage.get(field) or 0
                steps[key] += 1
    return totals, steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--by-branch", action="store_true", help="group by git branch instead of session")
    args = ap.parse_args()

    paths = transcripts(args.project)
    if args.by_branch:
        key_of = lambda record, path: record.get("gitBranch") or "(no branch)"
    else:
        key_of = lambda record, path: os.path.basename(path).replace(".jsonl", "")[:8] + (
            " (subagent)" if "/subagents/" in path else "")

    totals, steps = collect(paths, key_of)
    if not totals:
        sys.exit("no usage records found")

    m = lambda n: f"{n / 1_000_000:.1f}M"
    width = max(len(str(k)) for k in totals)
    print(f"{'':<{width}}  {'cache_read':>11} {'cache_write':>11} {'output':>9} {'steps':>6}")
    for key, t in sorted(totals.items(), key=lambda kv: -kv[1]["cache_read_input_tokens"]):
        print(f"{key:<{width}}  {m(t['cache_read_input_tokens']):>11} "
              f"{m(t['cache_creation_input_tokens']):>11} {m(t['output_tokens']):>9} {steps[key]:>6}")
    grand = sum(t["cache_read_input_tokens"] for t in totals.values())
    print(f"\ntotal context re-read: {m(grand)} over {sum(steps.values())} steps")


if __name__ == "__main__":
    main()
