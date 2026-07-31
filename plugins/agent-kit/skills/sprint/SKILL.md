---
name: sprint
description: Turn one hour of the owner's attention into a stretch of autonomous building — brief a coherent batch of features interactively, then run each through ship --brief in its own fresh session, and deliver the batch as one mergeable integration PR with a report.
argument-hint: "[theme] | --integrate [feature ids]"
disable-model-invocation: true
---

# Sprint

Two phases in one command. **The brief** — interactive, the owner is here. It runs until the batch
is settled, not until a clock says stop: it is finished when nothing is left open that would be
expensive to reverse once the run starts. A batch of small features can be briefed in minutes; one
that turns on a data migration and two public interfaces takes as long as those three decisions
take. **The run** — autonomous, the owner is away; each feature executes as
`/agent-kit:ship --brief <spec>` in a fresh headless session, because one ship run nearly fills a
context and a queue of them in one session would not survive. The contract of the whole command:
after the brief's last question, nothing asks the owner anything until the final report. Start it
whenever you like — over a working afternoon or before bed; the run is unattended either way, and
nothing in it depends on the hour.

`${CLAUDE_PLUGIN_ROOT}/rules/presenting.md` governs every moment of the brief. Length is spent on
questions, never on prose: designs arrive as one screen and questions arrive batched, so what the
brief costs the owner is deciding things rather than reading you explain them.

Like `riff`, a sprint needs a north star and a roadmap to choose work against. If the project is
not bootstrapped, say so and offer `/agent-kit:ship`, which runs the interview first.

If `.agent-kit/sprint/` already holds a queue that is not `done`, offer to resume it (see Resume)
before opening a new brief.

## The brief

1. **Compose the batch.** First run `stack-playbook`'s freshness check — the brief, with the
   owner present, is the cheapest moment to repair a missing or stale playbook, and every sketch
   will lean on its library map; current costs seconds and no words. Then: theme from
   `$ARGUMENTS`, or ask once. Read the idea and roadmap sources, the code, and recent history,
   then propose one coherent batch of 3–6 features with an explicit dependency order — which features build on which, which are independent. Put the composition up
   as one structured choice, not an essay. Fewer, coherent features beat many loose ones: shared
   context between them is what makes a batch cheaper than N separate sittings.

   Propose a depth for each feature in the same round — `light`, `normal`, or `deep`, as
   `brainstorming` defines them — with a word on why, and let the owner move them. This is the one
   place the batch's shape and its cost in attention are visible together, and a feature the owner
   marks `deep` is a promise that its sketch will be a real design conversation rather than a
   summary. Record the level in `queue.yml`; the run session reads it back.
2. **Scope the batch in one pass.** An `ideate`-style round over all chosen features together:
   what is in and out of each, deferred ideas to the roadmap. Structured questions, only where the
   answer changes what gets built.
3. **Design each feature to the depth it was given.** Explore enough to be concrete —
   `brainstorming`'s candidate sweep, its documents-against-the-code check, and its neighbours pass
   all apply here, and a sprint is where they earn the most, because nothing downstream will catch a
   missed neighbour or a stale document once the run is unattended. Then present per the presenting
   rule: goal, a small diagram when there is structure, the *your call* forks, the *taken as given*
   list, *left to the run*, and how the feature will be proven.

   What the depth buys:

   - `light` — the approach in a few lines plus done-means; component detail is the run's job.
   - `normal` — key decisions and boundaries, one approval round.
   - `deep` — two rounds, shape then mechanics, as full as an interactive design. The mechanics
     settled here are settled, which is the entire reason a feature gets marked deep.

   What the owner settles is exactly what `ship --brief` will treat as settled; what is left open
   becomes the run's logged assumptions. Say that once at the first sketch, and after that show it
   concretely as each feature's *left to the run* list rather than repeating the warning.

   Spend questions where wrongness is expensive. A fork on an irreversible or hard-to-change
   surface — a data migration, a public API shape, a security boundary, money — earns a question at
   any depth, however small the feature, and earns it even when you hold a confident answer.
   Internal mechanics earn one only at `deep`, where the owner has asked for precisely that. An
   unattended deviation is cheap to fix where code is private and brutal where it is not, and the
   brief mirrors that asymmetry — which governs *which* questions get asked, not how few.

   An unattended run buys patience, not budget. Nobody is waiting, so verification too slow to sit
   through is available here — mutation testing over the changed code, the one mechanical proof that
   the new tests *can* fail; property-based tests where there is parsing, arithmetic or an invariant;
   a full end-to-end pass over the touched surface instead of a smoke. But the token budget is shared
   with every other feature in the batch and with the window it has to run in, so slow is not free.
   Name **at most one** heavy layer per sketch, and only where the feature earns it: the mechanical
   proof for logic that is easy to get subtly wrong, properties for real invariants, resilience
   testing only where the product genuinely has failure modes to survive. A sketch that asks for
   three heavy layers is asking the batch to pay for certainty it did not need — and the run session
   owes whichever one was named as part of its verification plan.
4. **Write the sprint to disk.**

   ```text
   .agent-kit/sprint/<YYYY-MM-DD>-<slug>/
     queue.yml
     orientation.md
     01-<feature-slug>/spec.md
     02-<feature-slug>/spec.md
   ```

   `orientation.md` is what every child would otherwise work out for itself. You have just read the
   code, the documents and the history to compose this batch; write down once what all of the
   features need to know — the repository's shape, its test command and conventions, the handful of
   files the batch will keep touching, and the paragraph of any long document that actually applies —
   and put it beside `queue.yml`, where `ship --brief` looks for it without being told. Six
   children each reading the same thousand-line design document to find one section is six times the
   cost of reading it once, and each of them then carries it for the rest of its run.

   Each `spec.md` is the approved design: goal, scope in and out, settled decisions, the *left to
   the run* list with the default named for each item, and **done means** — the observable acceptance criteria the run
   session's tester must prove, with the verification expectations. A sketch without done-means
   lines gives the run nothing to aim its tests at; do not close a sketch's approval round
   without them. `queue.yml` is the sprint's durable memory:

   ```yaml
   sprint: 2026-07-28-auth
   status: briefed          # briefed | running | integrating | done
   integration:
     branch: sprint/2026-07-28-auth-integration
     carries: []            # the feature ids the open integration PR delivers
     pr: null
   features:
     - id: 01-password-reset
       spec: 01-password-reset/spec.md
       depth: normal          # light | normal | deep, as agreed in the brief
       branch: claude/password-reset
       base: main           # or the branch of the feature it depends on
       depends_on: null     # or a feature id
       status: pending      # pending | running | done | blocked
       sessions: {}         # stage name -> the uuid it ran under, so any stage can be resumed
       pr: null
       note: null
   ```

   The sprint directory is working state, not repository content: keep it out of git (add
   `.agent-kit/sprint/` to `.gitignore` with the owner's go-ahead if it is not already ignored).
   Untracked, it survives the branch switching the run does underneath it.
5. **Close the brief.** Show the queue as a table, name the estimated span, and ask the last
   question of the interactive phase: start the run now? On yes, start it in this session.

## The run

Preflight once: the working tree must be clean — a dirty tree is a blocker to report, not to work
around. Run the branch sweep over earlier sprints' branches while the tree is still untouched. The
session must be in an auto permission mode; each child is launched with the same permission mode the
orchestrator session runs under, or it will hang on its first prompt with nobody there to answer it.

Then loop until no feature is runnable:

1. **Pick** the first `pending` feature whose `depends_on` is `null` or `done`.
2. **Check out its `base`** — `main` freshly pulled for independent features, the dependency's
   feature branch for dependent ones. The child session branches from whatever is checked out.
3. **Hand down what actually happened.** For a dependent feature, write `<id>/upstream.md` before
   launch: the parent's deviations and assumptions, pulled from its Run log or PR body, in a few
   lines. The sketch was written against the parent as imagined during the brief; `upstream.md`
   is the diff against reality, and `ship --brief` reads it with the spec.

   **Delegate the writing of it**, to a single subagent given the parent's plan and PR number. Read
   those yourself and you pull a finished feature's whole Run log into the orchestrator's context,
   where it is then re-read on every remaining step of the batch — six features on, you are still
   carrying the first one's review findings. This is the one place the orchestrator would otherwise
   grow without limit, and it is why it does not need restarting between features: what it must know
   about a finished feature is its status, its PR number and one line of note, all of which live in
   `queue.yml`. Ask the subagent for `upstream.md` on disk and a three-line summary back, nothing
   more.
4. **Mark it `running`** in `queue.yml`, then launch the child in the background and wait for it:

   ```bash
   sid=$(python3 -c 'import uuid; print(uuid.uuid4())')   # record it in queue.yml first
   claude -p "/agent-kit:ship --brief <absolute path to spec.md> --stage <stage>" \
     --session-id "$sid" --permission-mode <the mode this session runs under> \
     --model <the stage's tier> --effort <the stage's effort> \
     >> .agent-kit/sprint/<sprint>/<id>/run.log 2>&1
   ```

   **Match the model to the stage.** Judgment and mechanics do not need the same machine, and a batch
   that runs every stage on the strongest one pays a multiple for work that never needed it:

   | Stage | Model | Effort | Why |
   |---|---|---|---|
   | `design` | `opus` | high | choosing an approach is the decision everything downstream inherits |
   | `build` | `sonnet` | medium | carrying out an approved plan against a written spec |
   | `review` | `opus` | high | judging finished work, and the only pass that reads the spec |
   | `deliver` | `sonnet` | low | watching CI, reconciling docs, mechanical to the end |

   Name a tier, not a version — these aliases resolve to the current generation, and a pinned id goes
   stale in a repository nobody revisits. This is a dial, not a law: a batch whose features are mostly
   intricate logic can put `build` on the strong tier and still save on the rest, and a sketch may say
   so. What makes the cheaper build stage safe is that the review wave immediately after it reads the
   same diff with fresh eyes on the strong tier — degrade *that* and nothing catches anything.

   **Four sessions per feature, not one** — `design`, `build`, `review`, `deliver`, in that order,
   each launched exactly like the command above with its own session id, model and effort. Not a
   shell loop: you check between them, and a stage whose steps are not settled in the plan's Run log
   stops the feature rather than handing a half-built branch to the next stage.

   Why it is worth four launches: a session re-reads its whole context on every step, so a run costs
   roughly its step count times its average context. Splitting divides the part that grows — the
   accumulated conversation — by the number of stages, while the part that does not, the handoff each
   stage re-reads at its start, stays. That floor is why the saving lands near half rather than the
   quarter the growth term alone would suggest, and why a fifth or sixth split buys little: the floor
   is most of what is left by then, and every extra seam loses working knowledge. The handoff itself
   is the spec, the plan, its Run log and the commits — on disk already, because the pipeline was
   built to survive losing its context.

   Record each stage's session id in `queue.yml` under that stage's name rather than replacing the
   last one. A feature that fails at `deliver` must be resumable from `deliver` rather than rebuilt
   from `design`, and a `build` that died is still worth resuming after `review` has started.

   One child at a time, by design: parallel features in one repository conflict, and sequencing is
   what lets dependent features stack. A stage takes tens of minutes — run it in the background and
   check on it periodically rather than holding a foreground call against a timeout.
5. **On exit, check the pipeline actually finished, then record the outcome.** Exit code 0 proves the
   process ended, not that the run reached its end — a step read inline can take over the child's
   role, and the turn ends with that step's report. So read the plan's Run log: `done` needs every
   declared step settled and a PR that exists. If steps are unsettled, nothing is lost and this is
   not the retry below — resume the child's own session, which costs seconds where a relaunch costs
   hours:

   ```bash
   claude -p --resume <session from queue.yml> \
     "Continue the pipeline from your first unsettled step in the plan's Run log." \
     >> .agent-kit/sprint/<sprint>/<id>/run.log 2>&1
   ```

   Do not finish those steps by hand from here. The orchestrator holds none of the feature's
   context, and a pull request assembled from outside it is not the one the pipeline would have
   written — it is a guess wearing the pipeline's name.

   Then find the feature's PR (`gh pr list --head <branch>`), and mark
   `done` with `pr` filled. A rate-limit exit is not a failure: the child's output names the hour the
   limit resets, so read it from the tail of `run.log` and wait until then before relaunching the
   same stage. Sleep in chunks a tool call can survive rather than one long one, checking the clock
   between them. Retrying immediately neither works nor costs nothing — it burns a session start per
   attempt, and a queue that polls a closed window all night has nothing to show for it. A real failure gets **one informed retry** before it costs anything: reset
   the branch state, relaunch the same feature once with the tail of its `run.log` alongside the
   spec — a transient failure should not take a stack down. Only after the retry mark it
   `blocked` with a one-line `note` naming the reason; a `blocked` feature blocks its dependents —
   mark them too, with `note: blocked by <id>` — and the loop moves on to the next runnable
   feature instead of stopping.

   A feature PR based on another feature's branch cannot deliver anything on its own: its merge
   button moves code into that branch, not into `main`. The `deliver` stage converts it to a draft
   itself as the last thing it does; check here that it did, and do it yourself if the stage was
   blocked before reaching that point (`gh pr ready --undo`). The order matters in both directions:
   the `code-review` plugin declines to review a draft, so a pull request drafted when it opens
   silently loses the strongest review in the pipeline — and one left ready is a merge click away
   from moving code sideways. Check too that its body opens with the line
   `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md` requires — the child should have written it, and
   the orchestrator is the backstop. It stays the place the feature is read, reviewed, and checked
   by CI; it stops being a way to land code.
6. **Never merge anything.** A dependent feature builds on its parent's *branch*, not on a merge,
   and nothing reaches `main` until the owner merges an integration PR.

The queue file is updated at every transition, not at the end — it is how a resumed session finds
out where the run stood.

## The integration branch

Features green one by one are not yet a green module — and a module the owner can merge with no
rework is the whole point of the run. The stack itself cannot deliver one: every dependent PR
targets its parent's branch, so its merge button moves code sideways rather than into `main`, and
the order and the merge method silently decide whether anything lands at all. The run ends by
taking that decision away from the owner.

When the loop empties, branch `sprint/<slug>-integration` from a freshly pulled `main` and merge
into it the tip of every stack and every independent branch that is `done`. Conflicts between
features surface here and are resolved here — by you, with the whole batch in front of you, rather
than by the owner under a merge button. Then run the project's full declared suite on that tree and
start the app if it has a runnable surface, exercising what the batch changed: this is the only
tree that matches what `main` will actually contain, and no feature PR has been checked in that
shape. The verdict leads the final report.

A failure traceable to one feature gets one fix round on that feature's branch — fix, rerun what
the fix put at risk, push, rebuild the integration branch, note it in the queue; anything wider than
one feature is reported, not patched at the end.

Then push and open the integration pull request against `main` per
`${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, and record `integration.pr` and `integration.carries`
in the queue. It is the sprint's only mergeable pull request, and it describes the batch as a whole:
the feature table with each feature's own PR named as the place to read that diff, the Manual
actions of every feature consolidated, and every feature's Assumptions gathered into one table — the
batch is read here, the code is read there. State in it that it must be merged with a merge commit
rather than a squash: a squash detaches the feature commits from `main`, which breaks both the next
batch and the branch sweep below. Check once that the repository allows merge commits, and report it
as a blocker if it does not.

**Batches.** The default batch is the whole sprint, and `--integrate <feature ids>` builds one from
part of it — for an owner who wants two features in production before taking the rest. The single
constraint is dependency closure: a feature ships only with all of its ancestors, whose branches
carry its commits. Name the missing ancestor and stop rather than quietly widening the selection.

A later batch needs nothing done to the feature branches. Build it exactly like the first —
a new branch from the freshly pulled `main`, the tips of the chosen features merged in — and the
commits the earlier batch already landed are common to both sides, so they merge clean.

**Rebuilding.** The integration branch is derived: nothing is committed to it directly, every change
belongs on a feature branch, and the branch is rebuilt the same way whenever a feature branch moves
after it was built — a review round through `/agent-kit:address`, a fix the owner asked for — or
`main` moves underneath it. Rebuild, rerun the suite, force-push. An integration PR built from stale
tips is worse than none: it looks mergeable and delivers the previous version of the fix.

## The branch sweep

Once an integration PR is merged, the branches it carried are dead weight: the feature PRs were
closed rather than merged, so nothing points at those branches any more. Do not track that in the
queue, measure it: a branch whose `git diff origin/main...<branch>` is empty adds nothing to `main`
and can go. The test only ever errs one way — a branch still holding unlanded code never reads as
empty. It does read as non-empty after a squashed merge, whose commits are detached from the ones on
the branch, which is the second reason the integration PR asks for a merge commit; a swept-up sprint
that keeps reporting live branches is that squash showing up later.

Sweep at two moments — the end of a run, and the preflight of the next sprint — over the branches
named in this and earlier `queue.yml` files. Delete the empty ones locally and on the remote, close
their pull requests with a line naming the integration PR that carried them, and report the rest in
one line as branches still holding code.

## The final report

When the integration PR is open, set the sprint `status` accordingly, write
`.agent-kit/sprint/<sprint>/REPORT.md`, and present it. In order: the integration verdict; a table
of feature / status / PR / CI; then **the decisions taken without the owner** — each feature's
assumptions and deviations gathered from the run's Run logs, as short lines, not counts, because
they are the exact places the owner's eye is needed; then **what to merge** — the integration PR,
as the command that merges it the right way (`gh pr merge <n> --merge`), with the feature PRs listed
as where to read each diff and explicitly not as things to merge; then the commands for what comes
next — `/agent-kit:address <pr>` for review rounds, `--integrate` for taking the batch in parts,
resuming the sprint for blocked features. Keep it to one screen; the details live in the PRs.

## Resume

Invoked with an unfinished queue, continue the run rather than re-briefing: `pending` features run
as normal. A feature marked `running` with no live child process means the last session died
mid-feature — read the plan's Run log to see which stage it died in, and pick up from **that stage**,
not from `design`. Its session id is in the feature's `sessions` map, so a stage that stopped
mid-way is resumed rather than rerun; a stage whose steps are all settled is simply skipped, and the
next one is launched. Rebuilding a finished `design` and `build` because `deliver` failed costs hours
and changes the code under a review that already passed. The specs were approved once; a resume never
re-opens them.

`--integrate` is not a resume: on a queue whose features are already `done` it builds the next
batch's integration PR from the ids given, sweeps branches, and stops. It is also how a sprint is
picked up days later, when `main` has moved and the open integration PR needs rebuilding.
