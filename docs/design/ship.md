# Ship — why it is shaped this way

The behavior is `plugins/agent-kit/skills/ship/SKILL.md`. This file holds only what the command
must not carry: the reasons, and what was rejected. Decided 2026-08-01, against
[kit-v1.md](kit-v1.md) and the numbers in [0.17.0-measurements.md](0.17.0-measurements.md).

## Eleven steps become four

Old: Gate, Task, Ideate, Design, Plan, Build, Test, PR, Review, CI, Docs. New: Design, Build,
Verify, Deliver.

`Gate` and `Task` and `Ideate` died with blueprint: the knowledge layer answers what to build, for
whom, and what is deliberately out of scope, so a step that re-asks those is asking the owner to
repeat themselves. `CI` folded into Deliver — waiting for a pipeline and fixing what it reports is
not a separate judgement. `Docs` died with `docs-reflection`: knowledge has one writer, and all
ship owes it is the entry's machine line.

**No spec document and no plan document.** The blueprint entry *is* the spec, and the task list
lives in the run file. Two generated documents per feature were re-read by every step after them,
which is the cost model this rewrite exists to fix.

## Design is a precondition, not a flag

Whoever creates the run file with an approved design is the designer: ship's own Design step when a
person ran it, the brief when a sprint did, nobody when `mvp` did. So the run file carries
`gate: owner | none` and ship reads it, rather than taking a `--brief` flag whose semantics needed
fifteen lines of explanation in 0.17.0 — most of them about not rewriting the sketch it had just
been told to copy.

The gate itself is conditional. After a good blueprint most features have no fork worth a question,
and a gate that always waits trains the owner to approve without reading. The rule that decides it:

> An expensive fork — stored data, a public contract, permission boundaries, money — is asked when
> someone is present, and becomes a recorded assumption when nobody is. Everything else is decided
> silently in both cases.

That is one rule with two outcomes, rather than an autonomous mode and an interactive mode that
have to be kept in agreement.

## No timer on an unanswered question

Waiting costs nothing: a session stopped on a question burns no tokens. What costs is a *queue*
held up, and a single feature has no queue — everything left in it depends on the answer. So ship
never times out.

It does write `waiting_since` and the fork's text into the run file before asking, and clears them
on the answer. Today that is an honest record of why a run is standing still; if `sprint` later
grows a driver that can spend the wait on another feature, that driver has something to look at
without ship changing.

## Review: one pass that reads the spec, one conditional pass, no fan

Measured on one markdown diff: the `code-review` plugin's fan cost **6.7M for 2 findings**, the
in-house `reviewer` **0.66M for 2 major and 10 minor**. The cost is volume — five agents each
re-exploring the repository — not model tier. So the fan is never run per feature; its place is
once on a sprint's integration pull request, where a repository-wide pass is amortised.

`agent-kit:reviewer` answers what nothing else can: whether this is the feature that was approved.
It is the only reader of the entry. `/security-review` runs on a diff trigger — permissions,
untrusted input, money, files and processes, migrations, outbound calls — and is named as a skip in
the pull request when it does not.

Claude Code's bundled `/code-review` is stronger than any of this and **cannot be invoked by an
agent**. It is not written into the pipeline and not advertised in every pull request either: a
standing line offering it reads as "we did not finish".

Dropped: `/simplify` (quality, not defects, and it costs another suite run), the
`pr-review-toolkit` specialists (overlapping lenses are what produced thirty findings and then
twenty more), and every review round after the first.

## Tests come from the entry, and prove themselves by being written first

The old `tester` agent chose its own coverage, and imagination has no bound — verification was ~70%
of a feature. Now the list is the entry's own lines: what changes, what the initiator sees, what
others see, what can go wrong. One test per line, at the highest seam that can see it. Three to six
per action, and the boundary is what the owner approved rather than what an agent thought of.

"Prove each test can fail" was a separate pass over the whole suite. Writing the risky tests before
the code gets the same proof for free, because they fail. No separate pass, and no `tester`
subagent: the outside view it used to supply now comes from blueprint, and delegation costs a
re-exploration.

The suite runs **once**, at the end of Verify. End-to-end scenarios are not run here — they are the
product's, not the feature's, and belong to a sprint's integration tree or `mvp`'s finish line.

## The pull request is opened after the review, not before

0.17.0 opened it first because the `code-review` plugin needs a pull request and declines drafts.
That plugin is no longer used per feature, so the constraint is gone and the order can serve the
owner instead: push, review, fix, then open. The pull request contains reviewed code from its first
minute.

## What ship does not own

Choosing the next feature, integration, merging, running the scenarios, and the fate of a pull
request after it is opened — all of that belongs to whatever launched it. A stacked feature's PR is
parked by its parent, not by a later stage of the child, which in 0.17.0 required the rule to be
explained in two places.

## Deferred, with the reasoning kept

`sprint` and `mvp` will want to run features unattended, and the shape that would give them
questions on a phone was worked out and **not adopted yet**: a shell driver holding the queue, each
feature as a visible `claude --remote-control` session that can ask and push on its own, and a
timeout in the driver that kills a child stalled on a question, marks the feature blocked, and moves
to an independent one.

It is better than 0.17.0's watchdog — two levels instead of three, children visible in the app,
and the question asked by the agent that actually hit the fork rather than relayed by an
orchestrator with no context. It also adds five mechanisms that exist for one scenario: nobody is
watching at 3am. That is the exact class of spend that inflated the old kit, so `sprint` starts with
the simplest thing that works — one visible session, children in sequence, no driver, no timers —
and the driver is added only if overnight deaths prove to cost more than it does.
