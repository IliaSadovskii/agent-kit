# Kit v1 — decisions taken while rebuilding from scratch

Working notes for the `claude/kit-v1` branch, written 2026-08-01. Everything here is settled unless
it is under "Still open". Nothing about what happens *inside* any command is settled — see the
warning below.

The branch starts from an empty payload: the plugin manifest and five command stubs. Every file the
old kit carried is one `git show main:<path>` away and comes back only where it earns its place.

## Why we are rebuilding rather than editing

Measured on the 0.17.0 run ([0.17.0-measurements.md](0.17.0-measurements.md)):
a feature cost ~27M tokens, of which the review wave was 13M of 19.9M; the `code-review` fan cost
6.7M for 2 findings against `agent-kit:reviewer`'s 0.66M for 12; verification was ~70% of a feature.
The only reliable win of that release was the orchestrator dropping 9× because orientation moved
into a file.

The diagnosis: nearly every expensive mechanism existed to insure the kit against its own autonomy,
and the insurance layers had started to confuse the agents reading them. Four rules in the old text
existed only to serve other rules — the Docs step had to end on the feature branch because the Stop
hook keyed on the branch; each stage had to rewrite the `**Steps:**` line so the previous stage's
guard would not fire; the PR was opened ready and converted to draft by a later stage because a
third-party plugin declines drafts; `--brief` needed fifteen lines to explain the semantics of
copying a sketch.

Autonomy stays, on all four build commands. What goes is the insurance.

## The command set

Six commands, all user-invoked, in three roles. **Knowing** what the project is, **building** from
that, and **checking** the code back against it — the third role was missing until 2026-08-03, and
its absence showed twice: `blueprint` answered a doubt about readiness by building a screenshot
harness, and there was nowhere to put "cover this inherited codebase with tests".

| Command | Role | Purpose |
|---|---|---|
| `blueprint` | know | the project's description: interview, documents, `--check` |
| `fix` | build | something is wrong and it is small |
| `ship` | build | one feature |
| `sprint` | build | a batch of features |
| `mvp` | build | from the blueprint to a running prototype |
| `audit` | check | compare existing code to the description, write a work list — see [audit.md](audit.md) |

The loop is **know → build → check → build**, entered wherever the project already is: an idea, a
half-built skeleton, or a finished application. Every command works with the knowledge missing
except `mvp`, which has no stopping condition without the MVP bounds and the scenarios — the kit
should be learnable from one command rather than from an hour of interview.

- `debug` and `address` are absorbed into `fix` — the first is its opening phase when the cause is
  unknown, the second is `fix --pr <n>`, the same pipeline with a different input source.
- `riff` and `ideate` are dropped outright. Product thinking without a build is a conversation with
  the agent; a command would exist only to carry roadmap machinery.
- `idea-interview`, `stack-playbook`, `docs`, `docs-reflection` and `screens-riff` are absorbed into
  `blueprint`, which becomes the single write point for the project's knowledge.
- `brainstorming` and `writing-plans` collapse into a short step inside `ship`. With detailed
  knowledge written in advance, a feature does not need a nine-step design skill.
- `screens` is deferred. The map's current format is not good enough to carry over; it is
  reconsidered, much simplified, after blueprint exists.

**The internals of all five are undecided.** Ship's eleven steps in particular are considered
excessive and get reviewed from nothing rather than trimmed. No step list here is a commitment.

## Removed, with the reason

- **The `Stop` hook.** It checked that a step had *a line* in the Run log — a line the agent writes
  itself, so the guarantee was zero. It also keyed on the branch name, so any conversation held
  while a feature branch was checked out was treated as that feature's pipeline and blocked
  (defect P4, hit a live analysis session). What it was reaching for is done from outside instead:
  whatever drives the stages checks the child's exit and its recorded state.
- **The sprint watchdog.** Three headless levels (watchdog → orchestrator → stage) made progress
  unobservable, which is what stopped the last run (P6). In the measured run it never once
  recovered correctly: it slept 86100s on a stale rate-limit notice (P1) and was ready to launch a
  second orchestrator on top of a live one, because liveness was measured by a log written only at
  exit (P2).
- **`interactive-mode` and `--manual`.** Every command is autonomous after its approval gate.
- **Three of the four "documents against code" passes.** `brainstorming`, `ideate`,
  `docs-reflection` and the playbook freshness check each re-derived whether the documentation was
  still true. One remains: `blueprint --check`.
- **Review levels beyond the first.** The `code-review` fan on every feature, the
  `pr-review-toolkit` specialists, `/simplify` in the pipeline, and the re-review of the fix diff.
  This stacking is what produced thirty findings and then twenty more — overlapping reviewers on one
  diff generate noise, and the noise is paid for twice, once in the review and once in the fixes.
- **The depth dial in three places** (`--deep/--quick`, `depth` in the queue, the Depth section of
  `brainstorming`) — at most one word in a spec.
- **The two gates in `ship`.** No manifest means run `blueprint`.
- **The hand-written YAML reader.** See the format policy below.

## Hooks

A hook is the only mechanism an agent cannot ignore, so it is justified exactly where a violation
is expensive and prose is unreliable. Two rules:

1. Every hook must be a no-op unless a kit run is actually in progress. A hook that fires on
   unrelated conversations is a tax, and taxes get routed around. This is what P4 was.
2. Anything a prompt can enforce reliably stays a prompt.

Two hooks survive:

- **PreToolUse (Bash)** — refuses `gh pr merge`, force pushes, and pushes to the default branch.
  Irreversible, genuinely forgotten by a long context, and it costs nothing: it runs outside the
  model's context. Moves over from `main` essentially unchanged.
- **PreCompact** — prints one line telling the run to re-read its run file before continuing.
  Compaction is precisely where a long autonomous run loses the thread.

Rejected: `SessionStart` injecting always-on rules (a per-session token tax on unrelated
conversations — and the rules that must always hold are enforced mechanically by the guard instead),
`SessionStart` running a cloud setup script (the environment is a running Docker container before
the kit starts), `PostToolUse` staleness marking (computed on demand by `--check`),
`UserPromptSubmit` (same tax), `Notification` (only pays off where permission prompts happen, and
runs are in bypass mode), `SubagentStop`/`SessionEnd` (the transcripts and exit codes already say
it), and the `Stop` hook above.

## Formats

**A script reads it — JSON. A person reads it — YAML.** This is what removes the need for the
stdlib YAML reader the old kit wrote and had to test: `python3 -c 'import json'` is the whole
parser.

## Run state

One recursive shape, one directory:

```
.agent-kit/runs/<slug>/
  run.json     # the same shape for fix, ship, sprint and mvp
  run.log      # append-only, written by the driver and the hooks, never by the agent
```

A sprint's `run.json` differs from a feature's only in having `children` filled — the slugs of its
child runs, each with a directory of the same shape. An `mvp` carries sprints in `children`. A
`fix` carries none and leaves most fields empty. There is no separate queue file: the queue is
`children` plus the status and dependency fields inside them.

The key is a slug, not a branch: a sprint has no branch of its own until integration, and the
branch is a field inside. Finding a run by branch is one grep across a handful of files.

This replaces the old `handoff.yml` + `queue.yml` + Run-log-inside-the-plan + `upstream.md`, which
is where context was being lost between stages.

`run.log` is the answer to "is it still working?" — one line per transition plus the children's
output, tailable. The old kit answered that question with `ps`, transcript mtimes and four
different logs.

## Non-prompt files

Nothing below is created until the command that needs it is being built. An empty file is a
promise, not a decision, and a registered hook that does nothing looks like protection.

**Ships with the plugin**

| File | Format | Purpose |
|---|---|---|
| `.claude-plugin/plugin.json` | JSON | plugin manifest |
| `hooks/hooks.json` | JSON | hook registration |
| `scripts/guard.py`, `guard.sh` | python3 stdlib, sh | the PreToolUse guard |
| `scripts/precompact.sh` | sh | the PreCompact reminder |
| `scripts/orchestrate.py` | python3 stdlib | conditional — only if `sprint` drives its stages from a script |
| `templates/project.yml` | YAML | the shape of the project manifest blueprint writes |
| `templates/run.json` | JSON | the shape of a run file |

**Written into the project**

| File | Format | Purpose |
|---|---|---|
| `.agent-kit/project.yml` | YAML | language, the project's commands, paths to the blueprint documents |
| `.agent-kit/runs/<slug>/run.json` | JSON | run state |
| `.agent-kit/runs/<slug>/run.log` | text | run trace |

**Repository infrastructure, never shipped**

| File | Purpose |
|---|---|
| `scripts/validate.sh` | manifests, frontmatter, structure; run locally and in CI |
| `tests/` | that the kit's scripts do what they claim |

## Build order

`blueprint` → `fix` → `ship` → `sprint` → `mvp`.

Blueprint first because the other three build commands read what it writes: starting elsewhere means
inventing a placeholder for knowledge and reworking it later. It is also useful alone — running it
on a real project before any other command exists produces documentation, and that first run is the
evidence for whether the slots are right, before four commands depend on them.

Then `fix`, the smallest builder, where the shared bones are cheapest to settle: the run file, the
branch and PR handling, verification, the single review pass. Getting them wrong there costs one
command instead of four. `ship` adds design-from-blueprint and the autonomous phase; `sprint` is
`ship` in a loop plus integration; `mvp` is `sprint` in a loop and introduces nothing below itself.

Each command lands usable on its own.

## Where it stands, 2026-08-04

| Command | State |
|---|---|
| `blueprint` | written, two live runs; second cost 2.0M against the first's 24M |
| `ship` | written, run inside two sprints |
| `audit` | written, six lenses, each run once on a real project (tests four times); 21.4M for the whole sweep |
| `sprint` | written with its driver; two live batches — a tests lens and a security one |
| `next` | written 2026-08-05, three live runs, each of which corrected a rule |
| `fix` | written 2026-08-05, **never run** |
| `mvp` | stub |

How a command is written and hardened is in [method.md](method.md) — eleven corrections paid for
with live runs, which `fix` and `mvp` should not pay for again. `sprint`'s reasoning, and the third
of its first design that a review deleted, are in [sprint.md](sprint.md).

The build order settled at **`sprint` → `mvp` → `fix`**, not the one below: the shared bones `fix`
was meant to settle are already live in `ship`, so `fix` became the smallest command rather than the
foundational one.

**Untested paths in `audit`**, all of them invocation rather than lens: a full run with no argument
(delegation per lens, cheapest-first ordering, per-lens commits), a repeat run without deleting the
file (reading the previous one, leaving declined items alone), narrowing by area, and free text. Also
untested anywhere: a project with a thin `stack.md`, and any stack other than Laravel.

## Still open

- ~~**What drives a sprint's stages.**~~ Decided 2026-08-04: a script driver, no orchestrating
  agent, one visible session per feature. The reasoning, the question protocol and the limit
  handling are in [sprint.md](sprint.md).
- **How `mvp` knows it is finished.** "Until the agent decides it works" has no anchor and either
  stops early or never stops. The intended anchor is blueprint's `mvp_bounds` (an explicit in-list
  and out-list) plus its scenarios walking end to end against the running app. Also settled in
  principle: `mvp` composes batches and owns no build, test or PR logic of its own — it calls
  `sprint`, which calls `ship`. And on an empty project the first batch is a skeleton that starts
  and serves something, not a feature.
- **Screens.** Deferred, to be reconsidered in a much simpler form once blueprint exists.
- ~~**Five of `audit`'s seven lenses.**~~ Closed: six lenses are written and each has run once. The
  reasoning for each, and the two that were rejected, is in [audit.md](audit.md).
- **What blueprint asks and writes.** Settled and shipped in 0.18.0; the templates under
  `plugins/agent-kit/templates/knowledge/` are the catalogue. It came from a larger design that was
  mostly rejected (`docs/design/knowledge-and-gates.md`, deleted — see the history of this branch).
  Kept from it: the slots themselves, actors
  rather than roles, the fixed entry shape for an action, the readiness criterion ("can an
  implementer act on this without asking?"), the three statuses (`filled`, `not_applicable`,
  `open_question`) that stop a slot being filled with invention, the story pass, writing after each
  slot, and tagging a run's assumptions back to the slot they stood in for. Dropped from it: the
  derived index, the anchors in the owner's prose, the per-entry graders with hash caching, the step
  gate, `pipelines.yml`, and the write-protected run state — because blueprint now owns the format
  of the documents it writes, so the structure *is* the index.
