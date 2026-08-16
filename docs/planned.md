# What is planned, and what was deliberately refused

The kit's design notes each end with what they left open, and there was no page that held those
together — so a session picking the work up had to read nine notes to find out what is next, and
nothing said which ideas had already been examined and rejected. This is that page.

**Read the second half before proposing anything.** Every item there was proposed once, checked
against the payload, and refused for a reason that is still true. A proposal that reappears without
answering the reason is the same proposal.

Order below is the order to do the work in, not the order of importance.

---

## 1. A bench for the kit itself — on `claude plugin eval`

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

**First, not last**, because it is the instrument every other item below is checked with.

## 2. A home for manual actions, with a proof that runs

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
session dies, the answer is gone. `answers` in the run file dies with the machine. Five children of
one batch can ask the same question in turn, and each gets it answered separately or not at all.
And the existing channel — the driver typing into the owner's tmux window, which the app turns into
a notification — is drowned by its own volume: a push fires for every session that starts, so the
one push that carries a question is lost among them.

**What to build.**

- **A directory, not a file**: `.agent-kit/asks/<id>.json`, one file per question. A single shared
  file means two sessions and a bot writing at once; one file per question is append-only and needs
  no locking. The "journal" is a view over that directory.
- Each question carries: which run asked it, when, what it is about (**the entry keys and the files
  it touches** — not a "share with siblings" flag, which would ask the writer to predict who needs
  the answer), what the run will do if nobody answers, and the answer when it lands.
- **The bot never writes into a run file.** It writes the answer into that question's own file, and
  — where the asking session is still alive and waiting — types it into that session exactly as the
  driver already types `continue`. The rule that only a run writes its own run file stays intact.
- **The reader is the preflight.** `check.py` already prints the debt and the open blocks before
  every command; open questions and fresh answers go in the same output. Nothing new to remember.
- **Closing.** An answer applied closes its question. A question still unanswered when the run ends
  becomes an `[assumed …]` block under the entry — it flows into a mechanism that already works
  rather than accumulating in a directory nobody prunes.

**Two cases, and they are different.** Where the session is genuinely waiting (`gate: owner`), this
is pure gain and no new semantics: the session stands as it stood, the question just reaches the
owner faster. Where nobody is waiting (`gate: none`, a night run), the channel only announces — the
run has already taken its default and built on it, so there is no answer to apply. See the refusal
of *an asynchronous channel with a deadline* below; this is the half of it that survived.

## 4. A merge policy — a program, not a decision

**The problem.** The kit never merges, by construction and by hook. That is right as a default and
is a dead end for the goal: one instruction from the owner, a finished result in the default branch.
The industry answer in 2026 is not "let the agent decide" — it is to cut the number of human
checkpoints while keeping the policy with the team, and to treat verification velocity as the
bottleneck rather than production speed.

**What to build.**

- A declared **evidence package**: CI green, acceptance green, no open critical or major review
  finding, no `unmet` on any entry this branch touched, the diff inside paths the project allows,
  manual actions of `when: before_merge` all proved. Every item already exists somewhere in the kit;
  what is missing is one place that collects them and one program that reads it.
- **At least one item of the package must not come from the kit.** Everything the package holds
  today is the kit's own word about itself — its tests, its reviewer, its suite. A static analyser
  (Semgrep, CodeQL) is deterministic, costs seconds and no tokens, and is produced by something
  other than the model that wrote the diff. It does not replace `/security-review`, which is
  agentic, expensive and triggered: one goes in the package, the other goes at a suspicious diff.
- **The program merges what passes and never judges.** What fails comes back to the owner as three
  lines, not as a pull request to read.
- The guard hook stays exactly as it is: it forbids *an agent* from merging. A policy is not an
  agent.
- Two modes, and they are the same machine: straight to the default branch, or one pull request with
  a very short body and the manual actions named.

**Blocked on.** Item 1 (the proofs are part of the package) and the branch bookkeeping in item 5.

## 5. Small, and each one already argued

- **One rule for ticking an audit box.** Three actors may do it today — the closing session, `next`,
  `accept` — each by its own paragraph. A program cannot do it (the item is free prose in the
  project's language), so the fix is one rule in `rules/` that the three point at.
- **A batch that is closed is not re-closed.** `epic --advance` is told *decide what follows, start
  it, stop*; measured, five of seven ran the suite, two wrote the batch record, one rewrote the pull
  request body — all of it the closing session's work, done twice. The check is mechanical: a batch
  whose `docs/runs` record, `spent` and `pr` are all present is closed.
- **Parked children's branches, recorded apart from delivered ones.** `close.md` has the batch record
  list every child's branch, parked included — so when the batch's pull request merges, an unfinished
  branch reads as delivered. Nothing can safely retire a branch until these two lists are separable,
  and `next` deletes branches on that list today.

## 6. Later, and deliberately not now

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
| **`@playwright/cli`** | the recommended value of `commands.e2e` on a project with an interface | Microsoft's CLI companion to Playwright MCP, measured at roughly a quarter of the tokens for the same work (≈27k against ≈114k), because it is plain shell commands. MCP is for agents with no filesystem; Claude Code has one |
| **Semgrep** (or CodeQL) | item 4, the evidence package | The only cheap signal in the package not produced by the model that wrote the diff. Studies put generated code at a 25–40% vulnerability rate, and this costs seconds |

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
  `blueprint` is the intake, and what was missing was a trigger and a view. See item 6.
- **Anything for Telegram.** Thirty lines around one HTTP call. A framework here would be the whole
  cost of the feature.

# Refused, with the reason

Nothing here is an open question. Each was proposed, checked against the payload, and refused.

| Proposal | Why it was refused |
|---|---|
| **Batch zero writes frozen acceptance tests** for every scenario before any feature exists | It blinds the only mechanical check the finish has: `check.py --state` counts a scenario as covered when the marker appears in the suite, so the count would read *10 of 10* in the first hour with nothing working. A deliberately red test also has nowhere to live — `unmet` is forbidden for what the run itself was sent to build, and the strict form must be edited exactly when it starts passing. Replaced by: the test rides with the feature that closes the scenario's last step. |
| **The closing session runs the end-to-end tests** after every batch | No command existed to run (now `commands.e2e` does); the driver's 30-minute silence timer would restart the session mid-run; a walk in the tree the children built in proves only that an already-running application still runs; and a red result has no one allowed to close it, since most scenarios are red by construction until the batch that completes them. The home is CI on the batch's branch. |
| **`--sync` also ticks audit boxes and deletes branches** | The state line has been in the program since 0.41.0 — what is distributed is the right to *run* it, deliberately, so that nothing writes as a side effect of reading. A box cannot be ticked by a program at all. Branch deletion is unsafe until item 5 above. |
| **Named views over `run.json`** so readers fetch a subset | Measured on 113 real run files: the whole traffic is 3.9% of a run and views would save 0.5–0.9%. The premise that the file is mostly the template's inline documentation is false — no real run file carries a single `_` key. |
| **A ceiling on the run file's prose fields** (`review`, `notes`, `task` are 51% of its bytes) | The saving is real and small; the cost is losing context that exists nowhere else. Not worth it. |
| **A task carries a free-text "how this is proved"** | Answered with "covered by unit tests" for free, and judged at a moment no command reaches. Replaced by `tasks[].commit`: a SHA either resolves in this repository or it does not. |
| **An asynchronous question channel with a deadline** — the child asks, takes its default, continues, and an answer landing within N minutes is applied | Tried and cut: `wait <hours>` shipped in 1.4.0 with this exact argument and was removed in 2.5.0 because every wait spent its hours and arrived where the run would have arrived anyway. "Applied" has no coherent meaning: an expensive fork is one whose cost *is* the cost of reversing it, and the answer arrives after the commits built on the default. The surviving half is item 2. |
| **Splitting `ship`'s Verify into a subagent** | Priced both ways and it is a wash: the tokens saved by keeping tool output out of the builder's context roughly equal what a subagent's own context floor costs. The remaining argument — a cleaner context — cannot be settled without a measurement nobody has. |
| **The kit learning from its own outcomes** — recording whether a merged feature later needed fixes | Not refused on merit; the owner set it aside as too large and too early. |
| **Rewriting the driver onto the Agent SDK**, so liveness, cost and limits come from the API instead of from parsing transcripts | The three most expensive driver defects all came from that parsing, and the SDK removes the whole class. Refused because it costs the visible tmux session per feature, which is what makes a stalled child rescuable by hand and a limit recoverable by typing one line. The owner values that more. |
| **A pull request per batch instead of one per run** | The owner does not want a pile of pull requests after an `epic`. The early-integration argument was answered separately, by CI on the batch's branch. |
| **Counting an `epic`'s price in the weekly quota** rather than in hours | The owner reads the quota themselves and decides what to start. |
| **A cron picking work up on its own** | It solves the wrong problem: the value is not that the kit starts without the owner, it is that it does not need them after it starts. And it has two real costs — a run nobody started is a run with `gate: none`, so every expensive fork becomes an assumption; and it cannot know the owner is spending this week's quota on another project. Replaced by the continuous mode in item 6. |
| **A separate `intake` mechanism** for new ideas | `blueprint` already is one: `planned` entries, the debt, the audits' work lists. What was missing was a trigger and a view, which are item 6. |
