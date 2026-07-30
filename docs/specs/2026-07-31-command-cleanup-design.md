# Command cleanup — nine commands become six

Expanded from the owner-approved brief at
`.agent-kit/sprint/2026-07-31-knowledge-and-gates/01-command-cleanup/spec.md`, stage 0 of
`docs/design/knowledge-and-gates.md`. Depth: light. Run under `--brief`, so this expansion settles
what the brief left open and records nothing the brief already decided.

## What ships

Three command entry points disappear and nothing they do disappears with them:

| Was | Is now |
|---|---|
| `debug` as a command | the `debug` skill, invoked by `fix` when the cause is unknown |
| `address` as a command | the `address` skill, invoked by `fix --pr <n>` |
| `screens-riff` as a command | the `screens-riff` skill, invoked by `riff` on a screen theme |

`fix` widens from "the light path for a small change" to the design's own framing: *something is
wrong — your words, a PR review, or an observed failure.*

## The mechanism

A skill in `plugins/agent-kit/skills/` is a user-facing command exactly when its frontmatter carries
`disable-model-invocation: true`. Removing that line (and `argument-hint`, which only a slash
command reads) makes the skill model-invocable and invisible in the command list, which is precisely
"absorbed, not deleted". The `description` is then rewritten in the shape the six existing internal
skills already use — "what it does. Invoked by X when Y" — because for an internal skill the
description is the routing signal rather than a menu row.

Bodies keep their procedures whole. This is a re-wiring, not a rewrite.

## Decisions this expansion settles

The brief left three things to the run, plus two the exploration turned up.

**How `fix` decides the cause is unknown.** The model's judgment from the task text, no new flag. A
task that names the change (`the footer link points at /docs`) is fix's own path; a task that names
only a symptom (`the export button does nothing on Safari`) runs `debug` first. `debug`'s step 4
already ends by continuing through the tail of `fix`, so the two skills already fit without either
of them changing.

**How `riff` recognises a screen theme.** The same standalone `S<digits>` token grammar `ship`
documents under "Screen references" — `S7`, not `S7Adapter` — or an explicit mention of screens, the
map, or a flow's screens. `riff` is interactive, so a genuinely ambiguous theme is asked about in
the one message `riff` already sends when no theme was given, never guessed.

**`$ARGUMENTS` in a skill that is no longer a command.** `$ARGUMENTS` is substituted for a slash
command; a model-invoked skill sees it literally. `ideate` — internal since before this change —
already carries one, so the precedent is that this is tolerable, but it is still a line that reads
as a hole. Each of the three gets one clause naming the caller as the other source of its input
(`… or the failure `fix` handed you`). One clause each, procedures untouched.

**The screens-riff comparison table.** `screens-riff`'s body opens with a table of the three
commands that touch the map, and two of its rows are now the same command. Rows become
`/agent-kit:riff` *on a screen theme* and `/agent-kit:riff` *on anything else*, which is the honest
description of what the owner now types, and the sentence under it stops contrasting "this command"
with `riff`.

**What `validate.sh` gains.** The brief asks for the dead-command grep, and the general form of it
is stronger than a grep for three names: every `/agent-kit:<name>` written in the shipped payload or
in either README must be a skill whose frontmatter still marks it user-facing. That scope is the
whole rule — `CHANGELOG.md`, `migrations/`, and the documents under `docs/` are records of a moment
and name removed commands on purpose. Five more features in this batch pass over these files, so a
check that catches *any* stale command reference is worth more than one that catches these three.

The existing allowlist of internal skills in the README cross-check gains the three names, as the
brief specifies. It stays a hand-maintained list rather than being derived from frontmatter: the
brief settled the mechanism, and the new check above already covers the direction that matters.

The Test step added five more assertions to the same block, on the same reasoning — six features
stack on this branch and they all edit these files. The root `README.md` must document every
command, and its prose command count must match the frontmatter; `argument-hint` may not survive on
a skill that is no longer a command, nor be missing from a command whose body reads `$ARGUMENTS`; an
internal skill's description must name the skill that invokes it, and that skill's body must
actually reference it back. The last one is the load-bearing one: it is what would catch a later
feature rewriting `fix` or `riff` and dropping a routing paragraph, which would leave a working
skill that nothing reaches — a failure no other check here can see.

## Out

`docs` is untouched — it is absorbed into `blueprint --check` at stage 7, and removing it now would
drop the capability for six stages. `riff` itself survives; its fate is decided later on evidence.
No behavior inside the three moved skills changes. `VERSION`, `plugin.json`, and `marketplace.json`
are not bumped: the release commit is the owner's, after the batch's integration PR merges.

## Verification

`scripts/validate.sh` is the whole declared suite and the mechanical gate: frontmatter, the
README ↔ skill cross-check in both directions, dangling `${CLAUDE_PLUGIN_ROOT}` references, the
`engine.md` 10,000-character cap, and now stale command references. It must be green, and the new
check must be shown to fail against a deliberately stale reference before it is trusted.

There is no runnable surface — the payload is documentation-shaped and its "execution" is a Claude
Code session reading it — so no app is started. No heavier layer is earned: there is no branching
logic for mutation or property testing to bite on, and the behavior under change is which files
carry which frontmatter keys, which is exactly what the validator reads.
