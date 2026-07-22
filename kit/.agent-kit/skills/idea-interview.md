# Idea Interview — Project Bootstrap

> **LANGUAGE:** the manifest may not exist yet, so the user's language is unknown. Ask it
> as the FIRST question (see below), then communicate in it for the rest of the interview.
> Until then, greet neutrally. These skill instructions are in English; generated core docs
> are prose in the user's language; code/paths/identifiers are in English.

Bootstrap a project from a bare idea to "ready for the autonomous flow". This is the
**one-time project-level gate**: it runs when `.agent-kit/project/manifest.yml` is missing or has
`bootstrapped: false`. It surveys the author, ensures the core docs exist (recording the
author's own docs if they already wrote them, generating the rest), provisions the project
scaffolding, and writes the manifest. After it, `ship` can pick features and build them
autonomously.

<SCOPE>
This skill is about the WHOLE product (once). It is NOT about a single feature — that is
`brainstorming` (runs every feature). And it is NOT about revising the roadmap after a
feature — that is the `Docs` step of `ship`. Three different things, do not conflate them.
</SCOPE>

<NEVER-MOVE-USER-DOCS>
If the author already has product docs (anywhere, any names), DO NOT move or duplicate them.
Record their paths in the manifest's `sources`. Generate only what is genuinely missing, into
`docs/` (visible, user-facing — never hidden in `.agent-kit/`). Two parallel copies of the same
doc is the failure mode we are avoiding.
</NEVER-MOVE-USER-DOCS>

## Checklist

Create a task per item and complete in order:

1. **Detect current state** — read `.agent-kit/project/manifest.yml` if present; scan the repo (`docs/`,
   `README.md`, root) for any existing product docs the author already wrote. Decide what is
   already there vs missing.
2. **Ask the communication language** — the very first question: what language should the agent
   talk to you in? This value goes into `manifest.language`.
3. **Interview the author** — one question at a time (multiple choice preferred), only about
   gaps. Cover the adaptive minimum below, plus whatever the project needs.
4. **Confirm the shape** — briefly play back the product understanding and the planned docs/
   scaffolding; adjust on feedback. This is the interactive gate of this skill.
5. **Produce the core docs** — record existing docs by path; generate missing ones into `docs/`
   (in the user's language). Do not move/duplicate the author's docs.
6. **Provision scaffolding** — set up the supporting files the flow needs (see below), adaptively.
7. **Write the manifest** — `.agent-kit/project/manifest.yml`: `language`, `bootstrapped: true`,
   `bootstrapped_at`, and `sources` pointing at wherever each doc actually lives.
8. **Bootstrap PR + stop** — commit docs + scaffolding + manifest on a branch using the active
   provider prefix and a `bootstrap-<slug>` suffix
   branch (planning, not feature code), open a PR, and STOP: tell the author to merge it and run
   Ship again for the first feature using the active provider invocation. Do NOT start building a
   feature on unmerged docs.

## Adaptive minimum

There is a firm core, the rest is by need — do not over-produce for a small project:

- **Always:** product idea (what the app is, for whom, the key value, what we do NOT do) and a
  **roadmap** with clear phases and a "done when" per phase.
- **If the project warrants it:** architecture (stack, layers, key decisions), product-spec
  detail, domain notes. Add these only when complexity or the author's answers call for them.

Judge adaptively: a tiny utility needs idea + a short roadmap; a real app needs architecture too.
When unsure, ask the author rather than generating heavy docs speculatively.

## Interview coverage (fill gaps only)

Ask, one at a time, until the adaptive minimum is solid:

- **Language:** communication language (first question).
- **Idea:** what the product is, what problem it solves, for whom, the core value.
- **MVP bounds:** what's in the first version, what we deliberately do NOT do.
- **Roadmap:** the major phases in a logical order; a "done when" criterion for each.
- **Stack / constraints:** technologies, platforms, external services (if they affect the plan).
- **Architecture (if needed):** the key layers/decisions that frame the features.

Keep it proportional: for a bare idea this is a real survey; if the author already has rich docs,
it may be one or two clarifying questions, then just record paths.

## Provision scaffolding

Once the stack/architecture is understood, set up the supporting files the flow relies on —
adaptively, only what fits the project. Offer sensible defaults, ask before overwriting anything
the author already has.

- **Shared project instructions** — fill `.agent-kit/project/instructions.md` from the interview: stack,
  cloud/run notes, concrete test/lint/migration commands, architectural constraints, and the
  coding-standards path. It is user-owned and survives kit updates.
- **Provider roots** — preserve the adapter bootstrap in `CLAUDE.md` and `AGENTS.md`. Put only
  provider-specific user overrides there; do not duplicate shared project rules from
  `.agent-kit/project/instructions.md`.
- **Coding standards doc** — generate a visible coding-standards document for this stack (default
  `docs/coding-standards.md`), register it as `sources.coding_standards`, and point
  `.agent-kit/project/instructions.md` to it.
- **Roles consume project configuration** — do not fork canonical roles per stack. Ensure tester
  and reviewers can derive exact commands and conventions from `.agent-kit/project/instructions.md`, the
  manifest sources, and existing project config. Put stack specifics in the shared project file.
- **Explainer** — do NOT generate a per-project "how it works" doc. The system is explained once,
  statically, in `.agent-kit/GUIDE.md` (English, ships with the package). Just point the user there.
  If they want it in their language, offer to translate it once on request — it's not part of the
  bootstrap.
- **Starter README** (`README.md` at repo root) — if the repo has none, generate a thin landing:
  a one-paragraph pitch, a quickstart command, a short repo tree, and an index of the `docs/`
  files. Keep it a pointer hub — do NOT restate the stack/principles/commands that live in the
  docs. If a README already exists, don't clobber it.
- **PR template** (`.github/pull_request_template.md`) — propose a default (What & why /
  Architecture / Patterns / Changes / Testing / Review / Assumptions / checklist) and ask if the
  author wants changes; then write it.
- **Setup/bootstrap script** (`scripts/cloud-setup.sh` or equivalent) — generate the dependency
  install commands for the known stack (`composer install`, `npm install`, `pip install`, `go mod
  download`, … — whatever fits), so cloud sessions self-provision.
- **Other config as needed** — `.env.example`, editorconfig/linters, CI stub — only when the
  stack clearly calls for it. Don't scaffold speculatively.

If a file already exists, don't clobber it — surface it and ask.

## After the interview

- Generated docs go to `docs/` (in the user's language, matching the project's existing doc style).
- The manifest is the single source of indirection — every generated/recorded doc gets a `sources`
  entry so the rest of the system reads paths from it, never hardcoded — and `language` is recorded.
- Open the bootstrap PR, then hand back to the author. The first feature starts with a fresh Ship
  invocation on the active provider.

## Key principles

- **Ask the language first** — everything after is in the user's language.
- **One question at a time** — don't overwhelm.
- **Adaptive, not maximal** — the minimum core always, heavy docs only by need (YAGNI).
- **Never relocate user content** — only record paths.
- **Interactive gate** — the interview runs with the author; it's this skill's only manual checkpoint.
