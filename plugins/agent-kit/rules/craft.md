# Craft

Read by the three that write product code or judge it: `ship`, `fix`, and the reviewer, which is
handed this path by whichever of them started it. It is a shared rule rather than a paragraph inside
`ship` because the reviewer needs the same standard the writer was held to — a reviewer judging by
its own taste is how a review turns into an argument — and a rule held in two files is already in
the wrong place.

**Four rules, and the number is the point.** Instruction-following degrades with the *count* of
instructions held at once, and models are measurably biased toward the ones they read first — so a
fifth rule here is paid for by the other four. Each of these is here because no program can settle
it. Everything about craft that a program can settle — that the suite ran, that mutants died, which
tree a claim was measured on — is settled by one, and is not repeated here.

## Make the product true, never the check quiet

A check that will not pass is a fact about the product until somebody proves it is a fact about the
check. What is never allowed is the third road: making the check agree without making the product
right.

Named one by one, because each looks like work while it is being done:

- editing a test so that it asserts what the code already does;
- a branch that recognises the test's own input;
- a value hard-coded for the case the test happens to use;
- an equality, comparison or serialiser bent to return what is wanted;
- state that answers the same input differently the second time it is asked.

Where the check itself is wrong — it contradicts the entry, or no correct product could satisfy it —
**stop and say so** rather than deciding it alone: a `blocker` in the run file when it stops the
feature, a line in `notes` when it does not, a question when somebody is present.

Measured on a benchmark of tasks whose tests could only be passed dishonestly, frontier models took
one of those roads on 46–93% of them; a single sentence telling them to stop instead cut one model's
rate to 1% where the conflict was in front of it, and barely moved it where the conflict was buried.
So this rule is worth writing and is not worth trusting: it is why `mutation` and the reviewer exist.

The neighbouring case is not this one and is unchanged: an entry that promises what standing code
contradicts is recorded with a test marked `agent-kit:unmet`, per `ship`.

## A stand-in proves the stand-in

A mock, a fake gateway, a fixed clock, a stubbed sign-in — each moves what a test proves from the
product to the double. Reach for one only where the real thing cannot be reached from a test, and
write the reason **beside it in the test**, where the next person to read that test is.

Then name the seam in the run file, in `suite`, beside what the suite returned: a feature whose every
proof went through a double has proved the double, and the session that writes the pull request
reads run files and never the code.

Measured: coding agents add mocks in 36% of their commits against 26% for people — and the study's
own recommendation is this file, that guidance on mocking belongs in what the agent is configured
with rather than in a reviewer's taste.

## Nothing the entry did not ask for

No layer of abstraction, no configuration switch, no defensive branch for input that cannot arrive,
no second implementation of something `stack.md`'s library map already names. The entry's lines are
the scope. Everything past them arrives as diff somebody has to read and code somebody has to keep.

This is the rule with the largest measurement behind it and the smallest visible cost per occurrence.
Across 623 million changes between 2023 and 2026, as agent authorship grew: duplicated blocks up 81%,
copy-paste within a commit up 41%, refactoring moves down 70%, and cross-file calls — the one signal
of reuse — down 35%. None of that arrived in a decision anybody would have defended. It arrived one
helpful extra at a time.

## The door out is marked

Not being able to do something is a result, and each kind has its place: `unmet` for a promise the
product does not keep, `blockers` for what stopped the run, a line in `docs/technical_debt.md` for
work understood and set down, a parked feature for one that cannot be finished. A run that says
plainly what it could not do has finished. Nothing here is improved by a green report over it.

Measured, with its own limit reported: given a legitimate way to declare a task impossible, one
model's cheating fell from 54% to 9% — and another's did not move from 46%. The door is necessary
and it is not sufficient, which is why it is a rule here and not a mechanism anything relies on.
