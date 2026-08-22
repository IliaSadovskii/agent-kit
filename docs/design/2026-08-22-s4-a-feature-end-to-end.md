# S4 — one feature, end to end

Written before building it, 22 August 2026, so that the next session starts from decisions rather
than from a blank page. S0–S3 are done: the package, the state, the step contract, and Claude Code
measured at level B. What follows is the shape S4 takes and why.

The plan's own words: *Design, Build, Verify, Deliver as steps with contracts. One provider, one
child, no parallelism, a real branch and a real pull request. Done when a small feature on a real
project is built by the third version alone. This is the first moment anything is worth judging.*

---

## The one decision that shapes everything else: some steps are programs

| Step | Who executes it | What it returns |
|---|---|---|
| **design** | an agent | what changes, the seams, **what will prove it — decided before the code**, assumptions with `expensive` answered |
| **build** | an agent | the test first and then the code; files changed, deviations and their cause |
| **verify** | **the program** | the kit runs the project's declared commands itself and records what they printed |
| **review** | an agent | findings, each with a severity; a `blocking` one refuses delivery |
| **deliver** | **the program** | the branch, the commit, the pull request — its body composed from what was already recorded |

This is question 1 of the plan's four — *can this be a program instead?* — applied to the method
itself. An agent cannot lie about green tests it did not run, and a pull request body assembled from
the recorded facts cannot describe work that did not happen. The second version asked an agent to
report both, and the measurement is what that was worth.

So S4 adds a second kind of executor beside the provider adapters: one that runs a declared command
and returns its output. The step contract does not change — an input the driver composes, an
executor, an output the driver validates — which is the point of having frozen it at S2.

## What a project declares about itself

`.agent-kit/v3/project.toml`, written by `agent-kit init`:

- the commands: how this project is tested, linted, built — one fact, one home, and `verify` runs
  exactly these;
- the default branch and what a pull request is opened against;
- which roles run here, if the machine's table is not what this project wants.

`agent-kit init` reads what is already in the repository rather than asking: a Makefile with a
`test` target is the test command, and what it cannot find it says is missing instead of guessing.

## Open questions this step must answer

**Question 6, and it finally has a reader.** A review finding carries a severity; a `blocking` one
makes `deliver` refuse. The contract vocabulary for it exists since S2 (`Records` with an `Enum`);
what was missing was the step that refuses, and now there is one.

**Question 5, the ceiling inside a step.** A step declares whether it may be split. `build` is the
one that can outgrow a window. The window is now measurable per provider (S3), so this can finally
be built rather than guessed — and the plan's warning holds: 1,000,000 tokens is what the window
holds, never what a step should be allowed to spend.

**Questions 7 and 8, the owner's channel.** Settled in the plan: Telegram, thirty lines around one
HTTP call, both directions; a question waits the measured twenty minutes against a phone, then the
default is taken and recorded as an assumption. S4 needs it only if a step asks something. If the
first feature runs without a question, this can wait for the night that needs it — but say so out
loud rather than leaving it unbuilt and unmentioned.

**Question 10, onboarding.** `agent-kit init` above.

## What is already decided and must not be relitigated

- **The sandbox is `IliaSadovskii/kit-sandbox`**, private, cloned at `/projects/kit-sandbox`: a small
  real Python project with `Money`, four tests, `make up/test/down`, and a GitHub remote. The first
  feature is built there. The owner chose a sandbox over beeplish because the second version runs
  there nightly on the same machine and the same quota.
- **The deliver step opens a real pull request** with `gh`, which is authenticated on this machine.
- **A driven session reads the project's `CLAUDE.md` and not the operator's.** Measured, and now
  declared as a flag in `provider.toml`.
- **Version 2 is frozen.** Nothing in `.agent-kit/runs/` is ours.

## How the work is done here

- **Tests land in their own commit, before the commit that makes them pass.** This replaced a
  sentence in a commit message claiming the same thing. Do not put the claim back.
- **A failure carries a named code, never a traceback**, and one exit code means one thing.
- **Nothing lands without its reader.** A field, a file or a record with no consumer is not written
  until the consumer is. Two rounds of review deleted things for breaking this; it is cheaper to
  obey it.
- **The kit runs in a container for tests** (`make up`, `make test`) and **on the host for anything
  touching the real `claude`**, because the container has no agent CLI and nothing may be installed
  on this shared host:

      PYTHONPATH=/projects/agent-kit/src python3 -m agent_kit -C /projects/kit-sandbox <command>

- **Review the step before building the next one.** Three reviews over S0–S3 found ten blocking
  defects between them, and every round paid for itself. Two reviewers is enough: one reading the
  code and running it, one reading the plan.
- **Run it for real before believing it.** The live probe found two defects that 168 passing tests
  did not, and the S3 review found four more that 169 did not. The tests were all clean successes
  and clean failures; nothing outside is clean.

## What S4 is done when

A small feature on `kit-sandbox` — designed, built, verified and delivered by the third version
alone, with a real branch and a real pull request the owner can read. Not a demonstration in a
scratch directory: a pull request with a number.

---

# What S4 turned out to be, written after building it

Two features were designed, built, verified, reviewed and delivered by the third version
alone on `kit-sandbox`, each in one attempt per step: pull requests 1 and 2. That is the
condition above, met.

## What was built, and what each piece answers

| Piece | The question it answers |
|---|---|
| `.agent-kit/v3/project.toml` and `agent-kit init` | one home for what a project declares: its commands, its default branch, its role table. `init` reads the repository rather than interviewing anybody, and names what it could not find |
| a second kind of executor: the program | *can this be a program instead?* `verify` runs the project's own commands; `deliver` composes the branch, the commit and the pull request from what was already recorded |
| `design`, `build`, `review` as contracts | *what trace does it leave?* What the second version prescribed in prose and checked nowhere is a required field: the title, the seams, what will prove it decided before the code, an assumption saying whether it is expensive, a departure carrying its cause, a finding carrying a severity |
| the brief, in the state | *what composes its input?* The one fact no step can derive, enclosed in every step's input, schema 2 with a migration |
| `blocking` refuses delivery | open question 6, and it finally has a reader |
| `splittable`, and the driver that carries a step on | open question 5. A part is kept, the next session gets it, and a continuation spends none of the attempts a refusal would |
| a step's `gate` | a verify whose commands came back red satisfies its contract — recording that is its job — and the run must not go past it |

## Three defects only the live run found

The suite was 267 tests and clean when the first real feature ran. It still showed three
things, which is the whole argument for running it before believing it:

1. The commit subject was the first 72 characters of the design's summary, cut mid-word
   with an ellipsis. The design now writes its own one-line title.
2. A program put its own name where `run show` reads a model, so the record said a
   session had done work no session did.
3. The pull request opened with everything at once — nine kilobytes, the design's full
   prose first. It is now a report: what was done, what is wanted of the owner, and
   anything blocking stay open; the record behind them is folded away.

## What S4 deliberately did not build, said out loud

**The owner's channel — questions 7 and 8 — is not built.** Neither feature asked a
question, so nothing forced it, and the doc above allowed it to wait on that condition.
What this costs today: a step that needs a decision only the owner can make has nowhere
to ask. The design role's prose tells it to say so in `summary` and design the smallest
honest thing instead, which is a worse answer than asking and is knowingly the state of
things until Telegram is built.

**A worktree per child is S8, not this.** `deliver` checks the branch out in the project
itself, so a run leaves the working copy on `kit/<slug>`. With one child and no
parallelism that is correct and cheap; with two it would be the collision the plan
already refuses, which is why S8 exists.

**Nothing writes into the project's knowledge yet.** That is S6, and the fields it will
need are not written until it can read them.

## The numbers from the two runs

Each feature cost about $1.05 across three sessions and roughly four minutes of model
time. No session went past 3.8% of its window, which says the ceiling question is not yet
a real question at this size of feature — it will be measured on something larger rather
than assumed from these.
