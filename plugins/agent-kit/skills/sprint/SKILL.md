---
name: sprint
description: Turn one evening hour of the owner's attention into a night of autonomous building — brief a coherent batch of features interactively, then run each through ship --brief in its own fresh session, stacked PRs out, report in the morning.
argument-hint: "[theme]"
disable-model-invocation: true
---

# Sprint

Two phases in one command. **The brief** — interactive, the owner is here, budgeted at an hour of
their attention. **The run** — autonomous, the owner is asleep; each feature executes as
`/agent-kit:ship --brief <spec>` in a fresh headless session, because one ship run nearly fills a
context and a queue of them in one session would not survive. The contract of the whole command:
after the brief's last question, nothing asks the owner anything until the morning report.

`${CLAUDE_PLUGIN_ROOT}/rules/presenting.md` governs every moment of the brief. The budget only
holds if designs arrive as one screen and questions arrive batched.

Like `riff`, a sprint needs a north star and a roadmap to choose work against. If the project is
not bootstrapped, say so and offer `/agent-kit:ship`, which runs the interview first.

If `.agent-kit/sprint/` already holds a queue that is not `done`, offer to resume it (see Resume)
before opening a new brief.

## The brief

1. **Compose the batch.** Theme from `$ARGUMENTS`, or ask once. Read the idea and roadmap sources,
   the code, and recent history, then propose one coherent batch of 3–6 features with an explicit
   dependency order — which features build on which, which are independent. Put the composition up
   as one structured choice, not an essay. Fewer, coherent features beat many loose ones: shared
   context between them is what makes a batch cheaper than N separate evenings.
2. **Scope the batch in one pass.** An `ideate`-style round over all chosen features together:
   what is in and out of each, deferred ideas to the roadmap. Structured questions, only where the
   answer changes what gets built.
3. **Sketch each design — this is a sketch, not a full design.** Explore enough to name the
   approach, then present per the presenting rule: goal, a small diagram when there is structure,
   the *your call* forks, the *taken as given* list, and how the feature will be proven. Key
   decisions and boundaries only; component detail is the night session's job. One approval round
   per feature, about ten minutes of the owner's attention each. What the owner settles here is
   exactly what `ship --brief` will treat as settled; what is left open becomes the night run's
   logged assumptions — say so at the first sketch so the trade is explicit.
4. **Write the sprint to disk.**

   ```text
   .agent-kit/sprint/<YYYY-MM-DD>-<slug>/
     queue.yml
     01-<feature-slug>/spec.md
     02-<feature-slug>/spec.md
   ```

   Each `spec.md` is the approved sketch: goal, scope in and out, settled decisions, points
   deliberately left open, and **done means** — the observable acceptance criteria the night
   session's tester must prove, with the verification expectations. A sketch without done-means
   lines gives the night nothing to aim its tests at; do not close a sketch's approval round
   without them. `queue.yml` is the sprint's durable memory:

   ```yaml
   sprint: 2026-07-28-auth
   status: briefed          # briefed | running | done
   features:
     - id: 01-password-reset
       spec: 01-password-reset/spec.md
       branch: claude/password-reset
       base: main           # or the branch of the feature it depends on
       depends_on: null     # or a feature id
       status: pending      # pending | running | done | blocked
       pr: null
       note: null
   ```

   The sprint directory is working state, not repository content: keep it out of git (add
   `.agent-kit/sprint/` to `.gitignore` with the owner's go-ahead if it is not already ignored).
   Untracked, it survives the branch switching the run does underneath it.
5. **Close the brief.** Show the queue as a table, name the estimated span, and ask the last
   question of the evening: run it tonight? On yes, start the run in this session.

## The run

Preflight once: the working tree must be clean — a dirty tree is a blocker to report, not to work
around. The session must be in an auto permission mode; each child is launched with the same
permission mode the orchestrator session runs under, or it will hang on its first prompt with
nobody awake.

Then loop until no feature is runnable:

1. **Pick** the first `pending` feature whose `depends_on` is `null` or `done`.
2. **Check out its `base`** — `main` freshly pulled for independent features, the dependency's
   feature branch for dependent ones. The child session branches from whatever is checked out.
3. **Hand down what actually happened.** For a dependent feature, write `<id>/upstream.md` before
   launch: the parent's deviations and assumptions, pulled from its Run log or PR body, in a few
   lines. The sketch was written against the parent as imagined the evening before; `upstream.md`
   is the diff against reality, and `ship --brief` reads it with the spec.
4. **Mark it `running`** in `queue.yml`, then launch the child in the background and wait for it:

   ```bash
   claude -p "/agent-kit:ship --brief <absolute path to spec.md>" \
     > .agent-kit/sprint/<sprint>/<id>/run.log 2>&1
   ```

   One child at a time, by design: parallel features in one repository conflict, and sequencing is
   what lets dependent features stack. A feature takes hours — run the child in the background and
   check on it periodically rather than holding a foreground call against a timeout.
5. **On exit, record the outcome.** Find the feature's PR (`gh pr list --head <branch>`), and mark
   `done` with `pr` filled. A rate-limit exit is not a failure: wait for the reset and relaunch
   the same feature. A real failure gets **one informed retry** before it costs anything: reset
   the branch state, relaunch the same feature once with the tail of its `run.log` alongside the
   spec — a transient 3 a.m. failure should not take a stack down. Only after the retry mark it
   `blocked` with a one-line `note` naming the reason; a `blocked` feature blocks its dependents —
   mark them too, with `note: blocked by <id>` — and the loop moves on to the next runnable
   feature instead of stopping.
6. **Never merge anything.** The stacked PRs wait for the owner; a dependent feature builds on its
   parent's *branch*, not on a merge.

The queue file is updated at every transition, not at the end — it is how a resumed session finds
out where the night stood.

## The integration check

Features green one by one are not yet a green module — and a module the owner can merge into the
app with no rework is the whole point of the night. When the loop empties, check out the tip of
each stack and each independent branch, run the project's full declared suite there, and start the
app if it has a runnable surface, exercising what the batch changed. A failure traceable to one
feature gets one fix round on that feature's branch — fix, rerun what the fix put at risk, push,
note it in the queue; anything wider than one feature is reported, not patched at dawn. The
verdict, per branch, leads the morning report.

## The morning report

When the integration check is done, set the sprint `status` accordingly, write
`.agent-kit/sprint/<sprint>/REPORT.md`, and present it. In order: the integration verdict; a table
of feature / status / PR / CI; then **the decisions taken without the owner** — each feature's
assumptions and deviations gathered from the night's Run logs, as short lines, not counts, because
they are the exact places the owner's eye is needed; then the merge order for the stacked PRs and
the commands for what comes next — `/agent-kit:address <pr>` for review rounds, resuming the
sprint for blocked features. Keep it to one screen; the details live in the PRs.

## Resume

Invoked with an unfinished queue, continue the run rather than re-briefing: `pending` features run
as normal. A feature marked `running` with no live child process means the last session died
mid-feature — inspect its branch and run log, then either mark it `blocked` or relaunch it from its
spec. The specs were approved once; a resume never re-opens them.
