---
name: idea-interview
description: One-time project bootstrap. Use when the project has no .agent-kit/project/manifest.yml or it says bootstrapped false — interview the owner, record or generate the core docs, provision scaffolding, and write the manifest.
---

# Idea Interview — project bootstrap

The one-time project gate: it runs when `.agent-kit/project/manifest.yml` is missing or has
`bootstrapped: false`. It surveys the author, makes sure the core docs exist, provisions the
scaffolding the flow needs, and writes the manifest. After it, `ship` can pick features and build
them autonomously.

This covers the whole product, once. A single feature is `brainstorming`; revising the roadmap
after a feature is the `Docs` step of `ship`.

## Steps

1. **Detect what exists** — read the manifest if present, and scan `docs/`, `README.md`, and the
   repo root for product docs the author already wrote.
2. **Ask the communication language first.** The manifest does not exist yet, so greet neutrally,
   ask, and use that language for the rest of the interview. It becomes `manifest.language`.
   Generated docs are prose in it; code, paths, and identifiers stay English.
3. **Interview, one question at a time**, only about gaps — see coverage below. Multiple choice
   where it fits.
4. **Play back the shape** — the product understanding and the docs and scaffolding you intend to
   create. Adjust on feedback. This is the interactive gate of this skill.
5. **Produce the core docs** — record existing docs by path; generate the missing ones into a
   visible `docs/`.
6. **Provision scaffolding** — see below.
7. **Write the manifest** — `language`, `bootstrapped: true`, `bootstrapped_at`, and `sources`
   pointing at wherever each document actually lives.
8. **Open a bootstrap PR and stop.** Commit docs, scaffolding, and manifest on a
   `bootstrap-<slug>` branch, open the PR, and tell the author to merge it before running `/agent-kit:ship`.
   Don't start a feature on unmerged docs.

**Never relocate the author's content.** If they already have product docs — anywhere, under any
names — record the paths in `sources`. Two parallel copies of the same document is the failure mode.

## What to cover

Always: the product idea (what it is, for whom, the core value, what it deliberately does not do)
and a roadmap with phases and a "done when" for each. Add architecture, product-spec detail, or
domain notes only when the project's complexity calls for them — a tiny utility needs the idea and
a short roadmap, a real app needs more. Ask rather than generating heavy docs speculatively.

Also worth asking where it affects the plan: MVP bounds, stack and platform constraints, external
services. If the author already has rich docs, this may be one clarifying question and then just
recording paths.

## Scaffolding

Offer defaults; ask before overwriting anything that exists.

The project-owned pair is seeded from the plugin's templates. Copy
`${CLAUDE_PLUGIN_ROOT}/templates/project/manifest.yml` and
`${CLAUDE_PLUGIN_ROOT}/templates/project/instructions.md` into `.agent-kit/project/`, then fill them
in — never write into the plugin's own directory, which a plugin update replaces.

- **`.agent-kit/project/instructions.md`** — stack, run and cloud notes, the concrete test / lint /
  migration commands, architectural constraints, and the coding-standards path. Owned by the
  project, so it survives every plugin update. Stack specifics belong here rather than in a forked
  copy of an agent — `tester` and `reviewer` derive their commands from this file and the manifest.
- **Coding standards** — generate one for this stack (default `docs/coding-standards.md`), register
  it as `sources.coding_standards`, and point the project instructions at it.
- **`scripts/cloud-setup.sh`** — the dependency install commands for the detected stack, so hosted
  sessions self-provision.
- **`.github/pull_request_template.md`** — propose the sections from
  `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md` and confirm before writing.
- **`README.md`** — only if the repo has none: a one-paragraph pitch, a quickstart, a short tree,
  and an index of `docs/`. A pointer hub, not a restatement of the docs.
- Anything else (`.env.example`, linters, a CI stub) only when the stack clearly calls for it.

Nothing needs to be added to `CLAUDE.md` or `.claude/settings.json`: the plugin brings its own
always-on governance and its own SessionStart hook. Leave both files to the project.

Don't generate a per-project "how this kit works" document — that is the plugin's own README, which
ships with the package. Point the author at it.
