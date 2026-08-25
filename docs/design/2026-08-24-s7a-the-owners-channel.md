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

`agent-kit bench run` reports every case as fired; a question raised at design time reaches
a phone and an answer typed into it changes what gets built; a question nobody answers costs the
night twenty minutes and leaves a block in the owner's knowledge saying what was taken and why;
a run that ends says so without anybody opening a terminal; `run show` and the page both name
what is being waited for and until when; and breaking any one of the eight new mechanisms by
hand makes exactly one case say it did not fire.

*(Nine, in the end, and seven of the nine light exactly one case. What the ninth is and why
it had to exist is at the foot of this note.)*

**Deliberately not built:** any command in the chat that acts — a stop, a skip, a retry; news
about a machine that is merely busy; an answer that arrives after the wait has ended being kept
for a later run of the same project (a mechanism with no reader today, and it would be one);
a second question in the same step, because a second round is a conversation and this kit's
handovers are files; and any channel that is not Telegram, because one was settled and a second
is a config block nobody asked for.

---

# What was built, 24 August 2026

Everything above was built as decided, with one thing added that the note did not
foresee — a ninth trap, and the reason it exists is the most useful paragraph here.
Forty-three bench cases all firing, 619 tests, and a question that reaches a phone
and changes what gets built.

## The sentence the step is done by

A question raised at design time, sent, waited on, and settled — four ways, and each
looks different in the morning:

```
add-vat · design
one VAT rate for everything, or one per country?
Через 2 мин возьму: one rate for everything
Почему: nothing in this project has a second country in it yet
Ответить на это сообщение, или: /a 2xdhdn <ответ>
```

Answered, the design runs again with the answer enclosed and what lands on the branch
follows the answer. Unanswered, the run goes on and the owner's knowledge gains a block
saying what was taken and why nobody settled it — written by `record`, which learned
nothing new, because a default nobody answered is an expensive assumption and this kit
already knew what one of those owes.

## The ninth trap, and why it is the useful one

The note listed eight. Breaking each by hand found that one of the eight measured a
different line than the one it was written for.

`the-same-question-asked-twice` is about the rule that the owner gets one round. Breaking
the round guard — `if round > 1 or not fresh` — left **the whole bench green**. What
actually holds that case up is a different line: a question already answered is filtered
out before anything is sent. So the guard that stops a *new* question in a second round
had no trap at all, and would have shipped exactly as S6's two mechanisms did.

`a-second-round-the-owner-never-saw` is the case for it: the owner answers the first
question, the second design raises something they were never asked, and it is taken at
its default without being sent — and still written down. Breaking either line now lights
exactly one case, and they are different cases.

This is the S7 lesson in a new costume: *a judge that was nearly green for nothing.* The
difference is that S7 found its by reading, and this one was found by breaking, which is
why the rule is that every new mechanism is broken by hand rather than reasoned about.

## Breaking the nine

| What was broken | What said so |
|---|---|
| the default nobody answered is never written down | `a-question-nobody-answers`, `no-channel-to-the-owner`, `a-channel-that-is-not-answering` |
| an answer does not run the step again | `an-answer-from-the-owner`, `the-same-question-asked-twice` |
| an answer is not matched to the question it names | `an-answer-to-another-question` |
| a machine with no channel says nothing happened | `no-channel-to-the-owner` |
| a channel that could not be reached looks like silence | `a-channel-that-is-not-answering` |
| a stop is not read while waiting on a person | `a-stop-while-the-owner-is-asked` |
| a run that ends says nothing | `news-when-a-run-ends` |
| a question already answered is asked again | `the-same-question-asked-twice` |
| the owner gets a second round in one run | `a-second-round-the-owner-never-saw` |

Seven of the nine light exactly one case. The two that light more are one mechanism seen
from several sides, which is the pair being right rather than a case measuring the wrong
thing: **the fold** has three endings — nobody answered, no channel, the channel failed —
and a case covering all three could not say which ending broke; **the re-run** is what the
same-question case is built on top of, so breaking it takes that case with it.

## What changed on the way, against the note above

**A question the owner answered leaves the output.** The note said an unanswered question
folds into the assumptions and said nothing about an answered one. Leaving it in `asks`
made the pull request ask for something the owner had already settled, which is the exact
defect the second version's report had. Answered is neither taken nor open: it is settled,
and it stops standing anywhere.

**The poll never sleeps longer than what is left.** Five seconds between polls is right for
twenty minutes and absurd for two, and two is what a bench case waits. Named here because
it is the difference between a case that costs two seconds and one that costs five.

**`_fold` writes absent rather than empty.** An optional field with an empty string is
refused by the contract — rightly — so a question with no `at` writes no `at` at all. The
guard behind it stands: if a fold makes an output no longer satisfy its contract, the step
is refused with `asked-with-no-block` and the next attempt is told exactly that.

**`run show` reads the ledger.** The note only promised the page and `machine`. A step's own
reason says it is asking; what was asked and when the default is taken lives in the ledger,
and somebody looking at a stuck run wants both.

## What building this found in what already stood

**Eight of S7's own cases go red every day after 17:00 UTC**, and today they did. The review
round that fixed the limit blocker replaced `2027-01-01T00:00:00+00:00` — *the one shape no
provider will ever say* — with `2026-08-24T17:00:00+00:00`, which was a real hour on the day
it was written. Past that hour the limit is swept, correctly, by the very sweep those eight
cases measure. The shape was the point and the shape is kept; the hour is computed ahead of
the run now.

It is worth naming what class of defect this is, because it is the same one twice: **a fixture
that encodes a moment rather than a shape.** The first time it cost an account limited for
good; this time it cost a suite that is honest only before teatime. Both were found by
something outside the suite — a review, and a day passing.

## What the review round has not seen

This is the record of what was *not* done, so the next session starts from it rather than
from an assumption:

**No review round yet.** S7's found twenty-two things, three of which would have taken a
night down, and all three lived where two mechanisms meet. This step has at least three such
places: a person's words and a composed input; a chain of attempts and a step that goes back
to pending; a ledger row and a step status that must agree about the same wait.

**Telegram's own HTTP is proved by nothing but its tests.** Every case answers through the
file channel, deliberately — the bench does not reach the network. `sendMessage` and
`getUpdates` are exercised through the one call they are given, and what has never happened
is a real bot answering a real phone. `agent-kit owner check` is the command that finds out,
and it is a person's to run.

**A late answer is dropped.** One that arrives after the deadline moves the offset and is
logged, and nothing reads it: the question it answers has already been taken at its default
and the run has moved on. Keeping it for a later run of the same project would be a row with
no reader, which is the rule this kit refuses both ways.

**One question, one message.** Three questions are three messages and three rows, and nothing
groups them. Nothing has measured that a step asks more than one at a time.

## Настройка одной командой, и почему она программа

`agent-kit owner setup` заводит канал целиком: спрашивает токен, проверяет его у самого
телеграма, говорит человеку, куда написать, и берёт идентификатор чата из того, что пришло.
Ни одного числа не переписывают руками.

Причина ровно та, на которой стоит вся третья версия: **шесть шагов в документации — это
шесть мест, где правило держится на человеке, а такое правило выполняется два раза из трёх.**
Здесь их выполняет программа, и она же проверяет то, что человек проверить не может, — что
токен принят и что бот имеет право писать в этот чат.

Настройка либо вся, либо никакая. Токен, который телеграм не принял, не пишется ни в секреты,
ни в конфиг: машина, которая думает, что канал у неё есть, хуже машины без канала.

Это первый писатель `config.toml` в ките. План обещал три редактора одного файла — команды,
страницу и текстовый редактор, — и раз файл заведён, чтобы человек его читал и комментировал,
команда правит свой блок текстом и не трогает вокруг ни байта.

**Ловушки у неё нет, и это сказано словами, а не считается покрытым.** Стенд гоняет прогоны:
`run new`, `run go`, судья читает запись. Интерактивная команда, которая разговаривает с
человеком и ходит в сеть, в эту форму не влезает. Её держат тесты — вся дорожка от токена до
записанного блока, отказ на непринятом токене, отказ на молчании — и `owner check`, который
человек запускает сам.

## What is open, said out loud

**The step status and the ledger row can disagree.** A driver killed between `ask_step` and
the ledger write leaves a step saying `asking` with no question standing; the next driver
refuses it back to pending and runs it again, which is correct, but `run show` in that window
prints *the owner was asked, and the ledger no longer holds the question*. That sentence is
the seam, written where it can be read rather than smoothed over.

**Nothing stops a question the code could have answered.** The role's prose says not to ask
what can be read, and prose is obeyed two times in three — which is the number this whole
version is written against. What would measure it is a count of questions against a count of
answers over real nights, and there have been none yet.

**A stop from the chat is still not built.** It is the one thing a person on a phone would
most want, and a chat identifier is not authentication. The day the page grows a button is
the day both of these get answered together.


---

# Что нашло ревью, 25 августа 2026

Три ревьюера по диапазону `365c91a..HEAD`, у каждого свой угол: что бывает, когда две такие
штуки работают разом; врут ли ловушки и тесты о том, что меряют; и соблюдает ли шаг
собственные правила проекта. Около тридцати находок. Пять из них молча портили ровно то,
ради чего S7a и написан, а одна была ложью в правиле, которое этот же шаг в `CLAUDE.md` и
дописал.

## Пятёрка: умолчание, взятое и забытое, было по-прежнему возможно

Заметка выше обещает: *«умолчание, взятое и забытое, становится невозможным»*. Оно было
возможным пятью разными способами, и корень у всех один — **`asks.json` был счётчиком кругов,
а не записью шага.** Драйвер читал оттуда одно число и больше ничего.

| Что происходило | Чем кончалось |
|---|---|
| два вопроса, на один ответили | умолчание второго не попадало в свёртку никогда |
| второй замысел перестал повторять вопрос | следа не оставалось вообще — ни в PR, ни в знании |
| драйвер умер после ответа владельца | ответ выбрасывался, в знание уезжало «ответа не было» |
| человек остановил ночь, чтобы ответить | круг считался потраченным, и утром его не спрашивали |
| вопрос второго круга | записывался кодом «никто не ответил» — про сообщение, которое не отправляли |

Теперь `asks.json` держит вопрос целиком — `because`, `at`, `block` — и час, когда каждый
уладился, а драйвер читает его на входе. Свёртка берёт всё, чем шаг когда-либо кончил
спрашивать, а не последний круг, и делается везде, где есть что уладить, а не только там, где
только что спрашивали. У пятого исхода появился свой код — `had-their-round` — и своя фраза.

**Ни одна из пяти не была видна стенду**, потому что все девять случаев задавали ровно один
вопрос. Это цена ловушки, поставленной на самый простой сценарий механизма.

## Ложь в правиле, которое этот же шаг и написал

`agent-kit owner check` не проходил никакой лестницы. Он печатал неизменную строку «the ladder
holds: …», не спросив у телеграма даже, кто он. Лестницу обещали заметка, `--help` и правило,
дописанное в `CLAUDE.md` этим же шагом. Тест назывался `..._walks_the_ladder_and_says_where_it_stopped`
и проверял, что в выводе есть слово `file`.

Это **утверждение вместо следа** — ровно то, против чего написан весь план, и написанное
рукой того, кто час назад про это правило и читал. Лестница теперь настоящая: четыре ступени,
каждая называется вслух по мере прохождения, и та, на которой встали, названа отдельно.

## Мёртвая ветка, выданная за механизм

Про `asked-with-no-block` заметка говорила: *«The guard behind it stands»*. Ревьюер заменил
его на `pass` — весь стенд и все тесты остались зелёными. Контракт отбрасывает вопрос без
блока ещё при разборе вывода, так что до этой ветки дело не доходит никогда. Удалена, а не
задокументирована.

## Судьи, которые мерили прозу

Правило проекта: случай сверяет код отказа, а не английскую фразу. Три судьи сверяли **русскую**
фразу из `_because`, а у девятой ловушки греп прозы был единственным дискриминатором. Ревьюер
переписал три предложения, не тронув ни одного механизма, — два случая покраснели зря.

Теперь все четыре читают код исхода. Проверено тем же способом: переписаны все пять фраз —
сорок пять из сорока пяти зелёные.

## Ловушка, которая рапортовала как поломка стенда

`a-stop-while-the-owner-is-asked` ждала 600 секунд при таймауте стенда в 300. Сломанный
механизм кита возвращал код 7 («сам стенд не смог ответить») вместо 6 («механизм не сработал»)
и делал `make bench` на пять минут дороже. Тридцати секунд хватает.

## Три утверждения, истинных при любом ките

- Последняя строка теста настройки сравнивала кортеж со строкой: тест был зелёным и тогда,
  когда подтверждение в телеграм не уходило вовсе. А заметка ссылалась именно на него —
  *«ловушки нет, её держат тесты»*.
- Тест про отказ читать `asking` ставил номер схемы на единицу больше и слова `asking` в файл
  не писал. Дословный дубль соседа, зелёный ещё до S7a.
- Тест про смещение зоны держал момент, а не форму, и не проверял, что лимит стоит.

## Ещё две ловушки

Без покрытия оставались ответ реплаем — то, что человек на телефоне делает на самом деле, —
и смещение канала. Обе заведены, и слом каждой красит ровно свой случай. Стенд — сорок пять.

## Поля без читателя

`Run.asking`, реэкспорт `CHANNEL`, колонка `answered_at`, неиспользуемый импорт, `--name` у
`set-token`. Удалены. Час, когда ответили, живёт в `asks.json`, где его кто-то читает.

Отдельно: `owner.setup` был одновременно модулем и функцией, и имя в пакете затирало модуль,
из которого пришло.

## Что ещё поправлено

Код 4 означал две вещи — «агента не запустить» и «до владельца не достучаться». У второго
теперь свой код 8: события разные, и делать по ним надо разное. `no-token` был одним кодом с
двумя кодами выхода в двух местах. Настройка стала атомарной: конфиг не записался — токен
забирается назад, потому что токен без канала это живой бот, о котором машина не знает.

## Четыре, которые были отложены, и почему это было неправильно

Первый круг правок остановился, когда кончились находки категорий «уронит ночь» и «испортит
запись». Четыре оставшихся были отложены со словами «заберём в S8, там всё равно про смерть
драйвера». Довод плохой: **S8 про то, что драйверов становится много, а эти дефекты работают
уже сегодня при одном.** Откладывали по тому, на что похоже, а не по тому, когда проявится.
Закрыты тем же вечером.

**Строка вопроса не обновлялась при повторной отправке.** Драйвер умер, шаг подняли заново,
вопрос ушёл новым сообщением — а реестр называл старое. Реплай переставал находить вопрос,
работала только форма `/a <id>`; а `until` оставался прежним, и через час выметание сносило
строку из-под живого ждущего драйвера — ответ пропадал навсегда. Теперь строка называет то
сообщение и тот час, которые есть, а ответ при этом не трогается.

**Упавший канал стирал уже доставленное.** Три вопроса, первый ушёл, на втором канал лёг —
стиралась и строка первого. Владелец видел вопрос на телефоне, а ответу некуда было лечь.
Теперь ждут ровно то, что ушло, а потерянным записывается только не ушедшее.

**Один идентификатор на два проекта.** Реестр выдаёт свободное имя — тем же способом, каким
знание разводит два одинаково сформулированных допущения.

**`owner setup` читал канал мимо аренды.** `getUpdates` рассчитан на одного потребителя, и
команда, которая канал заводит, не имеет права быть исключением из правила, которое заводит.

## Обе новые ловушки были зелёными против сломанного кита

И это стоит записать отдельно, потому что найдено единственным способом, каким такое находится.

Первая подкладывала строку с давно прошедшим часом — и первое же обращение прогона к реестру
выметало её раньше, чем вопрос уходил. Ловушки не было вовсе. Теперь час доживает до прогона, а
меряется та половина, которая доказуема в одном прогоне: какое сообщение называет реплай.
Вторая половина — выметание из-под живого драйвера — держится тестом, и здесь это написано
словами, а не засчитано ловушкой.

Вторая роняла канал фоновым сторожем, который гонялся с прогоном: оба вопроса успевали уйти
раньше, чем он замечал, и падения посреди списка не случалось никогда. Файловый канал теперь
принимает число — сколько сообщений отдать, прежде чем лечь. Фикстура, которая падает когда
придётся, меряет то, что подвернулось.

## Что осталось открытым

- **Выметание строки из-под живого драйвера** проверено тестом, но не ловушкой: чтобы поставить
  её, нужен прогон, переживший собственную смерть, а стенд гоняет прогон один раз.
- **Живой телеграм по-прежнему не проверен ничем**, кроме тестов на подставном вызове.
