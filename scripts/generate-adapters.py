#!/usr/bin/env python3
"""Regenerate every provider adapter wrapper in kit/ from catalog.tsv.

The wrappers are deliberately thin: they exist only so Claude Code and Codex can discover the
workflow, skill, or role, and they point at the canonical file under .agent-kit/. Keeping them
generated means adding a workflow is a one-line catalog change instead of five hand-edited files.

Usage:
    scripts/generate-adapters.py           # write the wrappers
    scripts/generate-adapters.py --check   # fail if the payload has drifted (used by CI)
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "kit"
CATALOG = REPO / "catalog.tsv"
WIDTH = 99

COLUMNS = [
    "kind", "name", "title", "claude_desc", "codex_desc",
    "also", "tools", "sandbox", "claude_note", "codex_note",
]


def read_catalog() -> list[dict[str, str]]:
    rows = []
    for lineno, raw in enumerate(CATALOG.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if fields[0] == "kind":  # header row
            continue
        if len(fields) != len(COLUMNS):
            sys.exit(f"catalog.tsv:{lineno}: expected {len(COLUMNS)} columns, got {len(fields)}")
        row = {key: ("" if value == "-" else value.strip()) for key, value in zip(COLUMNS, fields)}
        if row["kind"] not in {"workflow", "skill", "role"}:
            sys.exit(f"catalog.tsv:{lineno}: unknown kind {row['kind']!r}")
        rows.append(row)
    return rows


def paragraph(text: str) -> str:
    """Collapse whitespace and wrap, so descriptions of any length stay tidy.

    Never break on hyphens: every path in these wrappers contains one (`.agent-kit/...`), and a
    wrapped path stops being a path the agent can follow.
    """
    wrapped = textwrap.fill(
        " ".join(text.split()), width=WIDTH, break_on_hyphens=False, break_long_words=False
    )
    return wrapped + "\n"


def frontmatter(**fields: str) -> str:
    body = "".join(f"{key}: {value}\n" for key, value in fields.items() if value)
    return f"---\n{body}---\n"


def workflow_body(row: dict[str, str], provider: str) -> str:
    also = f"`{row['also']}`, " if row["also"] else ""
    args = "`$ARGUMENTS`" if provider == "claude" else "the invocation arguments"
    tail = (
        "The canonical workflow is authoritative; this file is only an adapter."
        if provider == "claude"
        else "This file is only a Codex discovery adapter."
    )
    note = row[f"{provider}_note"]
    return paragraph(
        f"Read `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, "
        f"`.agent-kit/platforms/{provider}.md`, `.agent-kit/workflows/{row['name']}.md`, {also}"
        f"and `.agent-kit/project/manifest.yml` completely. Execute the canonical {row['title']} "
        f"with {args}. {note + ' ' if note else ''}{tail}"
    )


def skill_body(row: dict[str, str], provider: str) -> str:
    refs = " and its canonical references" if row["also"] == "refs" else ""
    note = row[f"{provider}_note"]
    return paragraph(
        f"Read `.agent-kit/skills/{row['name']}.md`{refs} completely and follow it with "
        f"`.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, "
        f"`.agent-kit/project/manifest.yml`, and `.agent-kit/platforms/{provider}.md`. "
        f"{note + ' ' if note else ''}This adapter contains no canonical behavior."
    )


def role_body(row: dict[str, str], provider: str) -> str:
    note = row[f"{provider}_note"]
    return paragraph(
        f"Read `.agent-kit/roles/{row['name']}.md`, `.agent-kit/engine.md`, "
        f"`.agent-kit/project/instructions.md`, `.agent-kit/project/manifest.yml`, and "
        f"`.agent-kit/platforms/{provider}.md` completely, then perform the canonical "
        f"{row['name']} role. {note}"
    )


def build(rows: list[dict[str, str]]) -> dict[str, str]:
    """Return {path relative to kit/: file content} for every generated wrapper."""
    files: dict[str, str] = {}
    workflow_names = {row["name"] for row in rows if row["kind"] == "workflow"}

    for row in rows:
        name, kind = row["name"], row["kind"]

        if kind == "workflow":
            files[f".claude/commands/{name}.md"] = (
                frontmatter(description=row["claude_desc"]) + workflow_body(row, "claude")
            )
            files[f".agents/skills/{name}/SKILL.md"] = (
                frontmatter(name=name, description=row["codex_desc"]) + workflow_body(row, "codex")
            )

        elif kind == "skill":
            files[f".claude/skills/{name}/SKILL.md"] = (
                frontmatter(name=name, description=row["claude_desc"]) + skill_body(row, "claude")
            )
            # A workflow of the same name already owns the Codex discovery path; Codex exposes one
            # skill per name, and the workflow entry point is the one a user invokes.
            if name not in workflow_names:
                files[f".agents/skills/{name}/SKILL.md"] = (
                    frontmatter(name=name, description=row["codex_desc"])
                    + skill_body(row, "codex")
                )

        elif kind == "role":
            files[f".claude/agents/{name}.md"] = (
                frontmatter(name=name, description=row["claude_desc"], tools=row["tools"])
                + role_body(row, "claude")
            )
            toml = [f'name = "{name}"', f'description = "{row["codex_desc"]}"']
            if row["sandbox"]:
                toml.append(f'sandbox_mode = "{row["sandbox"]}"')
            toml.append(f'developer_instructions = """\n{role_body(row, "codex")}"""\n')
            files[f".codex/agents/{name}.toml"] = "\n".join(toml)

    # The payload keeps a minimal kind/name catalog: the in-project validator reads it, and it must
    # not depend on this repository's authoring columns.
    lines = ["# kind name — generated from catalog.tsv; do not edit by hand.", ""]
    for kind in ("workflow", "skill", "role"):
        lines += [f"{kind} {row['name']}" for row in rows if row["kind"] == kind]
        lines.append("")
    files[".agent-kit/catalog.txt"] = "\n".join(lines).rstrip("\n") + "\n"

    return files


def canonical_targets_exist(rows: list[dict[str, str]]) -> list[str]:
    missing = []
    for row in rows:
        folder = {"workflow": "workflows", "skill": "skills", "role": "roles"}[row["kind"]]
        target = KIT / ".agent-kit" / folder / f"{row['name']}.md"
        if not target.is_file():
            missing.append(str(target.relative_to(REPO)))
    return missing


def main() -> int:
    check = "--check" in sys.argv[1:]
    rows = read_catalog()

    missing = canonical_targets_exist(rows)
    if missing:
        print("catalog entries without a canonical file:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    files = build(rows)
    generated_dirs = [".claude/commands", ".claude/skills", ".claude/agents",
                      ".agents/skills", ".codex/agents"]

    # Anything under a generated directory that the catalog no longer produces is stale.
    stale = []
    for folder in generated_dirs:
        base = KIT / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and str(path.relative_to(KIT)) not in files:
                stale.append(path)

    drifted = [rel for rel, content in files.items()
               if not (KIT / rel).is_file() or (KIT / rel).read_text(encoding="utf-8") != content]

    if check:
        for rel in drifted:
            print(f"drifted: kit/{rel}", file=sys.stderr)
        for path in stale:
            print(f"stale:   kit/{path.relative_to(KIT)}", file=sys.stderr)
        if drifted or stale:
            print("\nRun scripts/generate-adapters.py and commit the result.", file=sys.stderr)
            return 1
        print(f"Adapters match catalog.tsv ({len(files)} generated files).")
        return 0

    for rel, content in files.items():
        target = KIT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for path in stale:
        path.unlink()
        print(f"removed stale wrapper: kit/{path.relative_to(KIT)}")

    print(f"Wrote {len(files)} adapter files"
          + (f", removed {len(stale)} stale" if stale else "") + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
