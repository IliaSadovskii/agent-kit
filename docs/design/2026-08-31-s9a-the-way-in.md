# S9a — the way in, for a machine that has nothing installed

Written after building it, 31 August 2026. The step was not in the plan of 22 August; the owner
wrote it in an hour before it was built, inserted before S9, because S9 builds the adapters and
nothing builds the door a person walks through before an adapter is worth having.

## 1 · What it is, in one screen

`agent-kit setup` — a program. No session, no model, no project, no lease, no working copy; it
runs in any directory, and the control surface never requires a live model.

It reads the `providers/` folder — the folder **is** the catalogue, and no provider is named
outside it — climbs the two free rungs of the ladder for everyone (the binary is there; it answers
what it is), prints what the chosen provider declares as its install command, waits for a typed
line, **re-measures**, prints the login command, waits again, and writes the machine's config.

**It runs nothing.** Not the install, not the login. That was the owner's decision before a line
was written, and the reason is in the plan: an installer that reports *done* is the assertion
instead of a trace this whole layer exists against, while a printed command followed by a
re-measurement is a trace. A command needing root is printed and waited on, like every other.

## 2 · What it does not spend

Nothing. The rungs above the free two — does the account answer, does a real job come back — cost a
live session on the owner's subscription, and they stay where they already are: `agent-kit provider
check <name>`, asked by name, one at a time. The walk ends by naming that command, because the
config block is written before the login was ever measured, and without that line the door falls
silent on exactly the machine where the person is lost — the tool installed, the account not.

**A note on how this was read.** The builder reported the plan's own bullet as self-contradictory —
*a program: no session* against *the rungs above cost a real session*. It is not: the sentence says
they cost a session **which is why** they are asked for by name and one at a time, which is a
description of `provider check`. I repeated the builder's reading to the owner before re-reading my
own text, and the review caught us both. Writing *the plan contradicts itself* into a note would
have been the assertion-without-a-trace this kit is written against, in the record of the work
itself.

## 3 · One key, and why a fresh machine could not run at all

Nothing in the config could say *this provider, for everything*. Roles are named one by one and
there are nine session steps, so a machine without nine blocks fell into `no-provider` on its first
session. Generating nine blocks is the wrong answer: S9 or S10 adds a tenth role and the old
machine breaks quietly at three in the morning.

So one line — `machine.provider` — and its reader was already written: `default_provider` in
`driver/session.py`, used until now only by `--provider`. Roles still win where they are named,
`--provider` still beats everything, and the project's own role table is preferred over the
machine's exactly as the driver prefers it.

The strongest argument for the key is not in any design document but in the code it made honest:
`doctor` already printed *roles: none — every role falls back to the default* while no default
existed. The line was a lie; the key makes it true.

## 4 · The door points at it

`agent-kit next` gains one line on rung 1: `no-provider`, naming `agent-kit setup`. Its order is
argued by S8d's own rule rather than by habit — **a rung must not name a command that would be
refused** — and `agent-kit knowledge tell` on a fresh machine is refused for want of a provider. So
`no-provider` stands above `no-description`.

The door gained a *source*, not merely a line: it had never read `config.toml`. So the source is
read in its own `try` and an unreadable config becomes a line in the view rather than toppling a
door whose only refusal is a path typed wrong.

**And the builder found, by reading its own work, that the rung did not consult the project's role
table** — which the driver prefers over the machine's — so it would have reddened on a project that
builds perfectly at night. Its own commit pair, test first.

## 5 · One screen replaced a list

`provider list` printed what `setup`'s reading prints, which makes it a third place obliged to
agree with two others — the defect §5 of the plan is written against. It is gone, and `doctor`
prints the shared reading instead: two screens over one pass, exactly as the door prints its answer
and its view from one pass.

Cost, measured rather than assumed: two tests rehomed onto `doctor`, one line in the README, bare
`agent-kit provider` now refusing by name, and `Declaration.real` — whose only reader was the dead
list — given one in the new reading. `title` and `notes` had no reader at all before this step and
now have one; that is said out loud rather than carried quietly.

Also named out loud: `doctor` is no longer a command that only reads files. It runs `--version` for
every shipped provider on every call.

## 6 · What the bench had to learn, and the two shapes that were wrong

**A pipeline was the wrong shape, and worse than the reason I gave for rejecting it.** I sent it
back because the walk asks at least two questions and a pipeline feeds one. The builder found the
deeper fault: the halves *race* — the line sits in the pipe's buffer, the kit's blocking read gives
no back-pressure, and the shim could finish installing before the kit had taken its reading. The
replacement is two runs: one with the stream closed (it prints the command, meets EOF, exits 8 and
writes nothing), then the person runs what was printed, then a second run. That is also what a
person does.

**The safety check measured the wrong thing.** Both judges checked that `$BENCH/bin/npm` exists,
while running the first word of the command *the kit declares* — so the day that declaration starts
with `brew`, `pnpm` or `curl`, the check would stay green and the judge would run the real command
from the host, network and all, on a disarmed run too. It now resolves the word that will actually
be executed through `command -v` and demands the answer lie inside the case's own bin.

**Proved by breaking, not by argument:** the declared install command was changed to `brew install
claude-code` and both cases refused — *'brew' resolves to nothing at all rather than into this
case's own bin*. The real command was never run.

## 7 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1294 | **1339** |
| `make bench` | 135 of 135 | **139 of 139** |
| `make armed` | 130 + 5 in words | **134 + 5 in words** |

Four traps, none carrying `no_disarm`; every commit imports every module; the bench also ran from
`git archive HEAD` unpacked elsewhere.

## 8 · Breaking it by hand

| broken | what said so |
|---|---|
| an install is called done without re-measuring | `an-install-that-installed-nothing` |
| the block writer drops a person's comments | `a-config-that-was-already-written` |
| the door does not ask whether a session can start | `a-machine-with-no-provider` |
| prose is printed instead of the declared command | `a-machine-with-nothing-installed` |
| the declared install command starts with `brew` | both cases that run it — the safety check |

Two breaks were chosen badly first, and both are worth recording because they are the failure mode
the rule exists for. Making a provider *permanently* not-ready reddened nothing — the case's own
expectation **is** a refusal, so every claim stayed true. And rewriting the config file whole
reddened two cases, because the second write would have erased the first block; the break was too
wide, not the judge.

## 9 · What is held by words, not by a trap

- `machine.provider` — all 139 cases run the kit with `--provider fake`, which beats the default.
- The walk's refusal on an unreadable config — a broken config would have felled the case's own run.
- The question about the quota pool, in both directions.
- The death of `provider list` and the refusal of a bare `provider`.
- The `answers` rung for a level-A provider — the bench ships none; that is S9.
- **The number of questions the walk asks is held from above only.** One question too many meets
  EOF and reddens, and a judge feeds a line that answers nothing so a stray question lands in the
  file where a check finds it. One question too *few* is caught by nothing: the kit's stdin is
  buffered, so counting what was left unread would measure Python's buffer rather than the walk.
  This is written into the judge itself, not only here.

## 10 · The one place the method does not check itself

A review of this step ended on something larger than the step. **There is no trace of the break
round in the repository.** `make armed` answers a different question — *does this case read its own
trap rather than the night around it* — and not *does breaking this mechanism redden exactly one
case*. So the break table in every note of the last five days, this one included, rests on the
builder's report and on my reading of the judges, and nothing measures it the way the kit measures
everything else.

It is the only claim in the method held the way the second version held its claims. Naming it is
not fixing it, and this note does not pretend otherwise.

## 11 · Where the plan was wrong — including the section written that morning

1. **"It asks what it cannot measure: the account and the roles."** On the machine this step exists
   for there is nothing to ask about roles: one provider works. A question with one answer is not a
   question, and the account is only asked once a second provider exists.
2. **"The list is derived from the shipped folders rather than from prose" promises a check the
   bench cannot perform.** The folder is the package itself; giving it an override for the bench's
   sake would be a mechanism nobody else reads. It is held by a test, and the rule that a template
   may not state a check no program performs applies to a *done when* as much as to a template.
3. **The plan never said how a person on a fresh machine finds `setup`.** §5 promised one door;
   without the rung, S9a would have built a door nobody points at.
4. **`agent-kit setup` collides with `agent-kit owner setup`** — two commands sharing a word for
   different things. The first names the second as optional at its end, which is the cheapest
   answer, but the collision was introduced by the plan without noticing.
5. **§"What a programmer actually does" is stale**: `provider add` should never be built — `setup`
   closes it — and `provider list`, which that section shows, is gone.
6. And one in the code rather than the plan: **"two free rungs for everyone" was not true** until
   this step. `version()` lived only in the level-B adapter, so a level-A provider — which is what
   three of the four will be after S9 — could not be asked what it is. Its applicability is decided
   by the declaration now, not by whether a Python method happens to exist.
