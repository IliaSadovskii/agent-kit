---
name: idea-interview
description: One-time project bootstrap, invoked by ship when .agent-kit/project/manifest.yml is missing or says bootstrapped false — interview the owner, record or generate the core docs, provision scaffolding, and write the manifest.
---

# Idea Interview — project bootstrap

The one-time project gate: it runs when `.agent-kit/project/manifest.yml` is missing or has
`bootstrapped: false`. It surveys the author, makes sure the core docs exist, provisions the
scaffolding the flow needs, and writes the manifest. After it, `ship` can pick features and build
them autonomously.

This covers the whole product, once. A single feature is `brainstorming`; revising the roadmap after
a feature is the `Docs` step of `ship`.

## Two halves, separately runnable

The skill has a technical half and a product half, and `ship` may ask for the technical one alone.

**Setup** — detect the stack, agree the language, generate the coding
standards and `scripts/cloud-setup.sh`, write `.agent-kit/project/manifest.yml` and
`instructions.md`, and record the paths of any documents that already exist. This is what makes the
project runnable at all: without it nobody knows the test command. It is cheap, mostly detection,
and produces no separate pull request — leave `bootstrapped: false` and let the caller commit it.

**Product bootstrap** — everything else: the interview, the core documents, and the bootstrap PR.
This is what makes the kit able to *choose* work rather than only execute it.

Run both when invoked directly or by `ship` with no task in hand. Run Setup alone when `ship` asks
for it, and say in one line what was set up and what is still missing.

## Steps

1. **Detect what exists** — read the manifest if present, scan `docs/`, `README.md`, and the repo
   root for product docs the author already wrote, and establish whether this is a fresh repository
   or one with a real codebase in it. That single fact changes the whole shape of the interview;
   see "Greenfield or existing code" below.
2. **Ask the communication language first.** The manifest does not exist yet, so greet neutrally,
   ask, and use that language for the rest of the interview. It becomes `manifest.language`.
   Generated docs are prose in it; code, paths, and identifiers stay English.
3. **Interview about the gaps only** — see coverage below, and ask per
   `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md`: independent facts — MVP bounds, platform
   constraints, external services — batched into one structured round of up to four questions,
   multiple choice where it fits; decisions that depend on each other one at a time in dependency
   order, so a settled answer can moot the rest of its branch; a recommendation on every question
   that has a sensible default.
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
and a roadmap of what comes next, with a "done when" for each item. Add architecture, product-spec
detail, or domain notes only when the project's complexity calls for them — a tiny utility needs the
idea and a short roadmap, a real app needs more. Ask rather than generating heavy docs
speculatively.

Also worth asking where it affects the plan: MVP bounds, stack and platform constraints, external
services. If the author already has rich docs, this may be one clarifying question and then just
recording paths.

## Greenfield or existing code

Both are normal, and they need opposite interviews. Decide which one you are in before asking
anything, and say which you concluded so the author can correct you in one word.

**A fresh repository.** The author is the only source, so interview for everything: what the product
is, who it is for, what it deliberately will not do, and the phases to get there. Write what they
tell you.

**A repository with a real codebase.** The answers to "what is this" and "how is it built" already
exist in the code, the README, and the commit history. Interviewing for them wastes the author's
time and produces a document that restates what anyone could read — the failure mode here is
ceremony, not missing information.

So invert the flow: read first, then bring a draft. Derive the idea and the architecture summary
from what you found, present them as *"here is what I read this project to be — correct me"*, and
spend the author's attention only on what the code genuinely cannot tell you:

- **Intent** — why it is built this way, and which constraints are deliberate rather than accidental.
- **What is deliberately out of scope** — invisible in code, and the thing an autonomous run most
  needs, because it is what stops the agent from helpfully building the wrong feature.
- **What comes next** — the roadmap. This is the one document that is genuinely missing and genuinely
  required: the `Task` step of `ship` cannot propose work without it. Do not reconstruct a
  retrospective phasing of what already shipped; nobody reads that. Cover only what is ahead.
- **Which conventions are real** — where the existing code is the standard to follow, and where it
  is legacy the author would rather not spread.

An architecture document here describes what *is*, not what is planned, and is worth writing only
when the codebase is large enough that a newcomer would need the map.

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
- **Coding standards** — run `stack-playbook` to generate the document (default
  `docs/coding-standards.md`): stack profile from the dependency manifests, the owner's
  architecture stance per area, the framework's rewarded patterns, the ecosystem library map, and testing
  idioms — researched, not recalled. Register it as `sources.coding_standards` and point the
  project instructions at it.
- **`scripts/cloud-setup.sh`** — the dependency install commands for the detected stack, so hosted
  sessions self-provision. It runs at every session start, so it must check before installing and
  no-op in seconds when everything is already present.
- **`.github/pull_request_template.md`** — propose the sections from
  `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md` and confirm before writing.
- **CI — detect first.** CI is the only verifier that outlives a session, so it gets the same
  treatment as the author's docs. If a workflow already exists, register its path as
  `manifest.sources.ci` and only compare: where the Verification section of the project
  instructions declares a layer the workflow does not run, say so — that is a finding for the
  owner, never an edit. If the repository has no CI, propose a workflow that runs the Verification
  commands verbatim, and write it only on an explicit yes.
- **`README.md`** — only if the repo has none: a one-paragraph pitch, a quickstart, a short tree,
  and an index of `docs/`. A pointer hub, not a restatement of the docs.
- Anything else (`.env.example`, linters) only when the stack clearly calls for it.

Nothing needs to be added to `CLAUDE.md` or `.claude/settings.json`: the plugin brings its own
always-on governance and its own SessionStart hook. Leave both files to the project.

Don't generate a per-project "how this kit works" document — that is the plugin's own README, which
ships with the package. Point the author at it.
