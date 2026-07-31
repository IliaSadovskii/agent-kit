#!/usr/bin/env python3
"""Mutation testing over the step gate's model.

Every other check in this repository proves the gate does what it is asked. Nothing proves the
*tests* would notice if it stopped. That gap matters more here than anywhere else in the payload:
the gate is what closes a pipeline step, and nothing downstream re-checks its verdict — a gate that
passes a step it should have failed reports success in exactly the voice of success. Elsewhere a
broken script eventually shows up as a broken run; here it shows up as a green pipeline.

So: change `kit_gate.py` in small, mechanical, definitely-wrong ways, and require `tests/test_gate.py`
to go red for each one. A mutant that survives is a hole in the tests, not a fact about the code.

    python3 tests/mutate_gate.py            every mutant, report survivors
    python3 tests/mutate_gate.py --list     name them without running anything

`SURVIVORS` below is the accepted list, and it is checked in both directions: an unlisted survivor
fails the run, and so does a listed one that turns out to be killed now — an allowlist nobody prunes
is an allowlist nobody reads.

Run directly; `scripts/validate.sh` runs it the same way.
"""
import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
# The suite resolves the payload from its own location, so a mutant only takes effect inside a
# copy of the whole repository — and mutating the real file in place would leave it mutated on any
# crash, in a working tree the run is about to commit.
TARGET = os.path.join("plugins", "agent-kit", "scripts", "kit_gate.py")
SUITE = os.path.join("tests", "test_gate.py")

# Mutants nothing can kill, each with the reason it is unkillable rather than untested. A number
# that only bounds a quantity — how long the gate waits, how much output it keeps — has no
# behavioural edge at ±1, and a test written to find one would be a test written against the
# constant it is reading.
SURVIVORS = {
    "<module>:1800→1801": "CHECK_TIMEOUT: ±1 second is not observable in any run short enough to "
                          "be a test",
    "<module>:2000→2001": "STATE_CAP: one character of headroom under a 10,000-character hook cap",
    "branch_of:5→6": "the `git symbolic-ref` timeout; a second either way answers the same",
    "_git:30→31": "the timeout on a `git` read, same reason",
    "now:0→1": "`replace(microsecond=0)`: a timestamp's sub-second precision decides no verdict",
    "_tail:Gt→GtE": "`len(text) > OUTPUT_TAIL` vs `>=`; at exactly the boundary `text[-N:]` is the "
                    "whole string, so the two branches return the same value",
    "_shell:124→125": "the synthetic exit code for a timed-out check; any non-zero fails it, and "
                      "reaching this branch costs CHECK_TIMEOUT seconds",
    "_shell:126→127": "the synthetic exit code for an OSError starting the shell; diagnostic only",
    "_exists_check:1→2": "the failure code of a glob that matched nothing; any non-zero fails",
    "_exists_check:20→21": "how many matching paths are listed in the evidence — a display cap "
                           "with no verdict behind it",
    # The six failure codes a `git:` check can return, in source order. Each one only has to be
    # non-zero — `Evidence.passed` is `exit_code == 0`, and the tests assert the check failed and
    # what it said, which is the part a reader acts on.
    "_git_check:1→2": "`git: tree_clean` when git did not answer; any non-zero fails the check",
    "_git_check:1→2#2": "`git: tree_clean` on a dirty tree, same reason",
    "_git_check:1→2#3": "`git: commits_on_branch` with nothing committed, same reason",
    "_git_check:1→2#4": "`git: pushed` with no upstream, same reason",
    "_git_check:1→2#5": "`git: pushed` when git did not answer, same reason",
    "_git_check:1→2#6": "`git: pushed` with commits ahead of the upstream, same reason",
}

_SWAPS = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
          ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
          ast.In: ast.NotIn, ast.NotIn: ast.In}


class Mutation:
    """One definitely-wrong edit, and the name it is reported and allowlisted under."""

    def __init__(self, key, describe):
        self.key = key
        self.describe = describe


def _enclosing(tree):
    """node -> the name of the function it sits in, or '<module>'."""
    where = {}

    def walk(node, name):
        for child in ast.iter_child_nodes(node):
            inner = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                else name
            where[child] = inner
            walk(child, inner)

    walk(tree, "<module>")
    return where


def _sites(tree):
    """Every mutable node, in a fixed order: source position, so two runs agree."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _SWAPS:
            found.append((node, "compare"))
        elif isinstance(node, ast.BoolOp):
            found.append((node, "boolop"))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            found.append((node, "not"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            found.append((node, "bool"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            found.append((node, "int"))
    return sorted(found, key=lambda pair: (getattr(pair[0], "lineno", 0),
                                           getattr(pair[0], "col_offset", 0), pair[1]))


def _apply(node, kind):
    """Mutate in place and return "before→after"; the tree is a throwaway copy."""
    if kind == "compare":
        before = type(node.ops[0]).__name__
        node.ops[0] = _SWAPS[type(node.ops[0])]()
        return f"{before}→{type(node.ops[0]).__name__}"
    if kind == "boolop":
        before = type(node.op).__name__
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return f"{before}→{type(node.op).__name__}"
    if kind == "not":
        return "not→(dropped)"
    if kind == "bool":
        node.value = not node.value
        return f"{not node.value}→{node.value}"
    node.value += 1
    return f"{node.value - 1}→{node.value}"


def _mutants(source):
    """(Mutation, mutated source) for every site, generated one at a time from a fresh tree.

    The key is the enclosing function, the change, and how many identical changes came before it in
    that function — `Eq→NotEq` happens four times inside one function, and an allowlist keyed by
    something ambiguous silences three mutants nobody looked at. It is deliberately not a line
    number: editing anything above a site would invalidate every entry below it.
    """
    total = len(_sites(ast.parse(source)))
    seen = {}
    for index in range(total):
        tree = ast.parse(source)
        where = _enclosing(tree)
        node, kind = _sites(tree)[index]
        function = where.get(node, "<module>")
        if kind == "not":
            # Dropping `not` means replacing the node, which its parent owns.
            replaced = _drop_not(tree, node)
            if not replaced:
                continue
            change = "not→(dropped)"
        else:
            change = _apply(node, kind)
        ordinal = seen[(function, change)] = seen.get((function, change), 0) + 1
        key = f"{function}:{change}" + (f"#{ordinal}" if ordinal > 1 else "")
        yield Mutation(key, f"{TARGET} {function}(): {change}"), \
            ast.unparse(ast.fix_missing_locations(tree))


def _drop_not(tree, target):
    for parent in ast.walk(tree):
        for field, value in ast.iter_fields(parent):
            if value is target:
                setattr(parent, field, target.operand)
                return True
            if isinstance(value, list):
                for position, item in enumerate(value):
                    if item is target:
                        value[position] = target.operand
                        return True
    return False


def _run_suite(copy):
    """The suite inside one copy of the repository. True when it passes — the mutant survived."""
    environment = dict(os.environ)
    # A stale .pyc is the trap here: two edits of the same length in the same second reuse the
    # cached bytecode, because the cache header is an mtime in whole seconds plus a size. Without
    # this the run reports survivors that were never actually tested.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("CLAUDE_PROJECT_DIR", None)
    environment.pop("KIT_PIPELINES", None)
    # `-f` stops at the first failure: a killed mutant does not need the rest of the suite, and the
    # whole harness is one suite run per mutant.
    done = subprocess.run([sys.executable, os.path.join(copy, SUITE), "-f"], capture_output=True,
                          text=True, cwd=copy, env=environment, timeout=900)
    return done.returncode == 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="name the mutants and stop")
    options = parser.parse_args(argv)

    with open(os.path.join(REPO, TARGET), encoding="utf-8") as handle:
        source = handle.read()
    generated = list(_mutants(source))

    if options.list:
        for mutation, _ in generated:
            print(f"{mutation.key:<44} {mutation.describe}")
        print(f"\n{len(generated)} mutants")
        return 0

    workspace = tempfile.mkdtemp(prefix="kit-mutate-")
    copy = os.path.join(workspace, "repo")
    shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    target = os.path.join(copy, TARGET)
    try:
        # The unmutated file, put through the same unparse. If this is red the harness is broken,
        # not the tests, and every survivor below would be meaningless.
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(ast.unparse(ast.parse(source)))
        if not _run_suite(copy):
            print("ERROR: the suite fails against the unmutated file — the harness cannot judge "
                  "anything", file=sys.stderr)
            return 2

        survivors = []
        for position, (mutation, mutated) in enumerate(generated, 1):
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(mutated)
            alive = _run_suite(copy)
            print(f"[{position}/{len(generated)}] {'SURVIVED' if alive else 'killed  '} "
                  f"{mutation.describe}", flush=True)
            if alive:
                survivors.append(mutation.key)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    unexpected = [key for key in survivors if key not in SURVIVORS]
    stale = [key for key in SURVIVORS if key not in survivors]

    print()
    for key in unexpected:
        print(f"ERROR: mutant survived and is not accounted for: {key}", file=sys.stderr)
    for key in stale:
        print(f"ERROR: {key!r} is listed in SURVIVORS but the tests kill it now — remove the entry",
              file=sys.stderr)
    if unexpected or stale:
        return 1
    print(f"{len(generated) - len(survivors)}/{len(generated)} mutants killed; "
          f"{len(survivors)} accounted for in SURVIVORS.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
