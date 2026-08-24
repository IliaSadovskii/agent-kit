# S7a — the owner's channel

Written before building it, 24 August 2026, the way S5, S6 and S7 were written before them,
so the next session starts from decisions rather than from a blank page. S0–S7 are done: the
package, the state, the step contract, Claude Code at level B, one feature end to end, a bench
of thirty-four traps, the knowledge written by the program, and a machine that counts its own
sessions.

The plan's own words, from the build order:

> **S7a · The owner's channel.** Telegram, both directions, as settled at the foot of this
> note. Its own step and not a half of S7: the daemon is about a machine's slots and the
> channel is about a person's phone, and folding them together is what made the second
> version's control surface a live session. *Done when* a question waits its measured twenty
> minutes against a phone, and an unanswered one takes the default and records it as an
> assumption.

And the settlement it points at, from *Two answers, settled 22 August*:

> News and questions go to Telegram — thirty lines around one HTTP call, both directions. A
> question waits the measured twenty minutes against a phone; unanswered, the default is taken
> and recorded as an assumption, exactly as the second version measured it. The waiting is a
> state of the step, not a sentence of prose.

That closes open questions 7 and 8. Everything below is in service of the last sentence of
each: **the waiting is a state, and the default is recorded.**

---

## 1 · What is actually missing today, read rather than remembered

**A question reaches the owner in the morning, or not at all.** `design` writes `needs_owner`,
one line per thing only the owner can decide. It has exactly one reader: the open half of the
pull request (`programs/deliver.py`). So a question raised at 02:00 is read at 09:00, by which
time the night designed around it, built it, verified it, wrote the knowledge and opened the
pull request. The role's own prose says so out loud — *until the kit has a channel of its own
it is the only way a question reaches the owner at all* — which is a sentence written to be
deleted by this step.

**The kit cannot say anything while a night runs.** The second version reached a phone by
typing a line into the owner's tmux session, which Anthropic's app turned into a notification.
That dependency died with the plugin. Today a run that finishes at 03:00, a run that fails on
its third attempt and a run that stops on a blocking finding are all equally silent until
somebody opens a terminal.

**Waiting exists, and only for machines.** S7 taught the driver to wait — for a slot, for a
limited account to reset — and both waits are rows in the ledger with a deadline the page can
show. There is no shape at all for waiting on a person, and `~/.local/state/agent-kit/secrets`
has been printed by `doctor` since S0 with nothing that ever writes it: the kit's own rule
about a field with no reader, standing in the kit's own state directory.

---

## 2 · The shape: the step asks, the driver waits, the program records

The obvious design is the wrong one, and naming why is the whole of this section.

**The obvious one:** give the session a way to ask a question in the middle of its turn — a
tool, a socket, a file it writes and the kit watches. **Refused.** It is a live conversation
between an agent and the kit, which is the thing the plan's measurement is written against:
every handover in this kit is a file with a name, replayable and answerable after the fact, and
a conversation is none of those. It would also need building once per provider, which is what
`method/` being prose exists to avoid.

**What is built instead:**

1. A step's contract may declare **`asks`** — questions, each carrying the **default** the step
   designed around. The step answers, and it answers completely: what it returns is a design
   that works if nobody ever replies.
2. The driver reads that field, sends the questions down the channel, and **waits** — twenty
   minutes by default, and the step's status while it waits is `asking`.
3. **An answer re-runs the step**, with the answer enclosed like any other enclosure. One
   round, never two.
4. **A question nobody answered becomes an expensive assumption** in the step's own output,
   which is a shape the kit already has a whole machinery for: `record` writes it into the
   knowledge as an `[assumed …]` block, `deliver` prints it in the open half of the pull
   request, and neither of them learns a single new thing.

Point 3 is the expensive one and it is deliberate. Enclosing the answer in the *next* step
instead would cost nothing and would leave the record saying one thing while the code did
another: the design on file would be the design of the default. A record that does not describe
the work is the defect the third version was built to delete.

The four questions, answered where the mechanism is written:

| | |
|---|---|
| Can this be a program instead? | It is one. No session decides whether an answer arrived, what it means, or when the waiting is over. |
| What trace does it leave? | `steps/<n>-<name>/asks.json` — every question, its default, what came back and when; a row in the ledger while it waits; the step's `asking` status; and the `[assumed …]` block when a default is taken. |
| What composes its input? | The driver. The owner's answer is an enclosure, exactly like an earlier step's output. |
| Who reads what it writes? | The driver (the second round), `record` (the folded assumption), `deliver` (the pull request), the page and `machine` (what is being waited for). |

**What becomes impossible:** a question that reached nobody, and a default taken and forgotten.

---

## 3 · What a question is

`asks` is a list of records, and every field of it has a reader:

| Field | What it is | Who reads it |
|---|---|---|
| `question` | one line, answerable from a phone | the channel |
| `default` | the answer taken if nobody replies — and the one this output was designed around | the driver, and the assumption |
| `because` | why that default is the safe one | the assumption's own `because` |
| `at`, `block` | where in the knowledge the taken default belongs, and what it should say | `record`, when the default is taken |

**`default` is required, and that is what makes a stall impossible.** A question with no default
is not a question, it is a step refusing to finish, and the contract refuses it by name. Every
path through this mechanism ends with the run going on.

**`at` and `block` are required only where the project keeps knowledge**, through the mechanism
that already exists for exactly this: `knowledge_requires` on the step definition, which the
driver turns into the stricter contract the session is shown and judged against. Two more
entries beside the three S6 added, and no new code.

**`needs_owner` becomes `asks`.** One thing has one name, and *needs owner* named a list of
sentences that went into a report. A question with a default and a deadline is a different
thing, and carrying the old name would be the kind of drift the map found everywhere in the
second version. The pull request keeps its Russian heading — *Что нужно от владельца* — because
that is what the section is for.

**Any step may ask; only `design` does today.** The driver reads `asks` wherever a contract
declares it, so `review` or `build` could grow one without the driver changing. Shipping it on
`design` alone is not a limitation of the mechanism, it is where questions actually arise.

**A program never asks.** `verify`, `record` and `deliver` are programs, and a program has
nothing to be unsure about that a person could settle.

---

## 4 · The waiting, and why it is a state

`StepStatus` gains **`asking`**, and the run file's schema goes from 2 to 3.

This is rule 4 of the build order — *a frozen shape is never quietly changed* — obeyed rather
than mentioned: the state changes in its own commit, with its own migration and its own tests,
before anything else in this step is written. The migration itself adds no field; what it buys
is the refusal. A run file that says `asking` must not be readable by a kit that does not know
what asking is, and `schema-too-new` is what says so.

A step is `asking` when its session has answered, the questions have gone out, and the driver
is waiting. Two things follow from that sentence and both matter:

**An asking step holds no slot.** The session is closed; the machine is free. S7's own words:
*a run that is waiting for a person, running the project's tests, or writing the knowledge is
holding nothing.* This is the first time anything is actually waiting for a person, and it is
the sentence being honoured rather than restated.

**An asking step holds its run.** The driver is alive and still the one writer, so
`agent-kit run stop` reaches it the way it reaches a driver waiting for a slot — which was a
finding of S7's own review round: *the run somebody is most likely to want stopped is the stuck
one.* A run waiting twenty minutes on a person is exactly that run.

**A driver that dies while asking leaves the step to the next one.** Same treatment as a step
left `running`: it goes back to `pending` and is tried again, and it is tried again from the
top rather than resumed, because the session that produced the questions is gone. An answer
that arrived in the meantime is in the ledger, so the second driver encloses it instead of
asking again.

**Where the two facts live, and they are two facts.** The ledger holds *this machine is waiting
for an answer to k7f3q2 until 02:41* — live truth, cross-project, read by the page, by
`machine`, and by whoever is polling the channel. The run file holds *the design step asked, and
this is what came of it* — the durable record, written by the run's own driver. One fact, one
home, as the plan's "Where everything lives" requires; these are not one fact.

---

## 5 · Twenty minutes, and what it is measured against

`[owner] wait = 1200`. The second version measured twenty minutes against a phone and it
worked; this is that number, kept, and now a setting rather than a constant in prose.

Two `wait` settings now exist and they are not a collision: `machine.wait` is how long a run
waits for the machine, `owner.wait` is how long a step waits for a person. The table each sits
in says which, and both answer the same question — *how long before we stop waiting.*

`0` means take the default at once. So does no channel being configured at all, and that is the
compatibility rule of this whole step: **a kit with no Telegram behaves exactly as it does
today**, except that the default is now written down as an assumption instead of being invisible.

**The deadline is the kit's own clock, and nothing else.** S7's blocker was an hour the provider
printed being stored as the phrase it came in — `5pm (America/Los_Angeles)` sorting above every
date there will ever be, and an account limited for good. The same shape is available here and
is refused in advance: a Telegram update carries a `date`, and it is *their* stamp on *their*
clock. What decides whether an answer arrived in time is the moment this kit read it. A time
inside a person's message text is never parsed at all — it is prose, and this kit's rule is that
prose is not a mechanism.

---

## 6 · Both directions, without a socket and without a daemon

Telegram's Bot API, over HTTPS. `sendMessage` out; `getUpdates` — long polling — in. **No
webhook:** a webhook wants an address on the public internet, and this machine is reachable only
inside Tailscale. One HTTP call each way, which is what the plan costed it at.

`getUpdates` has one property that decides the design: **it is a single-consumer API.** It is
read with an offset, and two processes reading at once steal each other's updates. Two drivers
waiting on two questions is the ordinary case here, so this has to be settled rather than
discovered at 02:00.

**The reader is whoever is waiting, one at a time, under a lease in the ledger.** The offset
lives in the ledger, not in a process. Whoever holds the reader lease polls, and writes down
*every* answer it reads — including answers addressed to somebody else's question, which the
other driver then finds without ever calling Telegram. The lease is reaped like every other
when its holder dies.

This is S7's argument applied unchanged: **a mechanism that needs a process to be alive is a
mechanism that is off when it matters.** The daemon is not in this path. It shows the questions
on its page and it answers none of them.

**An answer names its question.** The message the kit sends carries a short identifier, derived
from the run's name and the words of the question by the same function the knowledge blocks use
— which is why a bench case can name it in advance, and why the same question in a second
attempt resolves to the same identifier instead of being asked twice. The function stays where
it was first needed, in `knowledge/format.py`; giving it a third home would be a move with no
reader.

What arrives on the phone:

```
add-vat · design
Is the VAT rate one rate, or one per country?
Taking in 20 min: one rate, 20% — nothing in this project has a second country yet.
Reply to this message, or: /a k7f3q2 <answer>
```

A reply to the message is what a person actually does, and it is what is read first: Telegram
carries the message being replied to, so the identifier need not be typed. `/a <id> <answer>` is
the fallback, and it is the form the bench uses.

**Only the configured chat is read.** An update from any other chat is dropped without being
looked at. A bot's username is public and anybody may write to it.

**An answer is a person's words, and words are content.** It reaches the next session as a
labelled enclosure, exactly like an earlier step's output — never as an instruction, never as a
command, never as a path or a name the kit acts on. This is the same rule that makes a step's
input safe to compose from a project's own files, and it is worth writing down once for a
channel that comes from outside the machine entirely.

**No commands beyond answering.** No `/stop`, no `/skip`, nothing that acts. *Every button is a
way to break a night from a bus* was written about the daemon's page and it is truer of a chat:
a chat identifier is not authentication, and `agent-kit run stop` is a door that already exists
and already knows who holds the run.

---

## 7 · News

Two things go out, and each has a reader who wanted it:

- **a question**, which is the mechanism above;
- **a run ending** — done, failed, stopped by a person, or stopped by a gate — naming the run,
  the reason, and the pull request where there is one.

Sent by the driver, in the one place that already knows a run is over, so `run go` and
`step run` behave the same.

Nothing else, deliberately. A machine that filled up and is waiting two hours is the obvious
third, and nothing has measured that anybody wants to be woken for it. Named here rather than
built on a guess.

---

## 8 · What the code is, and which way the arrow points

```
owner/                  the channel, and the asking
  ask.py                a question, its deadline, and what folding a default into an output means
  channel.py            the contract: send this, read what has come back
  telegram.py           the Bot API, and the only thing in the kit that reaches the network
  file.py               a channel that is two files — what the bench answers with
```

`owner/` depends on `errors`, on `config`, and on `machine/` for the rows it writes while it
waits. `driver/` depends on `owner/`. `daemon/` reads the asks through `machine/`, as it reads
everything else. The arrow keeps pointing one way: state → contract → driver → adapters →
machine → daemon, with `owner/` beside the adapters, which is what it is — somebody else's
service behind one module.

**A channel is chosen by name, the way a provider is.** `[owner] channel = "telegram"` or
`"file"`, absent meaning none. Two implementations of one small contract, and the fixture is not
a mock inside the tests: it is a channel that ships, like `providers/fake/`.

---

## 9 · Secrets

The bot token is the kit's first secret, and `~/.local/state/agent-kit/secrets` — mode 600,
never in git, printed by `doctor` since S0 with nothing to print — gets its first writer.

`agent-kit owner set-token` reads it from stdin rather than from an argument, so it does not
land in a shell history. `config.toml` holds the chat identifier, which is a choice this machine
made and not a secret, and stays safe to show — which is the sentence the plan wrote about
`config.toml` and which this step must not break.

**A provider's level is measured, not declared**, and so is a channel's:
`agent-kit owner check` walks the ladder — a token is present, `getMe` answers, the chat accepts
a message, and (interactively) an answer comes back — and prints the rung it stopped on.

---

## 10 · What changes in what already stands

| Where | What |
|---|---|
| `state/schema.py` | `StepStatus.ASKING`; schema 3; `Run.ask_step`, and `answered` as its own event beside `refuse_step` and `continue_step` |
| `state/migrations.py` | 2 → 3, so a file that says `asking` is refused by an older kit rather than misread |
| `owner/` | new — the contract, Telegram, the file channel, and what an ask is |
| `machine/ledger.py` | new tables for asks and answers, and the reader's lease and offset; ledger schema 1 → 2 |
| `steps/definition.py` | nothing: a contract that declares `asks` is enough |
| `steps/registry.py` | `design`: `needs_owner` becomes `asks`, a list of records; two more `knowledge_requires` entries |
| `driver/runner.py` | read `asks` from an output, send them, wait, read a stop while waiting, re-run the step on an answer, fold a default into the output |
| `driver/compose.py` | the owner's answer, enclosed and labelled |
| `programs/deliver.py` | the open half prints the questions and what became of them, not a bare list |
| `config.py` | `[owner] channel`, `chat`, `wait`, `file` |
| `cli/main.py` | `owner check`, `owner set-token`, `owner say`; `run show` and `machine` print what is being waited for |
| `daemon/server.py` | the page shows *waiting for the owner*, and has nothing to press |
| `doctor` | the channel, and whether it has a token |
| `method/roles/design.md` | the sentence about the pull request being the only channel is deleted, and how to write a question with a default replaces it |
| `errors.py` | nothing — see below |
| `bench/cases/` | eight new cases |

**No new exit code.** A question that timed out is not a failure: the run went on, and the
default is in the record. A channel that could not be reached is not a failure either, and that
is the decision below. A stop while asking is 130, which is what it means everywhere else.

**A broken channel never stops a night.** Wrong token, no network, Telegram down: the default is
taken and the run goes on. What it must not do is look like silence — the assumption's `because`
says *the channel could not be reached* where an ordinary timeout says *nobody answered in
twenty minutes*, two phrases a person can tell apart in the morning, and `owner check` is where
they find out on purpose.

---

## 11 · What the last two rounds taught, applied here

S6's holes were a list S7 worked from; S7's own review round added more. Each has a place here:

| What it was | Where it lands here |
|---|---|
| a judge green where the trap was never planted | every judge proves the question was *sent* — the channel's own file is non-empty and names the identifier — before it judges what happened next |
| a green case whose two causes were the same place | the case about a default proves the design ran **once**; the case about an answer proves it ran **twice** and that the second input holds the answer |
| a case that measured an English sentence | every case reads an identifier or a refusal code; the question's prose is never matched |
| a mechanism with no trap shipped broken | eight mechanisms, eight cases, each broken by hand afterwards |
| green in the working copy only | the bench is run from `git archive HEAD` unpacked elsewhere before this is called done |
| the bench must not reach the network | no case configures `telegram`. The file channel is what every case answers with, and `owner check` — a person's command — is the only thing in the kit that ever opens a socket to Telegram |
| a time from somebody else's tool is a phrase | §5: the deadline is this kit's clock, and no time is ever read out of a message |
| source and tests in one commit | tests are their own commit, before the one that makes them pass — and the state change of §4 is its own commit before either |
| commit before breaking things on purpose | the break-by-hand round starts from a clean tree, which is what made three of five reports noise last time |

---

## 12 · Where this is proved

Eight traps. The bench becomes forty-two cases, and every one of them still costs nothing:
`providers/fake/` answers the sessions and the file channel answers the phone.

| Trap | The mechanism it must fire |
|---|---|
| a question nobody answers | the question went out, the run waited its (shortened) wait, the default was taken, the design ran once, and the knowledge holds an `[assumed …]` block under the identifier the case named in advance |
| a question the owner answers | the answer came back, the design ran a second time, the second `input.md` encloses the answer, and what was delivered follows the answer rather than the default |
| an answer addressed to another question | it is not mistaken for this one: the default is taken, and the stray answer changes nothing |
| no channel configured at all | nothing waits, nothing is sent, the run is not slower by a second, and the default is still recorded as an assumption |
| a channel that cannot be reached | the default is taken, the run lands green, and the reason says the channel failed rather than that nobody answered |
| a stop while the run is waiting for an answer | it is read at the ask, the run stops with `stopped-by-request`, later steps stay pending, exit 130 |
| a run that ends | the channel carries a line naming the run and its pull request — and the judge proves the file was empty before the run started |
| the same question twice | after an answer and a second design that asks it again, it is not re-sent; the known answer is enclosed and the run does not loop |

The file channel needs nothing the fake provider does not already have: two files, one written
and one read. A case plants an answer by writing `<id> <text>` into the second before the run
starts, and names the identifier because it is derived rather than drawn.

---

## 13 · What S7a is done when

`agent-kit bench run` reports forty-two cases as fired; a question raised at design time reaches
a phone and an answer typed into it changes what gets built; a question nobody answers costs the
night twenty minutes and leaves a block in the owner's knowledge saying what was taken and why;
a run that ends says so without anybody opening a terminal; `run show` and the page both name
what is being waited for and until when; and breaking any one of the eight new mechanisms by
hand makes exactly one case say it did not fire.

**Deliberately not built:** any command in the chat that acts — a stop, a skip, a retry; news
about a machine that is merely busy; an answer that arrives after the wait has ended being kept
for a later run of the same project (a mechanism with no reader today, and it would be one);
a second question in the same step, because a second round is a conversation and this kit's
handovers are files; and any channel that is not Telegram, because one was settled and a second
is a config block nobody asked for.
