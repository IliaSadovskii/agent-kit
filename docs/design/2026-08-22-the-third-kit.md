# The third kit — the plan, 22 August 2026

The kit stops being a Claude Code plugin and becomes a console application for Linux that drives
other people's CLI agents. This note is what was decided on 22 August, why, and in what order the
work happens. Nothing here has been built yet.

---

## 1. What it is

Three layers, and the line between them is one question: *does a program decide this, or a
conversation?*

| Layer | Owns | Runs as |
|---|---|---|
| **Application** `agent-kit` | state, checks, run files, the method, the bench, provider config | a command, Python, installed with uv |
| **Daemon** | slots on this machine, account limits, the queue, the web view | one permanent user process |
| **Driver** | one batch: raise children, watch them, hand over, close, open the pull request | one process per run, dies with it |
| **Adapters** | how a given CLI is started, written into, observed | one module per provider |

The application does not talk to model APIs. It drives agent CLIs, because they bring the tool loop,
the editing, the permissions and — decisively — the subscription. Billing is by subscription only;
per-token keys are out of scope.

---

## 2. What was decided, and why

| Decision | Reason |
|---|---|
| A console application, not a plugin | the method is portable; the packaging is what binds it to one vendor |
| Python, installed with `uv tool install` from git | the whole kit is text rules over git; version is a tag; nothing to publish |
| Linux only, systemd | it is the machine it runs on. Everything OS-specific lives in one module so macOS is one file later |
| Its own permanent daemon, from day one | parallel runs across projects share one machine and one account per provider. Somebody has to count slots and know that a provider is limited until 17:00 |
| Parallelism both inside a batch and across projects | with several providers on separate subscriptions, quota stops being one pool — the old refusal of parallel building expires with it |
| A worktree per child, in the core | two children cannot build in one tree. It also deletes two of the four things the hooks used to guard |
| Four adapters first: Claude Code, Codex, Gemini CLI, OpenCode | three families of native subscription login, plus one door to everything that logs in with a plan key |
| The method is delivered as a prompt, not as a native package | one delivery path for every provider. The application composes the role's core and the paths; the agent reads the rest from disk, exactly as a skill does today |
| No native hooks anywhere | every hook has a replacement outside the agent — see §4 |
| Role → provider + model + effort, with a fallback | so one limited account does not stop the night |
| The method itself moves across, rewritten piece by piece | the order of work is the only part of the old kit proven by live nights; the prose around it accumulated caveats |
| Version 2 is frozen | the running beeplish batch finishes on it and is not touched. No further edits unless a run breaks |
| A project's knowledge is read, its unfinished runs are not | knowledge is the owner's years of work; a run file is a week |
| A bench with planted traps | with more than one provider, "checked by a live overnight run" stops working — a bad model and a bad night become indistinguishable |
| Built on a bare branch in this repository | so that no defect is carried over by copying. What is carried deliberately is the *reasons*, written out first |

---

## 3. Providers

Two levels, declared in the provider's own block.

| Level | Can | Costs | Good for |
|---|---|---|---|
| **A. Started** | raise a session, write into it, stop it | a block of config | short jobs: a review, one fix |
| **B. Observed** | plus: is it alive, how much context, is it limited and until when | a block plus a small parsing module, or HTTP where the provider offers it | a session that runs for hours unattended |

Everything a block declares: the binary and its flags, the full-access flag, the project instruction
file, how a model is chosen and how effort is set, where the session's record lives, what the
provider can and cannot do, the plan's quota. Two levels of settings, the same shape the kit already
uses for verification: the kit declares what a provider is *asked*, the installation answers.

The program refuses to assign a level-A provider to a role that runs unattended. A missing capability
is never silent.

**OpenCode is the single door for anything that logs in with a plan key** — GLM, MiniMax, DeepSeek,
Qwen. It has an HTTP server and a headless mode, so its adapter reaches level B without parsing any
transcript at all, which makes it the cheapest of the four.

**Substituting the API address inside Claude Code is refused.** It costs the prompt cache, blinds the
context counter, breaks limit detection, and is a configuration Anthropic does not support.

---

## 4. What replaces the hooks

| What a hook holds today | What holds it now |
|---|---|
| refuse merge, force-push, push to the default branch | a git `pre-push` hook — catches the agent and the human, works with no agent at all |
| refuse e2e inside a build, refuse switching branches in a tree another run holds | a worktree per child: the situation cannot arise |
| refuse to end a turn mid-step | the driver, from outside: it already sees a silent session with an open step, and writes "continue". One poll slower than a hook |
| close the session when an epic is finished | the driver already does this |

Three of the four get better. One gets slower. In exchange there is one mechanism instead of one per
provider, and no package to build for anybody.

---

## 5. The knowledge, and the door

The concern the owner raised, and it is the sharpest thing on this page: **the kit relies on a person
choosing the right command at the right moment.** Nine commands are nine doors, each with its own
checks. Miss the door, miss the check. `next` carries more than the rest, which is not its merit — it
is a sign the others know less.

The map says the same from another side: a finding has no code and no level, the exit code means
three different things across three modes, so nothing can be automated on it; `--advance` reads no
blocks at all; `expensive` was unanswered on 28 of 73 assumptions in one measured run.

The intended shape: **one door instead of nine.** The kit knows the project's state and what is legal
next; the person asks *what now* rather than choosing from a list.

**What is broken in the exchange is measured, not guessed.** Over the beeplish artefacts: which marks
were written, which of them anybody read at the following step. The gap between written and read is
the defect list. That measurement is the first piece of work on this page.

---

## 6. Order of work

0. **Write out what the old kit held** — every rule, refusal and finding worth keeping, with its
   reason. This is what crosses to the bare branch; the code does not.
1. **Measure the knowledge exchange** over beeplish: written against read. Produces the defect list
   the third version's design answers.
2. **The skeleton**: the command, the run state on disk, the checks, one adapter (Claude Code) at
   level B, one driver, one child, no parallelism. First proof it works at all.
3. **The bench**: a sample repository with planted traps and script judges. From here on every claim
   is checked against it.
4. **The daemon**: slots, limits, the queue, autostart.
5. **Parallelism**: a worktree per child, waves by the `needs` graph, merging several branches.
6. **Adapters two to four**: Codex, Gemini CLI, OpenCode. Each is a config block plus a small module,
   and each is run through the bench for its level.
7. **Roles across providers**: the table with fallbacks, and the first night where the builder and the
   reviewer are different providers.
8. **AoE as an optional launcher**, so the owner's sessions appear in the dashboard he actually uses.

---

## 7. Open, to be settled on the way

- **Which CLIs AoE can raise.** If it does not know Codex, Gemini CLI or OpenCode, sessions on those
  providers will not appear in the dashboard. To check before the adapters.
- **The context ceiling is per provider.** 210k was fitted over 119 Opus sessions and follows the price
  of a token and the cache, not the size of the window. Every provider is measured again.
- **What the roles actually are.** Building, review, framing, closing, the interview at the gate — the
  list is inherited from the old kit and has never been written down as a list.
- **How OpenCode behaves as an agent.** Its plugins and hooks are TypeScript, its skills are its own
  format, and its quality on a long unattended run is unknown.
- **The web view.** The daemon can serve one; AoE already does. Decide when the daemon exists.

---

# What the measurement found, 22 August 2026

Measured over beeplish: 246 run files, 437 transcripts, the whole git history of `docs/knowledge`.
Scripts in the session scratchpad; every number below was recomputed after a challenge.

## Blocks, over the project's life

| Kind | Written | Closed | Open today | Median life |
|---|---|---|---|---|
| `assumed` | 217 | 126 | 91 | 3 days |
| `frame` | 197 | 116 | 81 | 1 day |
| `stale` | 35 | 35 | 0 | — |
| `found` | 12 | 11 | 1 | 3 days |
| `accepted` | **0** | 0 | 0 | — |

The knowledge does not silt up: the oldest open block is five days old. `accepted` has never been
written once — `advise` has a template, a block, a closing rule and no writer.

## Assumptions

671 written into run files. `expensive` answered on 86% — up from 62% in the 19 August measurement,
so that fix worked. 182 answered `expensive: true`; 217 `[assumed …]` blocks exist. **Nothing has
ever compared those two lists**, and the program can read both.

## Reading

A claim that collapsed twice under checking, which is the point of writing it down:

| Claim | Number |
|---|---|
| "almost half of build sessions never pull their entry" — first pass | 44% |
| after removing audits and debt teardowns, which have no entry at all | 22% |
| after checking whether they opened the knowledge directly instead of `--brief` | **3%** |

Of 181 substantial sessions building a feature that names an entry, **6** touched the knowledge in
no way at all. The defect is not that it happens often. **The defect is that nothing noticed** —
not during the run, not at the close, not in review. A prescribed step that leaves no trace cannot
be missed by anybody.

## The inventory: what `ship` prescribes against what is checked

Checked by the program (34 checks): `entries` resolve to real entries, `assumptions` are records,
`expensive` is answered, a closed task names its SHA, `suite` and `proved_at` agree with the branch,
`mutation`, `verified` covers the kinds, `pr` is not empty, the run was written to `docs/runs/`.

Checked by nothing:

| Prescribed in prose | Trace | Check |
|---|---|---|
| read the parent run's file | none | none |
| read the code the entry touches, and its callers | none | none |
| open `stack.md` and obey its `[frame …]` block | none | none |
| name the seams | field `seams` | **no reader in `check.py`** |
| the owner's answer into `answers` | field `answers` | **no reader** |
| a departure into `deviations` with its cause | field `deviations` | **no reader** |
| `deferred`, `closed_debt` | fields exist | **no reader** |
| decide the kinds of verification *before the code* | `verified` | checked at the end only; that it was decided early is unknowable |
| write the test before the code | none | none |
| record as you go, not at the end | none | none |
| an expensive assumption owes an `[assumed …]` block | both sides exist | **nothing joins them** |
| remove the `unmet` mark when the feature makes it true | none | none |

**One line: the kit checks the end state of delivery. It checks no act of reading and almost no act
of writing into the knowledge.**

## What this requires of the third version

1. **The driver composes a step's input.** Reading stops being a step — what must be read arrives
   enclosed. There is nothing to check because nothing can be skipped.
2. **Writing into the knowledge goes through the program.** The model returns fields; the driver
   writes the file. "An expensive assumption with no block" becomes an impossible state rather than
   an oversight.
3. **Every field has a reader or it does not exist.** Six fields are written into nothing today.
   That is the kit's own rule about four answers, never applied to itself.

A step is therefore: an input the driver composes, an executor, and an output the driver validates
before the next step starts. A debate between two agents falls out of that shape for free — same
input, two executors, the program compares, and a third pass shows each the other's answer. No
direct channel between agents, because nothing could then check what they agreed.

---

# The principles the measurement produced, and how they are applied

## The one number the whole architecture rests on

| How a step is held | How often it is obeyed |
|---|---|
| by a program — the batch record, `branches`, a task's SHA, `expensive` | **100%** from the day it was introduced |
| by prose — `--brief`, reading `stack.md`, applying blocks, `--advance` not redoing the close | **29–56%** |

Both halves were measured on the same project over the same weeks. `docs/runs/<batch>.json` arrived
on 11 August and every batch since has written one — 28 of 28. `branches` arrived on 15 August: 19
of 19. Against that, five of seven `--advance` sessions redid work the prose forbids them to redo.

This is not "models should follow instructions better". It is that **prose is obeyed two times in
three and nobody notices, and a program is obeyed always.**

## Four questions every mechanism of the third version answers

Asked when the mechanism is written, not in a survey beforehand — a survey is read at the wrong
moment. These join the kit's existing four (who writes, who reads, who may close, what becomes
impossible without it):

1. **Can this be a program instead?** If a rule can be checked mechanically it stops being a rule
   and becomes a step of the driver.
2. **If an agent must do it, what trace does it leave?** A step whose skipping is invisible is not a
   step, it is a hope. The trace is a field the driver writes or validates, never a claim the same
   model makes about its own work.
3. **What composes its input?** Anything that must be read is enclosed by the driver. Reading is
   never an instruction.
4. **Who reads what it writes?** A field with no reader is deleted, not documented. Six exist today:
   `seams`, `answers`, `deviations`, `deferred`, `closed_debt`, and half of `notes`.

## The order for each mechanism as it is rewritten

1. Read what the old one held, from the frozen branch — rules, refusals, the findings it was bought
   with.
2. Sort each rule by its evidence: a test, a named failure, or prose alone. Prose alone does not
   travel — see the table in §2.
3. Answer the four questions above.
4. Write the program, the test first.
5. Only what could not become a program goes into the prose of a step, and it goes into the step's
   own input, nowhere else.

## How the third version is built

**By hand, not by the second version.** The temptation is real and so are four reasons against it:
the old method builds from a project's knowledge entries, which the kit does not have; a session
editing `SKILL.md` carries that same text as instructions to itself; version 2 is frozen and its
nightly run on beeplish shares the machine and the quota; and the first work is architecture, which
is a conversation rather than a batch.

**Revisit once the skeleton and the bench exist.** A list of independent modules is a real batch, it
runs in a worktree where nobody edits the kit's own prose, and it is the first honest test of the
third version on itself.

---

# The build order

Replaces the sketch in §6, which listed the work without saying what holds it together.

## Five rules the order obeys

1. **A step ends green and ends demonstrable.** Something runs, something is tested, and there is a
   sentence naming what can now be done that could not be done before. No half-mechanisms left
   standing overnight.
2. **The test is written first**, because that is what makes the proof free — the same rule the old
   kit gave its build sessions and never checked.
3. **Dependencies flow one way**: state → the step contract → the driver → adapters → the daemon →
   parallelism. Nothing is built before the shape it writes into is frozen.
4. **A frozen shape is never quietly changed.** If a later step needs a different one, changing it is
   its own step, done first, with a migration and a test — never a side effect of building something
   else.
5. **Nothing lands without its reader.** A field, a file or a record with no consumer is not written
   until the consumer is.

## The steps

**S0 · The package.** `agent-kit` as a command: `uv` project, config loading, the XDG paths, logging,
exit codes that mean one thing each. No domain in it at all.
*Done when* `uv tool install` from this branch puts a working command on PATH and `agent-kit --help`
answers. *Why first:* the install path is where late surprises are most expensive.

**S1 · The state.** What a run is, as data: a versioned schema, read and write through one module,
validation on both sides, a migration hook. The state advances only through the program — no field is
ever written by an agent's editor.
*Done when* a run can be created, advanced and read back, and an invalid state is refused with a
named reason. *Why here:* everything later writes into this, and rule 4 makes a late change costly.

**S2 · The step contract.** A step is an input the driver composes, an executor, and an output the
driver validates. Registry, one fake executor, no real CLI anywhere.
*Done when* three tests pass: a missing output leaves the step unpassed, an output that does not
satisfy the contract is refused, and a valid one is recorded with its trace. *Why before adapters:*
this is the principle the whole architecture rests on. Proving it against a fake agent costs nothing
and finds the design errors while they are still cheap.

**S3 · The first adapter, Claude Code.** Level A first — start, send, stop, and the session's real
name reported rather than guessed. Then level B — alive, context size, limit and its reset.
*Done when* the machinery of S2 runs one real step in a real session, and the driver can say how much
context that session holds. *Why after S2:* the adapter plugs into machinery already proven.

**S4 · One feature, end to end.** Design, Build, Verify, Deliver as steps with contracts. One
provider, one child, no parallelism, a real branch and a real pull request.
*Done when* a small feature on a real project is built by the third version alone. This is the first
moment anything is worth judging.

**S5 · The bench.** A sample repository with planted traps and judges that are scripts.
*Done when* one command reports which mechanisms fired and which did not. *Why here:* before S4 there
is nothing to judge; after S4 every further change needs judging, and a live night can no longer
answer for it.

**S6 · The knowledge, through the program.** The model returns fields, the driver writes the file and
the mark. The join the second version never made — an expensive assumption owes a block — becomes an
impossible state rather than an oversight.
*Done when* a feature cannot be closed while an expensive assumption has no block, and the bench has
a trap proving it.

**S7 · The daemon.** Slots on the machine, limits per account, the queue, autostart under systemd.
Stop and skip (open question 9) belong to it. Its page shows and does not act, until somebody asks
for more: showing is what was missing, and every button is a way to break a night from a bus.
*Done when* two runs on one provider account wait for each other correctly instead of sleeping blind.
*Why not earlier:* until S4 there is only ever one run.

**S7a · The owner's channel.** Telegram, both directions, as settled at the foot of this note. Its
own step and not a half of S7: the daemon is about a machine's slots and the channel is about a
person's phone, and folding them together is what made the second version's control surface a live
session. *Done when* a question waits its measured twenty minutes against a phone, and an
unanswered one takes the default and records it as an assumption.

**S8 · Parallelism.** A worktree per child, waves from the `needs` graph, several branches merged in
an order the program decides.
*Done when* a batch of three features that depend on nothing builds at once and all three land.

Two things earlier steps deliberately left for this one, because neither has a unit until
batches exist:

- **Skip** (open question 9). S7 built stop and refused to build skip beside it: *its unit is a
  feature inside a batch, and there are no batches until S8. A `skip` with nothing to skip is a
  field with no reader wearing a command's clothes.*
- **The machine's own ceiling is not queued.** S7's queue orders waiters per account. Two runs
  waiting on *different* accounts, both held back by `machine.max_sessions`, are ordered by
  whoever polls first rather than by who asked first. S7 named it and refused to fix it on a
  guess — with one provider configured there is one account. Parallelism is what stops it being
  a guess.

**S9 · Adapters two to four.** Codex, Gemini CLI, OpenCode. Each is a config block plus a small
module, and each is run through the bench for its level. The context ceiling is measured per
provider, never inherited.
*Done when* the bench reports a level for each, and the numbers behind each ceiling are written down.

**S10 · Roles across providers.** The table with fallbacks, and the first night where the builder and
the reviewer are different providers.
*Done when* one batch runs with three providers and the bench says the result did not get worse.

**S11 · AoE as an optional launcher**, so sessions appear in the dashboard the owner actually uses.
*Done when* the kit works identically with it and without it.

## What is deliberately not in this order

The two-agent debate. It is one flag on a step once S2 exists — same input, two executors, the
program compares — and it costs double, so it waits for a step that has been measured as hard.

---

# Where everything lives

Three places, each with one owner. A fact has one home; where two would want it, the second reads
rather than copies.

| Place | Owner | Dies with |
|---|---|---|
| the kit's repository | the kit | nothing — it is the source |
| the machine — `~/.config/agent-kit`, `~/.local/state/agent-kit` | the installation | the machine |
| the project — `.agent-kit/` and `docs/` | the project | never; `docs/` is committed |

## The repository

```
agent-kit/
  pyproject.toml
  src/agent_kit/
    cli/                 the command surface
    state/               what a run is: schema, read/write, migrations
    steps/               the step contract and the registry of steps
    driver/              running a run: compose input, execute, validate output
    knowledge/           reading and writing the project's knowledge, by program
    providers/
      base.py            the adapter contract — the only file that defines it
      claude_code/
        adapter.py       what cannot be declared: transcript, limits, context
        provider.toml    what can: binary, flags, model, effort, capabilities, level
      codex/
      gemini_cli/
      opencode/
    daemon/              slots, limits, the queue, the web view
    bench/               the runner and the judges
  method/                the prose the driver encloses in a step's input
    roles/               build.md, review.md, frame.md, close.md, interview.md
    rules/               what more than one role needs
    templates/           the shape of a record, read by whoever writes one
  bench/cases/           the sample repository and its planted traps
  docs/design/           the arguments
  tests/
```

**A provider is a folder and nothing else.** Adding one at level A is `provider.toml` alone;
promoting it to level B adds `adapter.py` beside it. Nothing outside `providers/` ever names a
provider — the registry reads the folder.

**The method is prose in `method/`, not a package.** No `.claude-plugin`, no marketplace, nothing
installed into any agent CLI. The driver reads a role's file and puts it in the step's input, which
is why a provider with no skills is not a lesser provider.

## The project

```
<project>/
  .agent-kit/
    project.toml              what this project declares: commands, verification, roles
    runs/<slug>/
      run.json                the run's state — written by the program only
      steps/<n>-<name>/
        input.md              exactly what the driver enclosed
        output.json           what came back, after it satisfied the contract
        raw.txt               what came back before that
        meta.json             provider, model, cost, timing, attempts
  docs/
    knowledge/                the owner's, unchanged
    runs/<slug>.json          the durable record of a batch
    manual.md, technical_debt.md
```

**The step directory is where agents meet.** Two sessions never talk; one writes `output.json` and
the driver hands it to the next as part of an `input.md`. That makes every handover a file with a
name — replayable, diffable, and answerable after the fact, which no conversation between two live
sessions could ever be.

It is also what makes the debate cheap when its turn comes: `output-a.json`, `output-b.json`, and a
`verdict.json` the program wrote by comparing them. No new mechanism, one more file.

`raw.txt` beside `output.json` is deliberate: when a contract is not satisfied, the reason has to be
readable without re-running the night.

## The machine

```
~/.config/agent-kit/config.toml     accounts, role table, per-provider overrides
~/.local/state/agent-kit/
  daemon.sqlite                     slots, limits, the queue, the project registry
  logs/
```

**Two levels of provider settings, and they are not the same kind of thing.** `provider.toml` in the
kit states what is true about the tool. `config.toml` on the machine states what this installation
chose — which account, which model, which role. The kit never ships a choice; the machine never
ships a fact.

---

# The control surface: how a person configures this

There is no control *session*. The second version made the owner's own agent session the window,
which meant configuring anything required a live model somewhere. A session is a worker here, never
a controller.

**One truth, three editors.** `~/.config/agent-kit/config.toml` is the configuration. The commands
edit it safely, the daemon's page edits it from a phone, and a text editor edits it directly. All
three write the same file, and it is readable and commentable by a person.

`daemon.sqlite` never holds a setting. It holds only what is true right now — which slots are taken,
which account is limited until when, what is queued. Settings survive a wipe of it; state does not
survive a reboot and should not.

## What a programmer actually does

```bash
agent-kit provider list                 # what the kit knows, and what this machine has
agent-kit provider add codex            # writes the block, then runs the checks
agent-kit provider check codex          # the level it earns, measured rather than claimed
agent-kit role set build codex --model gpt-5.4-codex --effort high --fallback claude_code
agent-kit doctor                        # everything configured, everything missing, in one screen
```

**A provider's level is measured, not declared.** `provider check` runs the ladder: the binary is on
PATH, the login answers, the full-access flag is accepted, a one-shot job returns something, the
session's context and limit are readable. It prints A or B and says which rung failed. A level
nobody measured is the same class of claim as a rule nobody tested.

## The shape of the file

```toml
[machine]
max_sessions = 4                  # the ceiling the daemon enforces, memory before quota

[providers.codex]
enabled  = true
model    = "gpt-5.4-codex"
effort   = "high"
max_sessions = 2                  # of the machine's four, at most two here
[providers.opencode]
enabled  = true
model    = "glm-5.3"

[roles.build]
provider = "codex"
fallback = ["claude_code"]
[roles.review]
provider = "opencode"
[roles.interview]
provider = "claude_code"
```

**Two levels of settings, and neither may hold the other's kind.** `provider.toml` in the kit states
what is true about a tool — flags, capabilities, where its transcript lives. `config.toml` states
what this installation chose — which model, which account, which role, how many at once. A project
may override the role table in its own `.agent-kit/project.toml`, and nothing else.

**Secrets are in neither.** `agent-kit auth` writes them to `~/.local/state/agent-kit/secrets`, mode
600, or leaves them to the provider's own login where it has one. `config.toml` is safe to commit
and safe to show.

## The daemon's page

The same operations, plus what only it knows: what is running now, what is queued, which account is
limited and until when, and the last lines of each live session. It is the reason the daemon exists
at all — a phone cannot read a config file over ssh, and that is the whole difference.

Read-only until it is asked for more: showing is what was missing, and every button is a way to
break a night from a bus.

---

# What is still open, ordered by the step that needs it

Written before building rather than discovered during it. Each says which step forces the answer,
and carries a proposal where one is obvious.

**Questions 1, 2, 3, 4, 5, 6, 10, 11 and 12 are answered** — S0–S6 built them, each as its
proposal said, and the notes for those steps carry the arguments. What is left open is 7, 8
and 9, and 9 is S7's to build. The proposals below stand as written; where a step departed
from one, its own note says so.

## Needed by S1 — the state

**1 · Two kits on one project.** Version 2 is frozen but its nightly run on beeplish writes
`.agent-kit/runs/<slug>/run.json` under its own schema. The third version writes the same path with a
different shape, and the second version's checker judges anything it finds there.
*Proposal:* the third version writes `.agent-kit/v3/` and never touches `.agent-kit/runs/`. One
directory, one owner, no version sniffing. Deleted the day the second version is gone.

**2 · Who may write a run file, and how they do not collide.** The driver writes it, the daemon reads
it, and under parallelism several drivers exist at once. Two writers on one file is how a night ends
with a truncated record.
*Proposal:* one writer per run — its own driver — and everyone else reads. Cross-run facts (slots,
limits) live in the daemon and never in a run file. Writes are atomic: write beside, rename over.

**3 · The kit's own version, in the state.** A run file written by 3.0 and read by 3.2 has to say
which it was. The old kit learned this the expensive way.
*Proposal:* a `kit` field, refused if newer than the reader, migrated if older.

## Needed by S2 — the step contract

**4 · What happens when a step fails.** Missing output, an output that never satisfies the contract, a
session that goes silent, a provider that dies. This is the sharpest gap in the plan: the contract
defines success and says nothing about the other three.
*Proposal, and it wants your eye:* three attempts on the same provider with the reason enclosed each
time, then the role's fallback provider, then the run stops and says why. Never silent, never
infinite. What must **not** happen is the second version's nudge — typing "continue" at a stuck
session, which is a guess dressed as a recovery.

**5 · The ceiling, inside a step.** Steps make handover cheaper — each has its own composed input —
but one build step can still outgrow its window.
*Proposal:* a step declares whether it may be split. If it may, the driver closes the session at the
ceiling and starts the next with the same input plus what the previous produced. If it may not, the
step is too big and that is a design error to fix rather than to survive.

**6 · What the reviewer's verdict does mechanically.** A review that only prints is the second
version's problem restated. A finding needs a level, and a level needs a consequence — one blocks the
pull request, another rides along in it.
*Proposal:* the review step's contract is a list of records with `severity`, and `blocking` findings
make the deliver step refuse. That is the whole of it.

## Needed by S4 — the first real feature

**7 · The owner's channel, and it is a real hole.** The second version reached the owner by typing a
line into their tmux session, which became a phone notification through Anthropic's app. That
dependency dies with the plugin, and nothing replaces it. `docs/planned.md` item 3 proposed Telegram —
thirty lines around one HTTP call.
*Needs your decision:* Telegram, or the daemon's page with a push, or both.

**8 · Asking a question mid-night.** With no channel there is no question, so this rides on 7. The
second version's answer was a twenty-minute window against a phone, then the default is taken and
recorded as an assumption. It was measured and it worked.
*Proposal:* keep exactly that, and make the waiting a state of the step rather than prose.

**9 · Stop and skip, while a night runs.** The second version read a `control` file between features.
*Settled, and S7 builds it:* the daemon owns it — `agent-kit stop <run>`, `agent-kit skip <slug>` —
and the driver reads it at a step boundary. Same mechanism, an address instead of a file.

**10 · Onboarding a project.** `agent-kit init` in a repository: write `project.toml`, read what the
second version left in `docs/knowledge/`, migrate the format, say what is missing.

## Needed by S5 — the bench

**11 · What the bench is allowed to spend.** Four providers times a suite of cases is real quota, and
a bench nobody can afford to run is a bench nobody runs.
*Proposal:* a declared ceiling per bench run, and cases marked cheap or full — the cheap set on every
change, the full set before a release.

## Needed by S0, and cheap

**12 · Names, decided once.** The binary is `agent-kit`. The branch prefix stops being `claude/` and
becomes `kit/`, which is a lie on nobody. Commit messages and code in English; what the owner reads
in the project's language, as before.

**13 · The kit's own CI, and a provider that is not real.** Everything up to S3 must be testable with
no provider installed and no network — the second version's tests ran with no tmux and no `claude`,
and that is why they ran at all. A fake adapter in `providers/fake/` is a test fixture and ships with
the kit.

---

# Two answers, settled 22 August

**A failing step: three attempts, then the fallback, then a stop.** Each attempt encloses the reason
the previous one was refused — an attempt that repeats the same input is not an attempt, it is a
coin toss. If three fail, the role's fallback provider gets one. If that fails, the run stops and
says which step, which provider, and what the output was missing. Never silent, never infinite, and
never the second version's nudge: typing "continue" at a stuck session is a guess wearing the
clothes of a recovery.

**The owner's channel is Telegram, and AoE is not it.** They do different jobs and the plan conflated
them:

| | AoE | Telegram |
|---|---|---|
| what it is for | you came to look and want to intervene | the night came to find you |
| works when the kit runs without AoE | no | yes |
| covers a one-shot job with no live pane | no | yes |
| wakes a phone | no | yes |

So: news and questions go to Telegram — thirty lines around one HTTP call, both directions. A
question waits the measured twenty minutes against a phone; unanswered, the default is taken and
recorded as an assumption, exactly as the second version measured it. The waiting is a state of the
step, not a sentence of prose.

AoE stays what it is: the optional launcher that makes sessions visible and typeable when you open
it yourself.

---

# The layer this plan missed, 26 August 2026

Written four days after the plan, against S0–S8 built. It adds steps rather than arguments: what
follows belongs in the build order above and was absent from it.

## How it was missed

The conversation that produced this plan ran on 21–22 August and never reached the command surface.
It settled the kind of application, the providers, the daemon, the prompt in place of skills, the
refusal of hooks, the repository layout and the order of work. Asked, near the end, to predict what
had not been discussed, it produced §7 — thirteen open questions, every one of them about
execution: a failing step, the ceiling inside a step, the reviewer's verdict, the owner's channel,
stop and skip. Then the session ended and S0 began the next morning.

§5 named the defect of the second version — nine doors, each with its own checks — and promised
**one door instead of nine**. No step in the order builds that door, and nothing records what
became of the other eight. The promise was read as an answer.

So the second version's two halves came across unevenly. The half that **builds a feature** is here
and is better than it was: a step is a contract, the driver composes the input, the program writes
the knowledge, a trap proves each mechanism. The half that **says what the product is and what to
build next** is not here at all.

## What has no writer and no reader today

Measured over `src/`, not remembered:

| The second version held | The third |
|---|---|
| `blueprint` — the product's own description, dictated by the owner and sorted into records | nothing |
| `next` — where the project stands, one command named with its reason | nothing; §5 promised its replacement and no step owns it |
| `audit` — six lenses, code against the description, a work list | nothing |
| the composing sitting of `sprint` — the whole batch in front of one person, the night's questions pre-answered | the owner writes a TOML by hand |
| the catalogue of kinds of verification, answered per project with a command or a dated refusal | `[commands]` in `project.toml`, and nothing that asks about a kind nobody declared |
| a feature's record of what will prove it, walked again by Verify | `design.verification`, whose only reader prints it into the pull request |
| `docs/technical_debt.md` — where *works, but badly* went | nothing |
| `stack.md`, `product.md`, parts marked `walked:` or `derived` | nothing |
| block kinds `assumed`, `frame`, `stale`, `found` | `assumed` alone |

Two of those are worse than omissions.

**The newest mechanism of the second version never crossed.** The catalogue of kinds shipped on 20
August at 01:23; this plan was written on the 22nd at 01:46. The measurement the plan rests on ran
over runs made before it, which is why the inventory in this very document files `verified` under
*checked at the end only* — true until two days before the plan, and false after.

**And S6 made a promise to S8 that S8 did not keep.** `frame` — what the features of one batch must
build alike — was to arrive with batches. Batches arrived; the word appears nowhere in S8's note or
its code. In the second version it was the second most written kind of block: 197 of them.

## Two sessions, and why they break no rule

*The control surface* above says there is no control **session**, and the reason it gives is narrow:
the second version made configuration require a live model. That rule is about providers, roles and
limits — it is not about talking to the owner.

Two interactive sessions are therefore legitimate, and both are missing:

- **the knowledge session** — the owner says whatever they came to say about their product, and it
  is sorted into records;
- **the composing sitting** — the whole evening in front of one person before any of it runs.

Neither configures the machine. Both are the kit's oldest shape: *ask where somebody is standing,
never in the night where nobody is.* The twenty-minute window of S7a is what happens when the night
has a question anyway; it is not a substitute for the hour before it.

## What the restoration is held to

Not the second version as it stood — the second version **minus the defects already found in it**.
The map of 21 August carries 58 findings over the whole kit; this plan, written the next day, used
three of them, all about the command surface. The rest were never read, and a third of them are
about exactly this layer. Each step below cites the ones it closes by number.

## The recovered steps

Numbered after S8 rather than after S11, the way S7a was inserted: their dependencies are the
knowledge store (S6), the step contract (S2), `asks` (S7a) and the batch (S8), all of which exist.
Whether the adapters of S9 run before or after them is a choice about what to spend a night on, not
a dependency.

**S8a · The knowledge that has a writer.** An interactive session, and the only shape that fits what
it does: the owner talks, at any length and in any order, and nothing about that is sorted for them.

- **The reading goes up before anything is written** — *new, refines, contradicts, unchanged* — and
  the last row may not be dropped. Comparing one telling against fifty records means reading fifty
  records, and the cheap way to look thorough is to read a third and report three differences
  confidently. A line per record touched, including the ones that did not move, is what a third of
  the reading cannot produce.
- **Only contradictions are asked.** Everything else is stated and written.
- **The parts of the product, not the slots of the kit.** Nobody holds their product as actors and
  entities; they hold it as sign-in, the lesson, the account. The slots are what the answers are
  written into, never the route the questions walk.
- **Each part carries `walked: <date>` or `derived`** — what the owner told, against what the kit
  worked out from the code and they have never confirmed. Without that mark a description cannot
  admit that half of it was written by an agent, and every later run reads both halves as equally
  true.
- **Three destinations, one test between them**: this changes what the product must do — the record;
  it does what it should and does it badly — the ledger of S8f; it does not work at all — the ledger,
  saying so. Say the counts back, because the second number is the one nobody can see anywhere else.
- **A template may not state a check no program performs** (finding 53). Prose promising a
  cross-check nobody runs is the defect this whole plan exists against, and it is sitting in the
  second version's own templates.
- **The absence of a description is a named state, never silence** (findings 9, 10, 25). The second
  version answered zero, quietly, on a project with no `docs/knowledge/`; the third inverted the same
  mistake — `design`'s contract is *stricter* for a project that keeps knowledge, so the kit asks
  least of the project it knows least about. Both are one defect: missing is not the same as fine,
  and only one of them can be said out loud.

*Done when* a repository with no `docs/knowledge/` ends one sitting with a description the design
step can read; every record is traceable to a line the owner said or is marked `derived`; the same
telling run twice rewrites rather than duplicates; and a bench trap proves that a project with no
description is refused by name rather than passed in silence.

**S8b · An evening composed with the owner.** What `batch new <file>` does today, done in front of
somebody. Two things a child cannot supply: the whole batch is visible at once, and the owner is
here. So the sitting **pre-answers the questions the night will have nobody to ask**, and then gets
out of the way.

- **The declaration stays the artefact.** The sitting fills it; `batch new` still reads it. One door.
- **The `frame` block** — what every feature of this batch must build alike — is written here, where
  the whole batch is visible at once. This pays S6's promise to S8.
- **The gate, and it is the only place that stops anything.** A batch does not start while a kind of
  verification is unanswered (S8e), while the MVP bounds are unwritten, or while the scenarios have
  no endings. Dozens of features run afterwards with nobody watching, so the class of defect nothing
  catches is asked about while the owner is still standing. The second version refused to start an
  epic without a declared way to run and to test the product, and that refusal was fatal by design.
- **The MVP bounds and the scenarios** are read from the description where it has them and filled
  here where it does not (findings 41, 42: one was a hard-coded English string, the other dead code).

*Done when* a batch can be composed without anybody writing TOML by hand; the graph it produces is
the shape `batch new` already accepts; a `frame` block reaches the knowledge with a named writer; and
a bench trap proves the gate refuses an unanswered kind rather than starting the night anyway.

**S8c · The audit: lenses whose output is work.** Six lenses over the code against the description —
tests, dependencies, scenarios, security, performance, conventions — each writing its own report and
changing nothing. It is read-only by construction: the moment an audit starts fixing what it finds it
loses its stopping condition.

- **It runs the same preflight every other command runs** (finding 34: in the second version the
  audit was the one command that checked nothing before starting).
- **As a child of a batch** it takes its area from its own record, leaves a commit on the branch that
  record already names, and closes itself — never a branch it chose alone, because a branch nobody
  can account for later is what 51 of 99 measured branches were.
- **Its output is the candidate list S8b composes from.** That is what closes the loop: today the
  work list exists only in the owner's head, and the TOML is the owner typing it out.

*Done when* one lens over a project produces a report and a candidate list a sitting can compose
from, and a bench trap proves a lens that found nothing says so rather than inventing a finding.

**S8d · The door.** A program, not a session: it reads the runs, the batches, the open blocks, the
red commands, the unanswered kinds and the open pull requests, and names one command with the reason.
Everything it needs is already on disk. This is §5's promise, and it is one program rather than two:
the raw view of where a project stands and the ranked recommendation are the same data, and the
second version kept them in two places that had to agree.

*Done when* a project after a week's silence gets one named command and the sentence behind it, and
every part of that answer is derived from state rather than from anybody's word.

**S8e · What proves a feature, and what a project checks itself for.** The largest of these, and the
one the third version regressed rather than merely omitted. Two levels, one catalogue.

*The project's level.*

- **The catalogue lives in the kit**: suite, end-to-end, mutation, types, lint, static analysis,
  architecture, visual, contract, performance, accessibility, security — and `screen`, which S13
  adds. Each says **what it catches** (the defect, never a tool: tools differ per ecosystem and this
  list may not), which session runs it — `feature` or `epic` — and the shape of project it does not
  apply to. **A kind added here starts being asked of every project on its next check**, where a list
  copied into each project would have to be remembered into all of them by hand.
- **One home, and nothing holds a copy** (finding 30: the second version kept the same list in two
  places with nothing to make them agree).
- **The project answers every kind: a command, or a refusal carrying a date and a reason.** Never a
  word. A command is held to *starting*, because `yes` is a claim no program can test — and it is
  also a real binary on every Unix, which is how the second version's own gate was once opened by it.
  The date, because *there is no front end* stops being true the week there is one. The reason,
  because twelve lines of `no <today>` would clear every check here while recording that nobody
  thought about anything.
- **The answers are proposed from the repository, never from prose.** Read the dependency manifests,
  the test directories, the CI workflows, the scripts. Measured on three live projects: one said
  mutation testing was not installed while the plugin was a hard dependency of its test runner;
  another carried two hundred lines of a browser runner walking every screen and asserting nothing,
  named in no document. **On two of the three the cheapest finding was an instrument installed,
  configured and never declared** — one line, and every run afterwards starts using it.
- **What is offered is the decision, never the work.** Standing an instrument up is a task of its
  own, at most one at a time, cheapest first. An interview that turned into an installation is an
  interview nobody finishes.
- **An answer goes stale on evidence, not only on a date**: a dependency manifest whose hash has
  moved is a stack that changed under a decision taken about a different one.
- **One parser** (finding 52: a hand-rolled YAML subset in which a `#` inside a quoted value
  truncated the line). TOML, and the reader the rest of the kit already uses.

*The feature's level, and this is what is missing from the code today.*

- **A feature decides what will prove it before it writes any code.** `design` returns one record per
  kind whose `runs` is `feature`: the command this change owes, or the `why` it cannot apply here.
  Chosen after the code, that list is written by somebody who already knows what they built and is
  looking for a reason to be finished. It also makes *write the test before the code* mean more than
  the suite — a screen this feature changes owes its comparison in the same commit as the screen.
- **`verify` walks that list rather than deciding again.** Each record is completed with the command
  as it was actually run and its result. **Silence about a kind is a refusal, not a pass** — a record
  with neither a result nor a `why` is what a test written in the build and never started looks like.
  A result with no command behind it is refused. A kind the catalogue marks never-skippable cannot be
  excused at all.
- **The review step checks the claims against the diff** — the one thing no record can do for itself.
  A `why` saying *no screen here* on a diff that edits a template is the cheapest way there is to skip
  a kind of test, and every other pass reads the record rather than the change.
- **The kit prints what a feature of this project owes**, with the command for each, rather than
  leaving a model to join two files six times a night.

Today `design.verification` and `build.tests` exist and their only reader is the printer that folds
them into the pull request — `programs/deliver.py`. A field whose reader is a printer is prose with a
green tick, which rule 5 forbids and which this step ends.

*Done when* a project is asked about every kind the kit knows and answers each with a command that
starts or a dated refusal with a reason; a feature's design returns a record per kind it owes;
`verify` refuses a run that is silent about one, and refuses a result with no command behind it; the
review step refuses a `why` the diff contradicts; and the bench carries a trap for each of those four
refusals.

**S8f · The kinds of block that have no writer, and the ledger.** S6 wrote that the kit writes
`assumed` alone and named who the others were waiting for. Two are still waiting:

- **`found`** — a review's findings reach the knowledge not at all. A blocking one stops the run, and
  the rest ride along in a pull request nobody reads twice.
- **`stale`** — nobody marks a sentence of the description untrue when a feature makes it so. In the
  second version 35 of these were written and all 35 closed, which is what a healthy one looks like.
- **`docs/technical_debt.md`** — the ledger. Without it the three destinations of S8a are two, and
  *works, but badly* has nowhere to go except a conversation that ends when the session does.

*Done when* a review's finding reaches the knowledge with an identifier, a feature that outdates a
sentence marks it where it stands, the ledger has a writer and a reader, and each of the three has a
trap.

**S8g · Manual actions, with a proof that runs.** The one class of work an autonomous night cannot
do for itself — place a secret, apply a migration, create an account, point a domain — and the one
with no home in the third version at all. `manual` appears nowhere in `src/` or `method/`.

- **A file in the repository**, shaped like the ledger of S8f: a run appends a line, whoever does
  the work deletes it in the same commit. The second version kept these in a run file that is
  git-ignored and dies with the machine, and its only reader composed them out of a pull request
  body nobody opens again after the merge.
- **`proof` is an executable command, never prose.** It exits zero once the action has been done —
  the key is in the environment, the migration is applied, the endpoint answers — and then the
  program deletes the line itself. Nobody has to remember to tick anything, and *done* is not a
  claim anybody makes about their own work.
- **Where no check can be written**, because it truly needs a person holding a phone, the line stays
  and says so. That list is short, which is the point: on one measured run, nineteen items held six
  that needed a person.
- **A stage decides what is shown.** On a project still in development, the lines due before a
  release are not work anybody is doing this week, and showing them teaches the owner to scroll past
  the list.

*Done when* a run that needs a human action records it where it survives the machine; a proof that
passes deletes its own line; a line with no possible proof says so in its own words; and the door of
S8d names what is due rather than leaving it to be found.

## Deferred by the owner, and still deferred

Neither forgotten nor dropped — refused with a reason that has not expired:

- **a merge policy that merges by program**, refused until findings carry codes and levels, which
  they now do: the day this is taken up, the reason is spent and it needs deciding again;
- **the ranked backlog** — the door of S8d widened from one recommendation to the whole queue;
- **a schedule**, living wherever the project's own declaration lives;
- **a continuous mode** — when a run finishes, take the next thing off the queue until the owner
  switches it off. Parallel building was the fourth of these and S8 built it.

## What stays dropped, and this is the record of it

Not forgotten — decided, and each with its evidence:

- **the `accepted` block**: a template, a block and a closing rule, and no writer in the whole life
  of a measured project;
- **`accept` as a command**: the pull request is the report — three things open, the rest folded —
  which is where its work went. The map found it on neither preflight list, and found that the
  command writing its input never named it (findings 33, 55);
- **native hooks and skill packages**: §4, replaced one by one;
- **`deferred`, `closed_debt`, `seams` as fields**: written into nothing, and rule 5 deletes rather
  than documents.

`advise` is neither: it was never discussed. It stays out until somebody names a writer for what it
would produce — the same test that dropped `accepted`.
