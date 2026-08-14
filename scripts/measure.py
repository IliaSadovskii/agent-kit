#!/usr/bin/env python3
"""What a run cost. Development tool for the kit itself; it does not ship with the plugin.

    scripts/measure.py /projects/realest                every session of that project
    scripts/measure.py /projects/realest --by-role      grouped by what the session was doing
    scripts/measure.py /projects/realest --by-branch    grouped by git branch
    scripts/measure.py /projects/realest --curve        fit ship sessions and price the ceiling
    scripts/measure.py /projects/realest --since 2026-08-13

Three things this has to get right, because each of them has already been got wrong once:

**Prices, not raw tokens.** The four kinds of token differ by a factor of fifty, so a total in raw
tokens is a number nobody can act on. Everything here is in *weighted* tokens — a plain input token
is 1, cache read 0.1, cache write 1.25, output 5 — which is the only unit in which "context re-read"
and "output" can be compared at all.

**A turn is one reply of the model, not one transcript record.** A reply carrying several content
blocks is several records, a factor of ~1.9, and a curve fitted against the wrong axis is what put
the handoff ceiling 14% off its bottom. Records are deduplicated by `message.id`.

**Subagents count.** They live in `<session>/subagents/*.jsonl` and were 15% of one project's whole
spend. Leaving them out is how a run's cost reads low.

See docs/design/2026-08-14-where-the-tokens-burn.md for what these numbers said the last time.
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys
from collections import defaultdict

PRICE = {"input_tokens": 1.0, "cache_creation_input_tokens": 1.25,
         "cache_read_input_tokens": 0.1, "output_tokens": 5.0}
CONTEXT = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

# What the driver types into a session is what it was doing, so the role is read off the opening
# records rather than guessed from the file name. `mvp` is what `epic` was called before 2.0.0.
#
# The name must not run into a word: a run directory called `2026-08-13-epic-mvp-finish` appears in
# the arguments of every `--advance` of that run, and a plain `\b` matched the `/mvp-finish` inside
# it — filing twelve of one run's own sessions under a command nobody typed.
COMMAND = re.compile(r"/(?:agent-kit:)?(ship|epic|mvp|sprint|blueprint|audit|fix|accept|next|advise)"
                     r"(?![-\w])[^\"]{0,200}")


def sessions(project_dir):
    slug = "-" + project_dir.strip("/").replace("/", "-")
    root = os.path.expanduser(f"~/.claude/projects/{slug}")
    if not os.path.isdir(root):
        sys.exit(f"no transcripts for {project_dir} (looked in {root})")
    return root, sorted(glob.glob(f"{root}/*.jsonl"))


def scan(path):
    """One session: what it cost, how many turns it took, and what it was doing."""
    row = {"file": os.path.basename(path), "cost": 0.0, "turns": 0, "floor": 0, "peak": 0,
           "started": None, "branch": None, "command": None, "records": 0}
    seen = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            row["records"] += 1
            stamp = record.get("timestamp")
            if stamp and (row["started"] is None or stamp < row["started"]):
                row["started"] = stamp
            if record.get("gitBranch"):
                row["branch"] = record["gitBranch"]
            if row["command"] is None and row["records"] < 200 \
                    and record.get("type") in ("user", "queue-operation"):
                found = COMMAND.search(line)
                if found:
                    row["command"] = " ".join(found.group(0).split())
            message = record.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if not isinstance(usage, dict) or message.get("id") in seen:
                continue
            seen.add(message.get("id"))
            row["cost"] += sum(int(usage.get(f) or 0) * p for f, p in PRICE.items())
            size = sum(int(usage.get(f) or 0) for f in CONTEXT)
            row["peak"] = max(row["peak"], size)
            if not row["floor"]:
                row["floor"] = size
            row["turns"] += 1
    return row


def with_subagents(root, path):
    """A session and everything it spawned, as one row plus the children's cost."""
    row = scan(path)
    row["agents"] = 0.0
    for child in sorted(glob.glob(os.path.join(root, os.path.basename(path)[:-6],
                                               "subagents", "*.jsonl"))):
        row["agents"] += scan(child)["cost"]
    return row


def role(row):
    """What this session was: the invocation, narrowed to the flag that changes its job."""
    command = row["command"] or ""
    if not command:
        return "(no kit command)"
    name = re.match(r"/?(?:agent-kit:)?([a-z]+)", command).group(1)
    if "--close" in command:
        return "sprint --close"
    for flag in ("--advance", "--resume", "--window"):
        if flag in command:
            return f"{name} {flag}"
    if name == "ship" or "--run" in command:
        return "ship (feature child)"
    return name


def million(n):
    return f"{n / 1_000_000:.2f}M"


# --------------------------------------------------------------------------------------------
# the curve
#
# Refitted here rather than quoted, because the whole point of the note this comes from is that a
# curve quoted from a previous reading is a curve nobody has checked.


def fit(points):
    """Least squares for cost = a + b·n + c·n², over (turns, cost) pairs."""
    if len(points) < 6:
        return None
    order = 3
    xs = [[p[0] ** k for k in range(order)] for p in points]
    ys = [p[1] for p in points]
    a = [[sum(x[i] * x[j] for x in xs) for j in range(order)] for i in range(order)]
    b = [sum(xs[k][i] * ys[k] for k in range(len(points))) for i in range(order)]
    for i in range(order):                        # gaussian elimination, pivoted
        pivot = max(range(i, order), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        b[i], b[pivot] = b[pivot], b[i]
        if not a[i][i]:
            return None
        for r in range(i + 1, order):
            f = a[r][i] / a[i][i]
            for c in range(i, order):
                a[r][c] -= f * a[i][c]
            b[r] -= f * b[i]
    out = [0.0] * order
    for i in reversed(range(order)):
        out[i] = (b[i] - sum(a[i][j] * out[j] for j in range(i + 1, order))) / a[i][i]
    return out


def curve(rows):
    """Fit the feature children and price every ceiling against the run's own feature lengths."""
    ship = [r for r in rows if role(r) == "ship (feature child)" and r["turns"] >= 5]
    if len(ship) < 6:
        sys.exit(f"only {len(ship)} ship sessions here — too few to fit anything")
    coeffs = fit([(r["turns"], r["cost"] + r["agents"]) for r in ship])
    if coeffs is None:
        sys.exit("the fit did not converge")
    a, b, c = coeffs
    floors = [r["floor"] for r in ship if r["floor"]]
    floor = statistics.median(floors) if floors else 0
    growth = statistics.median([(r["peak"] - r["floor"]) / r["turns"]
                                for r in ship if r["floor"] and r["turns"] >= 20] or [0])

    print(f"\nfitted over {len(ship)} feature children")
    print(f"  cost(n) = {a / 1e6:.3f}M + {b / 1000:.2f}k·n + {c:.2f}·n²")
    print(f"  context(n) = {floor / 1000:.1f}k + {growth / 1000:.2f}k·n")

    print("\nobserved against the fit")
    print(f"  {'turns':>7} {'sessions':>9} {'observed':>10} {'fit':>10}")
    groups = defaultdict(list)
    for r in ship:
        groups[(r["turns"] // 20) * 20].append(r["cost"] + r["agents"])
    for low in sorted(groups):
        mid = low + 10
        seen = statistics.median(groups[low])
        print(f"  {low:>3}-{low + 19:<3} {len(groups[low]):>9} {million(seen):>10} "
              f"{million(a + b * mid + c * mid * mid):>10}")

    # How long a feature actually is here — the thing a ceiling is priced against. `run.log` is
    # gone by now on most machines, so the run directory is not the source: the sum of the turns of
    # every session that named the same run directory is.
    by_run = defaultdict(int)
    for r in ship:
        found = re.search(r"runs/([0-9a-z-]+)", r["command"] or "")
        if found:
            by_run[found.group(1)] += r["turns"]
    lengths = sorted(by_run.values())
    if not lengths:
        print("\nno run directories in these transcripts — cannot price a ceiling")
        return
    print(f"\n{len(lengths)} features, total turns each: median {statistics.median(lengths):.0f}, "
          f"p90 {lengths[int(.9 * len(lengths))]}, max {max(lengths)}")

    def total(useful, ceiling):
        """Cheapest way to do `useful` turns of work under a ceiling, in segments."""
        per = max(10, (ceiling - floor) / growth) if growth else 1e9
        k = 1
        while k < 40 and (18 + useful + 8 * (k - 1)) / k > per:
            k += 1
        n = (18 + useful + 8 * (k - 1)) / k
        return k * (a + b * n + c * n * n)

    work = [max(20, n - 18) for n in lengths]
    priced = {ceiling: sum(total(w, ceiling * 1000) for w in work)
              for ceiling in (110, 130, 150, 170, 190, 210, 240, 280, 340)}
    best = min(priced.values())
    print("\nwhat every ceiling would have cost these features")
    print(f"  {'ceiling':>8} {'cost':>10} {'vs best':>9}")
    for ceiling, cost in priced.items():
        mark = "  <- bottom" if cost == best else ""
        print(f"  {ceiling:>7}k {million(cost):>10} {100 * cost / best - 100:>8.1f}%{mark}")
    print("\n  Re-orientation is taken at 8 turns on a handoff and 18 from nothing. Re-measure it "
          "\n  before trusting this table: it is the first thing a change to `ship` moves.")


# --------------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--by-role", action="store_true", help="group by what the session was doing")
    ap.add_argument("--by-branch", action="store_true", help="group by git branch")
    ap.add_argument("--curve", action="store_true",
                    help="fit the feature children and price every handoff ceiling against them")
    ap.add_argument("--since", metavar="YYYY-MM-DD", help="only sessions that started on or after")
    args = ap.parse_args()

    root, paths = sessions(args.project)
    rows = [with_subagents(root, p) for p in paths]
    if args.since:
        rows = [r for r in rows if (r["started"] or "") >= args.since]
    rows = [r for r in rows if r["turns"]]
    if not rows:
        sys.exit("no usage records found")

    whole = sum(r["cost"] + r["agents"] for r in rows)
    print(f"{len(rows)} sessions, {sum(r['turns'] for r in rows)} turns, "
          f"{million(whole)} weighted tokens "
          f"({million(sum(r['agents'] for r in rows))} of it in subagents)")

    if args.by_role or args.by_branch:
        key = role if args.by_role else (lambda r: r["branch"] or "(no branch)")
        groups = defaultdict(list)
        for r in rows:
            groups[key(r)].append(r)
        width = max(len(str(k)) for k in groups)
        print(f"\n{'':<{width}}  {'sessions':>8} {'own':>9} {'agents':>9} {'total':>9} "
              f"{'share':>6} {'turns/s':>8}")
        for name, group in sorted(groups.items(), key=lambda kv: -sum(
                r["cost"] + r["agents"] for r in kv[1])):
            own = sum(r["cost"] for r in group)
            agents = sum(r["agents"] for r in group)
            print(f"{name:<{width}}  {len(group):>8} {million(own):>9} {million(agents):>9} "
                  f"{million(own + agents):>9} {100 * (own + agents) / whole:>5.1f}% "
                  f"{sum(r['turns'] for r in group) / len(group):>8.0f}")
    else:
        print(f"\n{'session':<10} {'role':<22} {'total':>9} {'turns':>6} {'floor':>7} {'peak':>8}")
        for r in sorted(rows, key=lambda r: -(r["cost"] + r["agents"]))[:60]:
            print(f"{r['file'][:8]:<10} {role(r)[:22]:<22} {million(r['cost'] + r['agents']):>9} "
                  f"{r['turns']:>6} {r['floor'] / 1000:>6.0f}k {r['peak'] / 1000:>7.0f}k")

    if args.curve:
        curve(rows)


if __name__ == "__main__":
    main()
