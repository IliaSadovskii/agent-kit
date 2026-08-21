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
