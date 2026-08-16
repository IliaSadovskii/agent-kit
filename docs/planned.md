# What is planned, and what was deliberately refused

The kit's design notes each end with what they left open, and there was no page that held those
together — so a session picking the work up had to read nine notes to find out what is next, and
nothing said which ideas had already been examined and rejected. This is that page.

**Read the second half before proposing anything.** Every item there was proposed once, checked
against the payload, and refused for a reason that is still true. A proposal that reappears without
answering the reason is the same proposal.

## Next, in order

1. **The three gaps in coverage** — item 6, second bullet. Small, independent, one commit each.
2. **The journal of questions** — item 3.
3. **Codes and levels on findings, and judging a run before it closes** — item 6, third bullet and
   fourth, together. A day, and it rewrites the check's output; the merge policy needs it, and needs
   it first, because a policy reads an exit code. The fourth rides with the third because both move
   the same code — what a finding is and when it is asked — and apart they rewrite one file twice.

Done since this page was written: one `gh` call instead of N, in 2.19.2.

Deferred by the owner, with the reason: the bench (item 1), the merge policy (item 4), parallel
building, the backlog command, the schedule, the continuous mode (item 7). Until the bench exists,
changes to the kit are checked by real runs.

Everything below is the reasoning, and the second half is what was refused.

---

## 1. A bench for the kit itself — on `claude plugin eval` · **deferred**

**Deferred by the owner**, August 2026: until it exists, changes to the kit are checked by real
runs, which is what they were checked by before. Everything below stands as written — the reason to
build it has not changed, only its turn.

**The problem.** Checking a change to the kit costs a live overnight run on a real project. That is
why talking about the kit cost 26% of one measured week — more than two thirds of a whole `epic` —
and why discussion substitutes for measurement. It is also why no two versions of the kit have ever
been compared with each other.

**Do not build a harness — Claude Code ships one.** `claude plugin eval` runs cases from
`evals/**/case.yaml` with graders in `graders/*.md` against a plugin, and carries everything this
would otherwise need:

- `--ablation with-without` runs each case **with the plugin and without it** and reports the delta.
  Nothing in this kit has ever measured what the kit itself is worth;
- `--runs <n>` (3 by default) — the result is probabilistic and one run says nothing;
- `--threshold <0..1>` exits non-zero when a case drops below it, which is a CI gate;
- `--max-cost-usd` is a hard ceiling, which is what makes a bench safe to run against a weekly quota;
- `--json` and `--report` give a machine result and a self-contained HTML report with per-grader
  verdicts;
- `claude plugin eval init` authors a suite through an interview.

Three things the list above does not say, and each costs a run to find out. `with-without` is the
default **only when the target is a plugin by name** — installed or in a skills directory; a path
gets `none`, which is the shape a repository checkout is most likely to be run as. A sample
repository is built by a case's `scaffold_script`, which does not run without `--scaffold`, off by
default because it executes the author's bash as the user. And a case whose agent has to touch the
tree needs `--allow-tools`, since Bash, Write, Edit and WebFetch are gated behind that grant.

**What to write, then, is only the cases.** A sample repository with a blueprint and traps planted
in it. The bench does not judge whether the code the kit wrote is good — that is not measurable. It
judges **whether the kit's own mechanisms fired**, and a grader can be a script:

| Trap in the sample | What must happen |
|---|---|
| an entry promising what the code does not do | a test marked `unmet`, a line in `unmet`, the suite still green |
| a scenario with no harness | named at the gate, not discovered at the finish |
| two features quietly writing to one table | the frame child links them through `needs` |
| a debt line the feature closes | the line deleted in the same commit |
| an entry whose prose the feature makes false | a `[stale …]` block under it |
| a task closed with no commit | the check names it |

**Half that table is out of reach of a bench, and it was written without saying so.** An eval case
is *one agent run* under a turn limit — so the rows that are one command in one session are
reachable (a `ship` against a planted entry, a gate meeting a scenario with no harness), and the row
about two features and one table is not: it needs a batch, a frame child and the driver starting
several sessions, which is a night, not a case. The last row — the check naming a task closed with
no commit — is already covered by `tests/test_check.py`, where it costs nothing and runs in
milliseconds; putting it in front of a model would be paying tokens for an answer a unit test
already gives. What is left for the bench is what only a bench can do: **the with/without ablation**,
which says what the kit itself is worth, and the behaviour of one command under a trap.

**First, not last**, because it is the instrument every other item below is checked with.

## 2. A home for manual actions, with a proof that runs · **done in 2.19.0**

`docs/manual.md` written from a template of its own, `proof` as an executable command,
`check.py --manual` running them and deleting what has happened, `stage` deciding what is shown,
`accept` running the proofs before it lists anything. Kept here for the reasoning.

**The problem.** `manual` records — a secret to place, a migration to apply, an account to create —
live in `.agent-kit/runs/<slug>/run.json`, which is git-ignored and dies with the machine. The only
reader is `accept`, which composes them out of a pull request body that nobody opens again after the
merge. So the one class of work that genuinely needs the owner is also the one with no durable home.

**What to build.**

- A file in the repository, shaped like `docs/technical_debt.md` — same idea, same lifecycle: a run
  appends a line, whoever does the work deletes it in the same commit.
- **`proof` becomes an executable check**, not prose. A command that exits zero once the action has
  been done: the key is in the environment, the migration is applied, the endpoint answers. Then the
  program removes the line itself and nobody has to remember to tick anything.
- **`when` decides visibility**, against `stage` in `project.yml`. On a project at `development`,
  `before_release` lines are not shown at all — they are not work anybody is going to do this week.
- Where no check can be written (it truly needs a person holding a phone), the line stays with that
  said plainly. That list is short, which is the point: on one measured run, nineteen items held six
  that needed a person.

**Where.** `templates/run.json` (`manual[].proof`), a new template for the file, `check.py` (run the
proofs, print what is due), `rules/pull-requests.md` and `skills/accept/SKILL.md` (they compose from
the field today).

## 3. A journal of questions and answers, with Telegram as its transport

**The problem.** An answer from the owner lives in the context of the session that asked. The
session dies, the answer is gone. `answers` in the run file reaches nobody outside that run. Five
children of one batch can ask the same question in turn, and each gets it answered separately or not
at all. And the existing channel — the driver typing into the owner's tmux window, which the app
turns into a notification — is drowned by its own volume: a push fires for every session that
starts, so the one push that carries a question is lost among them.

**What to build.** Settled with the owner on 16 August 2026, on two rules: a run waits only inside a
window it cannot lengthen, and it never replays what it has already built.

- **A directory, not a file**: `.agent-kit/asks/<id>.json`, one file per question. A single shared
  file means two sessions and a bot writing at once; one file per question needs no locking. It
  lives on the machine, beside the run files: what has to survive here is **the death of a session**
  — which is what makes an answer given at three in the morning worth anything — and not the loss of
  the machine, which is a different problem with a different home. The "journal" is a view over that
  directory.
- Each question carries: which run asked it, when, what it is about (**the entry keys and the files
  it touches** — not a "share with siblings" flag, which would ask the writer to predict who needs
  the answer), **the default this run took**, and the answer when it lands.
- **A window, and then the default.** Twenty minutes: a question stops the run for that long and no
  longer. Answered inside it, the run goes on the answer — no assumption, no block, nothing to
  settle later, which is the whole reason to wait at all. Unanswered, the run takes its default and
  carries on.
- **The number is the kit's, not a project's**, and it lives beside the hang timer in the driver
  rather than in `project.yml`, so that no configuration can put a window past the timer that kills
  the session waiting in it. Two numbers in two files drift; two numbers in one file are held to
  each other by the program that owns both — and `--hang` is refused below the window rather than
  quietly winning against it.
- **An unanswered window closes the next ones for three hours.** An owner who did not answer at
  02:10 is asleep, and the second question of that night must not spend another twenty minutes
  finding that out again. Three hours on, the next question opens a window as normal. It needs no
  new state: the newest question that expired unanswered is in the directory, so every child of a
  batch reads the same fact without being told. This is the whole answer to what killed
  `wait <hours>` — that wait had no ceiling and no cooldown, so a night paid for its hours over and
  over.
- **The driver holds the window, and that is why it can be trusted.** A session that stops on a
  question writes `waiting_on` and says nothing more; the driver — which already reads that field,
  already watches the transcript and already types into a live session — waits out the window and
  then types one line: *no answer, take your default*. So the two timers are enforced by the same
  program, twenty against a hang of thirty, and a session's own prose carries no number to get
  wrong. A `ship` the owner started by hand has no driver and needs none: they are at the keyboard,
  and the question is asked the way it is asked today.
- **A window at `gate: none` too.** With a push that reaches a phone, *nobody is present* stops
  being a property of the run and becomes a property of the moment — the owner may be awake at
  02:10, and if they are, the run gets a real answer instead of an assumption for twenty minutes of
  patience. `rules/asking.md` says today that a `gate: none` run does not ask and does not wait; that
  section is rewritten when this is built, and what it keeps is the part that is still true — the
  run never *stops* on an unanswered question.
- **A session that has already gone past the fork is not told the answer.** It cannot act on it
  without redoing decided work, and a night run that starts redoing its own finished tasks is the
  other half of what got `wait <hours>` removed in 2.5.0.
- **The reader of the answer is `blueprint`**, and that is not a new mechanism. Closing a block with
  the owner and writing their answer into the knowledge is what `blueprint` already does. So the run,
  as it closes, leaves the record that points back at the question — `[assumed 2026-08-16 ·
  ask:<id>]` — and the answer meets the owner there. An answer that agrees with the default closes
  the block and touches no code. One that disagrees rewrites the entry, and where the build was
  wrong the entry goes back to `planned`, which `next` picks up: the disagreement becomes work
  instead of a patch behind a merged commit.
- **Where that record hangs follows the question, not the mechanism.** About the product — a block
  under the entry. About the stack — a block under `stack.md`. Something only the owner's hands can
  do, a domain to buy or a plan to pick — a line in `docs/manual.md` with its proof. All three exist
  already; the question file only records which one was used.
- **The reader of the open ones is the preflight.** `check.py` already prints the debt and the open
  blocks before every command; questions still open, and answers that have landed and not yet been
  settled, go in the same output. Nothing new to remember.
- **Closed by the program, on a fact it can check.** `check.py` deletes a question file once its run
  has reached a terminal step and nothing in the project references its `ask:<id>` any more — the
  block gone means `blueprint` settled it, the line gone from `docs/manual.md` means the proof
  passed. Both are facts, not promises, which is the whole reason this closes at all: a record whose
  removal waits on somebody remembering has cost this kit a release before.

**Open, and deliberately not decided yet**: whether the bot is one process on the server for every
project or a script inside the plugin, one per project. The files and their reader come first — the
transport bolts onto them either way.

See the refusal of *an asynchronous channel with a deadline* below, which this partly reverses and
partly keeps. Reversed: a run may stop and wait, because twenty minutes with a push on a phone is
not the same instrument as `wait <hours>` in front of a tmux window nobody was looking at, and
because an unanswered window now shuts the rest for three hours instead of charging the night for
each one. Kept, and it is the part that mattered: **an answer that arrives after the window is never
applied**. It goes to `blueprint`, and a disagreement becomes work.

## 4. A merge policy — a program, not a decision · **deferred**

**Deferred by the owner**, 16 August 2026, until the check has codes and levels — a policy reads an
exit code, and today that code means three different things. Two things below were checked against
the payload on the same day and are wrong as written; they are marked where they stand.

**The problem.** The kit never merges, by construction and by hook. That is right as a default and
is a dead end for the goal: one instruction from the owner, a finished result in the default branch.
The industry answer in 2026 is not "let the agent decide" — it is to cut the number of human
checkpoints while keeping the policy with the team, and to treat verification velocity as the
bottleneck rather than production speed.

**What to build.**

- A declared **evidence package**: CI green, acceptance green, no open critical or major review
  finding, no `unmet` on any entry this branch touched, the diff inside paths the project allows,
  manual actions of `when: before_merge` all proved. **Two of those do not exist**, checked in the
  payload on 16 August 2026: there is no field anywhere saying which paths a project allows —
  `templates/project.yml` has no such thing — and `accept` leaves no verdict a program could read,
  by its own boundary (*"`accept` changes nothing"*). So either they are dropped from the package or
  they are built, and building the second one costs `accept` the boundary that keeps it cheap. **Left open on purpose** — the owner takes that decision when this item comes off the shelf, not now. The
  rest — CI, review findings, `unmet`, the proofs — is there and only needs collecting.
- **At least one item of the package must not come from the kit.** Everything the package holds
  today is the kit's own word about itself — its tests, its reviewer, its suite. A static analyser
  (Semgrep, CodeQL) is deterministic, costs seconds and no tokens, and is produced by something
  other than the model that wrote the diff. It does not replace `/security-review`, which is
  agentic, expensive and triggered: one goes in the package, the other goes at a suspicious diff.
- **The program merges what passes and never judges.** What fails comes back to the owner as three
  lines, not as a pull request to read.
- The guard hook stays exactly as it is: it forbids *an agent* from merging. A policy is not an
  agent — **and the hook cannot tell them apart**. It matches the string `gh pr merge` in a Bash
  call (`hooks/guard.py`), so a program that merges inside itself walks past it, and any session
  could merge by starting that program. What actually holds the invariant is therefore who is
  allowed to start the policy, and that has to be decided before a line of it is written.
- Two modes, and they are the same machine: straight to the default branch, or one pull request with
  a very short body and the manual actions named.

**Was blocked on** the proofs (item 2) and the branch bookkeeping (item 5). Both landed — 2.19.0 and
2.17.0 — so what stands in front of this now is only the codes and levels of item 6.

## 5. Small, and each one already argued

- ~~**One rule for ticking an audit box.**~~ Done in 2.18.0: `rules/audit-boxes.md`, with the three
  callers pointing at it. Writing it down found the drift it exists against — three of the five
  places naming who ticks had never learned about `accept`.
- ~~**A batch that is closed is not re-closed.**~~ Done in 2.18.0: `epic --advance` asks
  `check.py --run` about the batch that just closed, before doing anything.
- ~~**Parked children's branches, recorded apart from delivered ones.**~~ Done in 2.17.0: `parked`
  beside `branches` in the batch record, held out of retirement, with the mismatch between the two
  named by the check. This was what blocked retiring branches by program rather than by hand.

## 6. The check system, looked at as one thing

Surveyed August 2026, by inventorying every check the kit runs. There are five layers and they do
not overlap by audience: `validate.sh` (about the kit itself), `check.py` before every command,
`check.py --run` about one run, the two hooks (outside the model, while work is happening), and the
passes over a result — the reviewer, `/security-review`, the six lenses, the project's CI.

**What is right and is not to be traded away:** looking is free and writing is asked for (`--sync`);
a check that cannot read its input says so rather than guessing; and there is no verifying pass over
a verifying pass.

Four findings, cheapest first.

- ~~**`gh` is called once per entry, on every preflight.**~~ Done in 2.19.2: one
  `gh pr list --state all`, read once per process, answers for every entry and every number a batch
  record names. A number outside the listing's cap is still asked about on its own, because an
  entry closed on a listing's silence is an entry closed on a guess.

- **Three gaps in what is checked**, all small:
  - **a declared command is never checked for existing.** `test: make test` with no Makefile is
    found out mid-run; only the string's emptiness is judged today. It matters most for the new
    `commands.e2e` and for `mutate`.
  - **a run file's `entries` are not matched against the knowledge.** `--entries` names a key that
    matches no entry; a run file carrying the same key passes in silence, and the child meets it at
    three in the morning.
  - **`base` and `branch` in a run file are not checked for existing.** The driver catches part of
    this; the check does not.

- **A finding has neither a code nor a level, and that is the root of the rest.** The difference
  between *stop* and *note this* is carried by the prose alone: nine groups reach the exit code,
  twenty-seven other places print beside them and do not. `rules/preflight.md` exists to translate
  between the output and the reaction, and its rows do not map one-to-one onto the groups.
  Consequences: the exit code means three different things across `main`, `--run` and `--epic`, so
  **nothing can be automated on it** — which the merge policy will need; findings cannot be counted
  or compared between runs; and a rule that fires and is ignored looks exactly like one that did not
  fire. Give each finding a code (`KNOW-FIELDS`, `RUN-PROOF`, `BATCH-SPENT`) and a level
  (`stop` / `statement`), and `preflight.md` shrinks to two sentences.

- **Almost everything about a run is judged at `step: done`**, which is the moment nothing can be
  fixed — the session is closing and the finding becomes a line in a report nobody can act on at 3am.
  The shape rules, `prompt`, `handoff` and now `tasks[].commit` were moved early, and that is the
  direction to keep going: `proved_at` and `mutation` can be asked on entering Deliver rather than
  at the end of it — the steps run `verify → deliver → done`, and both fields are written in
  `verify`. **Done together with the bullet above**: what a finding is and when it is asked move the
  same code, and taken apart they rewrite `run_defects` twice.

One thing deliberately not changed: the check recomputes everything on every run and remembers
nothing, so the same finding prints thirty times a night. That is the price of silence meaning *all
clear*, and it is the right trade. With codes it becomes cheap to print what is new in full and what
was already standing in one line.

## 7. Later, and deliberately not now

**Not checked against the payload**, unlike everything above it: these four were read as the owner's preferences and left as written, on their instruction. Check them the day one of them is taken up — the reasons below are two months old and the kit has moved under them twice.

- **A backlog command** — `next` widened from one recommendation to a ranked list, so the owner can
  see the whole queue without reading files. All the data is already read by `check.py`.
- **A schedule, living in `blueprint`** — it already owns `project.yml`.
- **Parallel building, behind a switch.** The frame child already computes `needs` — the graph of
  what cannot be built before what — and the driver flattens it into a single queue. Three of five
  features usually depend on nothing and could be built at once; the industry standard is a worktree
  per agent with a light container each. **Not now**: on a fixed weekly quota, parallelism does not
  add capacity, it spends the same quota faster. It becomes worth doing on a larger plan, and it
  should be a flag — one lane by default.
- **A continuous mode**, also a flag: when a run finishes, take the next thing off the queue and
  carry on until the owner switches it off. Started by the owner, at a moment they chose.

---

# Outside tools, examined

Surveyed August 2026, against the question *what would the kit stop having to build itself.*

**Taken.**

| Tool | Where it goes | Why this one |
|---|---|---|
| **`claude plugin eval`** | item 1 | Ships with Claude Code. Cases, graders, a with/without ablation, repeated runs, a cost ceiling, a JSON result and an HTML report. Building this would have been the largest thing on this page |
| **`@playwright/cli`** | the recommended value of `commands.e2e` on a project with an interface | Microsoft's CLI companion to Playwright MCP, reported at roughly a quarter of the tokens for the same work (≈27k against ≈114k), because it is plain shell commands — **their number, not one measured here**, and worth re-measuring on a real project before it is quoted again. MCP is for agents with no filesystem; Claude Code has one |
| **Semgrep** (or CodeQL) | item 4, the evidence package | The only cheap signal in the package not produced by the model that wrote the diff. Published studies put generated code at a 25–40% vulnerability rate — **quoted, not measured here** — and this costs seconds either way |

**Examined and not taken, with the reason still true.**

- **Cloud sandboxes** — E2B (Firecracker microVMs, ~150 ms cold start), Daytona (Docker snapshots,
  ~90 ms, stateful sessions). They earn their price when many agents run in the cloud. One server and
  a fixed weekly quota is answered by a local worktree plus a container, for nothing. Revisit
  together with parallel building.
- **Agent observability platforms** — Braintrust, Langfuse, OpenTelemetry GenAI conventions. They
  measure trajectories of LLM applications. The question this kit asks is *what did a feature cost*,
  and `scripts/measure.py` is closer to it than any of them.
- **Orchestration frameworks.** The kit's driver is a program that holds the flow while agents decide
  at marked points — which the literature now describes as the desired shape rather than as a
  compromise (*A Deterministic Control Plane for LLM Coding Agents*, arXiv 2606.26924). Replacing it
  with a framework would be a step back.
- **MCP servers for intake** — GitHub, Linear, Jira all publish OAuth endpoints now. Not needed:
  `blueprint` is the intake, and what was missing was a trigger and a view. See item 7.
- **Anything for Telegram.** Thirty lines around one HTTP call. A framework here would be the whole
  cost of the feature.

# Refused, with the reason

Nothing here is an open question. Each was proposed, checked against the payload, and refused.

| Proposal | Why it was refused |
|---|---|
| **Batch zero writes frozen acceptance tests** for every scenario before any feature exists | It blinds the only mechanical check the finish has: `check.py --state` counts a scenario as covered when the marker appears in the suite, so the count would read *10 of 10* in the first hour with nothing working. A deliberately red test also has nowhere to live — `unmet` is forbidden for what the run itself was sent to build, and the strict form must be edited exactly when it starts passing. Replaced by: the test rides with the feature that closes the scenario's last step. |
| **The closing session runs the end-to-end tests** after every batch | No command existed to run (now `commands.e2e` does); the driver's 30-minute silence timer would restart the session mid-run; a walk in the tree the children built in proves only that an already-running application still runs; and a red result has no one allowed to close it, since most scenarios are red by construction until the batch that completes them. The home is CI on the batch's branch. |
| **`--sync` also ticks audit boxes and deletes branches** | The state line has been in the program since 0.41.0 — what is distributed is the right to *run* it, deliberately, so that nothing writes as a side effect of reading. A box cannot be ticked by a program at all. The third reason — that branch deletion was unsafe — expired in 2.17.0, and `next` deletes delivered branches today; the read/write split is what keeps this refused. |
| **Named views over `run.json`** so readers fetch a subset | Measured on 113 real run files: the whole traffic is 3.9% of a run and views would save 0.5–0.9%. The premise that the file is mostly the template's inline documentation is false — no real run file carries a single `_` key. |
| **A ceiling on the run file's prose fields** (`review`, `notes`, `task` are 51% of its bytes) | The saving is real and small; the cost is losing context that exists nowhere else. Not worth it. |
| **A task carries a free-text "how this is proved"** | Answered with "covered by unit tests" for free, and judged at a moment no command reaches. Replaced by `tasks[].commit`: a SHA either resolves in this repository or it does not. |
| **An asynchronous question channel with a deadline** — the child asks, takes its default, continues, and an answer landing within N minutes is applied | Tried and cut: `wait <hours>` shipped in 1.4.0 with this exact argument and was removed in 2.5.0 because every wait spent its hours and arrived where the run would have arrived anyway. "Applied" has no coherent meaning: an expensive fork is one whose cost *is* the cost of reversing it, and the answer arrives after the commits built on the default. **Half of this was reinstated on 16 August 2026** and now lives in item 3: a run may wait, but for twenty minutes against a push on a phone rather than hours against a window nobody watched, and an unanswered window shuts the rest for three hours so a sleeping owner is paid for once a night. What stays refused is the sentence above — an answer that lands after the window is never applied to work already built. |
| **Splitting `ship`'s Verify into a subagent** | Priced both ways and it is a wash: the tokens saved by keeping tool output out of the builder's context roughly equal what a subagent's own context floor costs. The remaining argument — a cleaner context — cannot be settled without a measurement nobody has. |
| **The kit learning from its own outcomes** — recording whether a merged feature later needed fixes | Not refused on merit; the owner set it aside as too large and too early. |
| **Rewriting the driver onto the Agent SDK**, so liveness, cost and limits come from the API instead of from parsing transcripts | The three most expensive driver defects all came from that parsing, and the SDK removes the whole class. Refused because it costs the visible tmux session per feature, which is what makes a stalled child rescuable by hand and a limit recoverable by typing one line. The owner values that more. |
| **A pull request per batch instead of one per run** | The owner does not want a pile of pull requests after an `epic`. The early-integration argument was answered separately, by CI on the batch's branch. |
| **Counting an `epic`'s price in the weekly quota** rather than in hours | The owner reads the quota themselves and decides what to start. |
| **A cron picking work up on its own** | It solves the wrong problem: the value is not that the kit starts without the owner, it is that it does not need them after it starts. And it has two real costs — a run nobody started is a run with `gate: none`, so every expensive fork becomes an assumption; and it cannot know the owner is spending this week's quota on another project. Replaced by the continuous mode in item 7. |
| **A separate `intake` mechanism** for new ideas | `blueprint` already is one: `planned` entries, the debt, the audits' work lists. What was missing was a trigger and a view, which are item 7. |
