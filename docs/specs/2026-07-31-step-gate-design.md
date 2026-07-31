# Step gate — design

Stage 3 of `docs/design/knowledge-and-gates.md`. Expanded from the owner-approved sketch at
`.agent-kit/sprint/2026-07-31-knowledge-and-gates/04-step-gate/spec.md`, read together with the
`upstream.md` beside it.

## Goal

A step is closed by the **gate**, never by the agent. The agent asks; the gate runs the criteria and
writes the verdict; run state lives where the agent cannot write it.

This closes both holes named in section 1 of the design: a step that settles itself, and `skipped:
<any reason>` as a universal exit.

## What ships

| Path | What |
|---|---|
| `plugins/agent-kit/pipelines.default.yml` | the plugin's default pipeline definitions — ordered steps, `requires`, `done_when`, `max_attempts`, `on_exhausted`, `optional`, `skippable_when` |
| `plugins/agent-kit/scripts/kit_gate.py` | the model: pipeline definitions, run state, checks, step transitions. Imported by the CLI and by the hooks |
| `plugins/agent-kit/scripts/gate.py` | the CLI the agent calls: `step start`, `step settle`, `step skip`, `state`, `run reset` |
| `plugins/agent-kit/scripts/write-guard.py` / `.sh` | new `PreToolUse: Write\|Edit\|MultiEdit\|NotebookEdit` hook refusing writes to `.agent-kit/runs/**` |
| `plugins/agent-kit/scripts/guard.py` | the Bash guard, extended with the same refusal |
| `plugins/agent-kit/scripts/stop-guard.py` | rewritten onto run state |
| `plugins/agent-kit/scripts/session-start.sh` | appends the branch's unfinished run state after `engine.md` |
| `.agent-kit/runs/<slug>.yml` | run state. Written by the gate and by nothing else; gitignored |

Prose: `skills/ship/SKILL.md`, `skills/fix/SKILL.md`, `skills/sprint/SKILL.md`,
`skills/writing-plans/SKILL.md`.

Out, as the sketch says: the project-owned `pipelines.yml` and the `commands:` block (stage 4),
`limits.wall_clock` (stage 4), grader-backed `agent:` checks.

## Run state

`.agent-kit/runs/<slug>.yml`, where `<slug>` is the branch with every character outside
`[A-Za-z0-9._-]` replaced by `-`. The full branch name is recorded inside the file and verified on
every read, so `claude/foo-bar` and `claude-foo/bar` cannot silently share one file: a state file
whose `branch:` disagrees with the checked-out branch is not this branch's run.

```yaml
version: 1
branch: claude/step-gate
pipeline: ship
session: 44608e54-ff5f-41b5-9ef6-0ae14aeb96ef
state: open                     # open | finished | blocked
opened_at: '2026-07-31T09:14:02Z'
opened_at_commit: 91d1109…      # HEAD when the run opened
steps:
  - name: Design
    verdict: attested           # open | verified | attested | skipped | blocked
    attempts: 1
    opened_at: '…'
    settled_at: '…'
    evidence: 'expanded the brief into docs/specs/2026-07-31-step-gate-design.md'
  - name: Build
    verdict: open
    attempts: 2
    opened_at: '…'
    history:
      - attempt: 1
        check: 'run: scripts/validate.sh'
        command: scripts/validate.sh
        exit: 1
        output: '…tail…'
        at: '…'
```

Written atomically — rendered with `kit_yaml.dump()`, written to a sibling temporary file and
`os.replace`d — because two sessions share one working tree during a sprint and a half-written state
file is indistinguishable from a corrupt one. Both the `.agent-kit/runs` directory and the file go
through `kit_knowledge.kit_owned()`, which refuses a symlink at a path the kit fixed by name.

### The owner field — why run state is not keyed by branch alone

`upstream.md` records the defect this feature exists to absorb: a sprint orchestrator and its
headless child share one working tree, the child checks that tree out onto its own branch, and the
old `Stop` guard read the child's plan as the orchestrator's unfinished run — demanding, every turn,
the exact action the sprint contract forbids the orchestrator to take.

Keying run state by branch alone moves that defect into the new mechanism unchanged. So the run
records the **session that opened it**:

- `gate.py` reads `CLAUDE_CODE_SESSION_ID`, else `AGENT_KIT_SESSION_ID`, at the moment the run opens.
  The harness's own variable comes first because the agent can set the other one, and a bogus owner
  would silence the `Stop` hook for the rest of the run in a single command.
- The `Stop` hook payload carries `session_id`. It holds the turn only when the run's `session` is
  unset **or** equal to the stopping session's id.

Unset holds, so an ordinary single-session repository behaves exactly as it does today. `sprint`
launches its child with `AGENT_KIT_SESSION_ID` set to the same uuid it passes as `--session-id`, so
under a sprint the owner is correct by construction rather than by an environment variable's good
behaviour.

## The pipeline definition

`plugins/agent-kit/pipelines.default.yml` describes the current behaviour of `ship` and `fix`
explicitly. Until stage 4 adds the project-owned override this file is the only source, and a
project that never writes one keeps working forever.

```yaml
pipelines:
  ship:
    steps:
      - name: PR
        requires: [Security]
        done_when:
          - git: tree_clean
          - git: pushed
        max_attempts: 2
        on_exhausted: block
        skippable_when: [no_remote]
```

A step does not open until **every step before it in the list** holds a terminal verdict. `requires:`
names the same predecessor explicitly, so that a project editing this file in stage 4 can read the
dependency without inferring it from position, and it is checked when the file is read — it must
name an earlier step, which catches a typo or a forward reference. It is not a second gate at run
time: it could never fire, because the order rule already covers every earlier step.

### Check kinds

| Kind | Passes when |
|---|---|
| `run: <shell command>` | exit 0. Printed before it runs, and refused outright when `guard.refusal()` covers it |
| `exists: <glob>` | the glob matches at least one file inside the project |
| `git: tree_clean` | `git status --porcelain` is empty |
| `git: commits_on_branch` | at least one commit since `opened_at_commit` |
| `git: pushed` | the branch has an upstream and nothing is ahead of it |

`approved_by_owner:` and `agent:` are in the schema and **declared unsupported**: the gate names them
and exits 2 rather than passing them silently. `on_exhausted: escalate` is the same — `block` and
`continue` are supported, `escalate` needs a push channel this stage does not have.

`git: commits_on_branch` counts against the commit HEAD pointed at when the run opened, not against
the default branch. On a stacked feature branch — every feature in this sprint — the default-branch
comparison would count the parent feature's commits and pass a step that produced nothing.

### Attempts

`settle` increments `attempts` on failure and records the attempt in `history`. When `attempts`
reaches `max_attempts` the step is recorded `blocked` with every attempt kept, and `on_exhausted`
decides what happens to the run: `block` marks the whole run `blocked`, `continue` leaves it open so
the agent carries on and reports the step in the PR.

A run that is `blocked` or `finished` releases the `Stop` hook. A gate that can deadlock a run has
replaced one failure mode with a worse one, so a blocked run is a run the agent may end.

## Verdicts

| Verdict | Means |
|---|---|
| `verified` | every `done_when` check ran and passed. Evidence is the check list with commands, exit codes and output tails |
| `attested` | the step declares no checks. `settle --evidence "<text>"` is **required**, and an empty string is refused |
| `skipped` | `step skip --reason <name>`, where the step is `optional: true` or `<name>` is one of its `skippable_when` conditions |
| `blocked` | attempts exhausted |

All four are terminal. `open` is not. The gate is honest about what it guarantees: Design, Plan,
Test, Review, Security and Docs are attested today and become verified when a check is added in
YAML — which is exactly what stage 4's `commands:` block makes possible for Test.

Named skips replace the free-text `skipped: <any reason>` that closes any step today. A step that is
neither `optional` nor carries a matching `skippable_when` cannot be skipped at all.

## Hooks

| Hook | Behaviour |
|---|---|
| `PreToolUse: Write\|Edit` | **new.** `deny` on any path containing the `.agent-kit/runs` segment |
| `PreToolUse: Bash` | the existing guard, plus `deny` on any command naming `.agent-kit/runs` that is not an invocation of `gate.py` |
| `Stop` | reads run state, not markdown. Holds the turn while the run is `open` and a declared step lacks a terminal verdict |
| `SessionStart` | prints the branch's unfinished run state after `engine.md` |

The decision is `deny`, not `ask`. The existing guard asks because a human is usually there; a
headless sprint child has nobody to answer, and a hanging child is worse than a refused write.

`refusal()` gains the run-state rule rather than the hook gaining it privately, because the same
decision has three callers now: the hook, `blueprint_check.py` running a contract's declared
commands, and this gate running a pipeline's `run:` checks. A pipeline definition becomes
project-owned in stage 4; the gate that will execute it is written here, so every `run:` invocation
goes through `refusal()` from the start. `refusal()` therefore returns a `Refusal(decision, reason)`
— `deny` for run state, `ask` for the never-rules that were there before — and its one existing
caller reads `.reason`.

Every hook fails open on a parse error, as `stop-guard.py` already does. Unreadable state means there
is no run: the agent carries on and records the fact in the Run log.

The Bash rule is blunt on purpose. A shell command that names `.agent-kit/runs` and is not the gate
is refused, full stop — reading state is what the Read tool is for, and a precise rule about
redirects, `tee`, `sed -i` and `cp` targets would leak. The refusal text names the one escape hatch
a human has: delete the file yourself if a run was abandoned.

### The session-start addition

`gate.py state` prints nothing when there is no run for this branch, and otherwise the open step,
every step's verdict, and the attempt history of the open step. Its output is hard-capped at 2,000
characters. Claude Code caps a hook's whole output at 10,000, past which it is written to a file and
replaced with a preview — so the governance would silently stop being always-on. `validate.sh`
already checks `engine.md` against 10,000; it now checks it against 10,000 minus that cap, and a test
asserts the cap holds against a deliberately enormous state file.

## Where the run opens

The gate opens a run at the **first `step start`**, and both pipelines are careful about where that
is:

- `ship` opens at **Design**. Task and Ideate can end with the owner declining; a run opened for work
  that never starts is a guard nobody can satisfy.
- `fix` opens at **Change**. Before that the path may still turn out to be `address` (which owns its
  run end to end and is not gated here), `debug` stopping with a diagnosis for the owner, or a
  handoff to `ship`.

`Stop` nudges once per turn — `stop_hook_active` short-circuits, as it does today — so an abandoned
run costs one message per turn, not a wedged session.

## `sprint`

The sketch's scope line names `sprint` among the pipelines the default file describes. It is not
described there, and this is a recorded deviation.

The orchestrator checks the working tree out onto each child's branch as it goes. Run state is keyed
by branch, so an orchestrator run opened on `main` is invisible to its own `Stop` hook for most of
the sprint and visible again between features. An intermittent guard is worse than none: it reads as
assurance and is not. `ship` and `fix` are gated; the orchestrator of gated runs is not.

What `sprint` does change:

- Its completion check moves off the plan's Run log and onto the child's
  `.agent-kit/runs/<slug>.yml` — the same question, *which step is the first unsettled one*, asked of
  the file that now holds the answer. The `--resume <session>` path is unchanged, and it is
  load-bearing: it is what finished `03` after a session limit.
- It exports `AGENT_KIT_SESSION_ID` alongside `--session-id` when it launches a child.

## The Run log

The `**Steps:**` machine header leaves the Run log: the step list has a machine home now. `**Branch:**`
stays as human context.

The agent still writes one settle line per step, after the gate returns success and carrying the
gate's verdict — `- step Test — verified: scripts/validate.sh → 0`. Nothing parses it any more, but
run state is gitignored, so without those lines the pull request would carry no record of the steps
at all.

## Verification

The plugin runs from `~/.claude/plugins/cache/agent-kit/agent-kit/<version>/`, not from this working
tree, so nothing changed here takes effect until someone runs `claude plugin update`. That is what
makes it safe to rewrite the `Stop` hook mid-sprint, and it is also why the hooks cannot be exercised
end to end in this run.

- **Hook tests driven by crafted JSON on stdin**, one per hook, covering the allow, the deny and the
  malformed-input fail-open path. This is the verification, not a lesser substitute for it.
- **Property-based tests on the state machine**: over pseudo-random sequences of `start` / `settle` /
  `skip`, a step never leaves a terminal verdict, `attempts` never exceeds `max_attempts`, and order
  is never violated. Seeded from a fixed list of seeds so a failure is reproducible.
- **Mutation testing over `kit_gate.py`**, wired into `scripts/validate.sh`. The gate is the one
  piece of this batch whose tests passing while the code is wrong would be invisible, because nothing
  downstream checks it.
- Fixture projects under `tests/fixtures/gate-*/`, each with its own `pipelines.default.yml`, follow
  the pattern the knowledge tests established.
- No runnable app surface: the kit is skills, hooks and scripts. `scripts/validate.sh` is the whole
  declared suite and stays green.

## What the security pass changed

The gate executes shell from a YAML file and writes a file inside the project, so the review was
where most of the design's real edges turned up. Every finding below was reproduced before it was
fixed.

- **The atomic write's temporary file was not a kit-owned path.** `state_path()` refuses a symlink
  at `.agent-kit/runs` and at `<slug>.yml`; `<slug>.yml.kit-new` was neither, and `os.replace` then
  moved the link onto the checked path. A pull request could ship that link and the run's first
  `step start` would write through it. Both it and the directory's own `.gitignore` are now opened
  with `O_NOFOLLOW` — and `.gitignore` with `O_EXCL` and `lexists`, because a *dangling* link reads
  as absent and the write creates its target.
- **`KIT_PIPELINES` is a seam the agent can also reach.** A forged definition with `done_when: []`
  settles a real step without running anything. The seam stays, because the tests need a pipeline
  that fails on purpose — but every write now stamps the override into the run, and the `Stop` hook
  holds a run whose steps were closed against definitions that were not the plugin's.
- **The run's owner is read from the harness first.** `CLAUDE_CODE_SESSION_ID` before
  `AGENT_KIT_SESSION_ID`, because the agent can set the latter and one bogus owner would silence the
  `Stop` hook for the rest of the run. Under a sprint the two are the same value, so the fix costs
  the child nothing.
- **The run-state rule was a substring test.** `.agent-kit//runs/x.yml`, `.agent-kit/./runs/x.yml`,
  a leading `D=.agent-kit/runs` environment assignment, `cd .agent-kit && cd runs`, and
  `rm -rf .agent-kit` all walked around it. Words are normalised before matching, the run-state test
  moved ahead of the environment-assignment strip, and stepping into or deleting the kit's own
  corner is refused by name. The `Write`/`Edit` hook resolves the path against the session's
  directory through `realpath` first.
- **`refusal()`'s splitter missed separators.** A newline, a bare `&`, and a leading `(` all put the
  real command at `words[1]`, where nothing looked — so `run: "echo hi\ngh pr merge 5"` in a
  definition file would have executed. The splitter now covers them.
- **A committed run-state file was trusted.** `.gitignore` does not apply to a path a commit already
  tracks, so one can arrive in a pull request with every step `verified`. `load_state` now refuses a
  state file git tracks, and validates each step entry rather than reaching into it.
- **`git` failing read as `git` approving.** `_git` returned `""` for both "no output" and "no
  answer", and the two checks that prove anything — `tree_clean` and `pushed` — read emptiness as
  success. An index.lock made the PR step pass. `_git` now returns `None` when git did not answer,
  and both checks fail on it and say so.
- **Evidence was replayed into the next session's context verbatim.** `SessionStart` output is the
  most trusted voice in a fresh window; a multi-line evidence string could open a heading of its own
  and read as the kit's own governance. It is collapsed to one line, cut to 120 characters, and
  wrapped as a quoted record.
- **The dumper could deadlock a run.** `kit_yaml.dump` raises on a value that will not round-trip —
  `closed the owner's #1 complaint` is one — and `write_state` did not catch it, so the attempt was
  never recorded, `max_attempts` was never reached, and the `Stop` hook held for ever. That is the
  deadlock the design forbids. `_render_scalar` now falls back to double quotes instead of failing,
  and `write_state` reports what it cannot write as a gate error.
- **`exists:` globs followed symlinks out of the project.** Matches are kept only when their
  `realpath` is inside the root, and the pattern itself is judged when the definition is read rather
  than mid-run.

Two things are deliberately *not* fixed. The Bash rule cannot be complete — a shell has more
spellings than any text rule can model — and the refusal now says so: it makes closing a step by
hand a decision rather than a slip, and it is not a sandbox. And a `run:` check inherits the
session's environment; scrubbing it would break every project command that needs it.

## `run reset`

`gate.py run reset --reason "<why>"` discards a branch's run. It closes nothing — every step of the
next attempt has to be proven from nothing — and it grants no power the design did not already have,
because no state file already means no run.

It exists because two real paths had no way out. `sprint`'s "one informed retry" resets the branch
and relaunches the feature under a new session id, onto a branch still carrying the previous
attempt's state: the new child would be unowned by the `Stop` hook and refused at its first
`step start`. And a run abandoned mid-pipeline nudges every turn for ever, with the only remedy
being a human deleting the file — which a headless orchestrator does not have.

## Autonomous defaults recorded here

- State file naming: slug plus the full branch inside the file, verified on read.
- Evidence fields: check, command, exit code, output tail (last 1,000 characters), timestamp.
- `session-start.sh` prints the open step, each step's verdict, and the open step's attempt history,
  capped at 2,000 characters.
- `step start` prints the closing criteria as a list.
- A `run:` check gets a 1,800-second timeout. `limits.wall_clock` is stage 4; without any bound a
  hung command would hang the gate, and a headless overnight run has nobody to notice.
- `KIT_PIPELINES` overrides the definition file's location. It exists so the tests can drive the gate
  against fixture pipelines; the plugin never sets it, and a run that used one is held by `Stop`.
- The mutation pass is wired into `scripts/validate.sh` behind `KIT_MUTATE=1`, and CI sets it. It
  costs about seven minutes against fifteen seconds for everything else in that file, and a
  pre-release check nobody waits for is a check nobody runs.
- The fixture pipelines live as strings inside `tests/test_gate.py` rather than under
  `tests/fixtures/gate-*/`: two of them declare a check that fails on purpose, and a definition read
  a screen away from the assertion about it is one nobody re-reads.
