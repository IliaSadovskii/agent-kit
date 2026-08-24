# S7 — the daemon

Written before building it, 24 August 2026, so that the next session starts from decisions
rather than from a blank page. S0–S6 are done: the package, the state, the step contract,
Claude Code at level B, one feature end to end, a bench of twenty-three traps that all fire,
and the knowledge written by the program.

The plan's own words: *Slots on the machine, limits per account, the queue, autostart under
systemd. Stop and skip (open question 9) belong to it. Its page shows and does not act, until
somebody asks for more: showing is what was missing, and every button is a way to break a
night from a bus. Done when two runs on one provider account wait for each other correctly
instead of sleeping blind.*

That last sentence is the whole step. Everything below is in service of it.

---

## 1 · What is actually missing today, read rather than remembered

Three holes, and each one is a real night going wrong:

**Nobody counts sessions.** `machine.max_sessions` has been in `config.toml` since S0 and is
printed by `doctor`. **Nothing reads it.** It is the kit's own rule — a field with no reader —
standing in the kit's own configuration since the first commit. Two `run go` in two terminals
today start two sessions, and four start four.

**A limit is learned once and forgotten immediately.** `ExecutorFailed` already carries
`until`, `providers/process.py` already parses the hour out of what the CLI said, and the
driver already declines to retry a limited account. Then the attempt ends, the fact dies with
the process, and the next run walks into the same wall and pays another session for the news.
`limited_until` reaches `meta.json` and `run show` prints it — to a person, after the fact.

**A run is stopped by editing state under a driver that is still writing it.** `run stop` writes
`run.json` directly. Open question 2 settled that a run has one writer — its own driver — and
this command is the exception nobody has closed.

---

## 2 · The central decision: the truth is a file, the daemon is a process

The plan says the daemon counts slots and knows a provider is limited until 17:00. It does not
say the counting has to happen *inside the process*, and it should not.

**The ledger — `~/.local/state/agent-kit/daemon.sqlite` — is where slots, limits, the queue and
the stop requests live. Every driver reads and writes it directly, in a transaction. The daemon
process serves the page, reaps what died, and is the thing systemd starts.**

Four reasons, in order of weight:

1. **A mechanism that needs a process to be alive is a mechanism that is off when it matters.**
   The daemon dying at 02:00 would take the ceiling with it and the night would run unbounded —
   silently, which is the one thing the whole plan is written against. SQLite is transactional
   across processes; the ceiling holds while nothing is running at all.
2. **The bench can reach it.** Twenty-three cases run the kit as a command in a world of their
   own. A trap about slots costs a planted row, not a server to raise and shoot. The plan's
   rule holds: a new mechanism gets a trap immediately, and a mechanism the bench cannot see is
   a mechanism that ships broken — S6 shipped two that way.
3. **There is no protocol to design, and therefore none to get wrong.** No socket, no
   authentication for the mechanism, no version skew between a driver from one tag and a daemon
   from another. The schema is one `PRAGMA user_version` and it is checked the way `run.json`
   is checked.
4. **It is the shape the kit already has.** `config.toml` is what this machine *chose*;
   the ledger is what is true on it *right now*. Two files, one owner each, exactly as the
   plan's "Where everything lives" says.

**What the process is still for**, and it is not nothing: the page (the reason the daemon exists
at all — a phone cannot read a config file over ssh), reaping leases whose driver died, and
being an address systemd can start on boot. It holds no setting and no truth of its own; kill
it and the ledger is unchanged.

The four questions, answered where the mechanism is written rather than in a survey:

| | |
|---|---|
| Can this be a program instead? | It is one. Nothing here is prose in a role's file. |
| What trace does it leave? | A row per lease, per waiter, per limit, per request, each with when and who. The page reads them; `agent-kit machine` prints them; a bench judge queries them. |
| What composes its input? | Nothing composes anything: no session is involved. |
| Who reads what it writes? | The driver (before a session), the page, `machine`, and the bench's judges. |

---

## 3 · What a slot is

**One slot is one live session.** It is taken immediately before an executor is asked to run and
released the moment it answers or fails, in a `finally`. Not per run and not per step: a run
that is waiting for a person, running the project's tests, or writing the knowledge is holding
nothing.

**Only a step done by a session takes one.** `verify`, `record` and `deliver` are programs.
A slot counts sessions, whose cost is quota and a model's memory; the project's own `make test`
is the project's business, and a second ceiling over it would be a mechanism with no
measurement behind it.

**Two ceilings, both already declared and neither read until now:**

| Ceiling | Where it is declared | What it means |
|---|---|---|
| `machine.max_sessions` | `config.toml` | how many sessions this machine runs at once, whoever they belong to. Memory before quota |
| `providers.<name>.max_sessions` | `config.toml` | of the machine's, at most this many on that provider |

A request that would break either waits. Nothing about a *project* limits anything: two runs of
one project are two sessions like any other.

**A lease is dead when its driver is.** Three things say so, in this order: the machine's boot
id differs from the one written with the lease (a reboot kills every lease, and state that does
not survive a reboot *should not*); the pid is not alive on this boot; or `expires_at` has
passed — the step's own timeout plus five minutes, which is the backstop for a pid that was
reused. Whoever asks for a slot reaps what is dead first, so the ceiling is correct with no
daemon running.

**A run has one driver, and the ledger is what says so.** A lease names its project and slug,
so a second `run go` on a run somebody already holds is refused by name — `run-held-elsewhere` —
instead of two writers racing on one `run.json`. That is open question 2, which has been
settled prose since S1 and enforced by nothing.

---

## 4 · Accounts, and the limit that outlives the session that found it

**The quota pool is the account, not the provider.** `providers.<name>.account` is already in
`config.toml` and read by nothing; it becomes the key. Where it is absent the account is the
provider's own name, which is the common case and needs no configuration.

**A limit found by a session is written down.** `ExecutorFailed` already carries `until`; the
driver records `account, until, said_at, said_by` in the ledger before it moves to the fallback
provider. Nothing else about the attempt changes.

**A limit found in the ledger costs no session at all.** Before taking a slot the driver asks
whether that account is limited. If it is, no session is started: the run waits for the reset,
or refuses with `provider-limited` naming the hour and who learned it. This is the sentence the
step is done by — the second run does not pay to be told what the first one already knows.

A limit whose `until` has passed is cleared by whoever notices, like a dead lease. A limit with
no `until` — the CLI said it was limited and named no hour — is held for one hour, and the row
says the hour was guessed rather than read. Neither of those is inventable from prose: both are
in the ledger where the page can show them.

---

## 5 · The queue, and how waiting ends

**A waiter is a row.** Before it sleeps, the driver writes what it is waiting for and when it
began; the slot goes to the oldest waiter for the account. Without that a run that arrived
first can be jumped by one that woke at a better moment, and a run can starve all night behind
a busier project. It is also what the page has to show: *what is queued* is the row, not a
guess.

**Waiting is a poll of the ledger, once a second.** No signal, no socket, no daemon in the path.
A driver that is killed while waiting leaves a row that is reaped like any other.

**Waiting has a ceiling, and it is a setting.** `[machine] wait = 7200` — two hours by default,
which is longer than a limit reset and shorter than a night. `run go --wait 0` refuses instead
of waiting. Exceeding the ceiling is `no-slot` or `provider-limited`, exit 4, naming what held
the machine and until when.

**The driver says what it is waiting for, once, when the answer changes** — not once a second.
A night's log that scrolls is a night's log nobody reads.

---

## 6 · Stop, and why skip is not here

**`agent-kit run stop <slug> <reason>` becomes two things behind one door.** If no lease holds
that run, it writes the state as it does today. If a driver holds it, it posts a request into
the ledger and says so; the driver reads it **at a step boundary**, stops the run itself with
`stopped-by-request` and the reason the person typed. One writer per run, kept.

The plan spells the command `agent-kit stop <run>`. The kit already has that door under
`run stop`, and a second spelling for one act is the nine-doors defect in miniature. The name
in the plan was a sketch; the door stands.

**Exit code 130.** A run stopped by a person is `INTERRUPTED`, which is what that code has meant
since S0 — *the operator stopped it*. Reading it as 5 would say the method refused the work,
and the method said nothing.

**Skip is not built, deliberately.** Its unit is a feature inside a batch, and there are no
batches until S8. A `skip` with nothing to skip is a field with no reader wearing a command's
clothes.

---

## 7 · The page, the port, and why there are no buttons

`http.server` from the standard library, one page and one JSON endpoint the page polls. What it
shows is exactly what the ledger holds: what is running (project, run, step, provider, model,
since), what is queued and since when, which accounts are limited and until when, and what the
machine's ceilings are.

**Read-only, as the plan says.** Every button is a way to break a night from a bus, and *showing*
is the thing that was missing.

**Port 8080, on loopback.** The block `8080-8089` is claimed for `agent-kit` in this server's
registry. The kit binds `127.0.0.1:8080`; the server's shared proxy is what puts it in the
tailnet, and the tailnet is the only way in from outside. So the kit ships no authentication and
this sentence is the record of why — a decision to revisit the day the page grows a button.
`[daemon] host` and `[daemon] port` are the settings, in `config.toml`, where a machine's
choices live.

**What the page does not show: the last lines of a live session.** The plan asks for it. Level B
reads a transcript *after* the CLI answers, and while a step is running the kit holds a blocking
child and knows nothing. Tailing it needs the adapter to say where the transcript is *before*
the answer, which is a change to the adapter contract and therefore its own step. Named here
rather than half-built.

---

## 8 · Autostart

`agent-kit daemon install` writes `~/.config/systemd/user/agent-kit.service` and prints the two
commands that enable it. `daemon start`, `daemon status`, `daemon stop` are the same thing
without systemd, which is what a container has.

Everything that knows about systemd, `/proc`, boot ids and pids is in one module, so the
sentence in the plan — *macOS is one file later* — stays true.

---

## 9 · Where the code goes, and which way the arrow points

The plan's tree puts slots and limits in `daemon/`. Taking that literally makes the driver
import the daemon, which points the arrow backwards: the build order is state → contract →
driver → adapters → daemon.

So it splits, along the line that was already there:

```
machine/            what is true on this machine right now
  ledger.py         the sqlite: leases, waiters, limits, requests
  linux.py          boot id, is-this-pid-alive, the systemd unit
daemon/             the process
  server.py         the page and its json
```

The driver depends on `machine/`, which depends on nothing but `paths` and `errors`. The daemon
depends on `machine/`. The arrow keeps pointing one way and the plan's sentence is honoured
where it means something.

---

## 10 · What changes in what already stands

| Where | What |
|---|---|
| `machine/ledger.py` | new — the ledger, and every question asked of it |
| `machine/linux.py` | new — boot id, pid liveness, the unit file |
| `daemon/server.py` | new — the page, read-only |
| `driver/runner.py` | take a slot before a session, release it after; record a limit it was told about; read a stop request at a step boundary; refuse a run somebody else holds |
| `config.py` | `[machine] wait`, `[daemon] host`, `[daemon] port` — and `account` and `max_sessions` finally get a reader |
| `cli/main.py` | `machine`, `slot take/release`, `limit set/clear`, `daemon start/status/stop/install`; `run stop` posts a request when a driver holds the run; `run go --wait` |
| `errors.py` | no new exit code — see below |
| `doctor` | the ledger, the daemon, and what is held right now |
| `bench/cases/` | seven new cases |

**No new exit code, and that is a decision rather than an oversight.** `no-slot` and a limit read
from the ledger both mean *an agent cannot be run right now*, which is what 4 has meant since
S0. A stop by a person is 130. A code that means two things is what the plan's §5 measured as
un-automatable, and adding one that means what an existing one already means is the same defect
from the other side.

---

## 11 · What the last round taught, applied here

The S6 review is a list of holes already stepped in. Each one has a shape, and each shape has a
place in this step:

| What it was | Where it lands here |
|---|---|
| a judge that is green where the trap was never planted | every judge proves its row was in the ledger before it judges |
| a green case whose two possible causes were the same place | the waiting case proves it *waited* — the step started after the lease expired — not merely that it finished |
| the same identifier twice half-wrote the file | every ledger act is one transaction: taking a slot removes the waiter row in the same one, and a release, a stop or a limit set twice is the same as once |
| a mechanism with no trap at all shipped broken | seven mechanisms, seven cases, each broken by hand afterwards |
| a case that measured an English sentence | every case reads a refusal code |
| green in the working copy only | the bench is run from `git archive HEAD` unpacked elsewhere before this is called done |
| `agent_kit.__file__` pointing at a reviewer's copy | checked first when a test fails for no reason |
| source and tests in one commit | tests are their own commit, before the one that makes them pass |

---

## 12 · Where this is proved

Seven traps. The baseline project stays what it is; what a case plants is a row in its own
world's ledger, written by the same commands a person would use.

| Trap | The mechanism it must fire |
|---|---|
| a lease held by somebody else, and `--wait 0` | the run refuses `no-slot` and starts no session at all |
| a lease that expires in a few seconds | the run waits and then lands green — and its first session began after that lease died |
| an account already limited, until an hour far away | the run refuses `provider-limited` naming the hour, without asking the provider |
| a session that says the account is limited | the ledger holds the account limited until the hour it named, after the run is over |
| a lease whose driver is not alive | it is reclaimed and the run goes on, instead of a machine deadlocked until somebody notices |
| a stop posted while the run is between steps | the run stops with `stopped-by-request`, the later steps stay pending, and the exit code is 130 |
| a second driver on a run somebody already holds | refused `run-held-elsewhere` rather than two writers on one `run.json` |

The fake provider needs one new ability for the fourth of these: **a reply file may be a refusal
instead of an answer.** A first line of `!refuse <code> [key=value…]` makes it raise
`ExecutorFailed` with that code, so a case can play a limited account, a dead session or a
provider that crashed. One mechanism, and its reader is the bench.

---

## 13 · What S7 is done when

`agent-kit bench run` reports thirty cases as fired; two runs against one account on a
one-session machine do not run at once, and the second one's own record says it waited rather
than that it slept; a limit one session paid for costs the next one nothing; a person can stop
a running night without touching a file a driver is writing; the page answers on 8080 and shows
what is held, what is queued and what is limited; and breaking any one of the seven new
mechanisms by hand makes exactly one case say it did not fire.

**Deliberately not built:** skip, which needs batches (S8); the owner's channel, which is S7a and
is about a person's phone rather than a machine's slots — folding them together is what made
the second version's control surface a live session; buttons on the page; a tail of a live
session, which needs the adapter contract to change; and any queue that reorders by anything
but the hour it was asked, because nothing has measured that a priority is needed.

---

# What was built, 24 August 2026

Everything above was built as decided. Thirty bench cases all firing, 506 tests, and the page
answering on 8080. What changed on the way is at the foot of this section, and so is what the
live run found that nothing else could have.

## The sentence the step is done by, measured

Two runs, two projects, one machine allowed one session, both on the account `fake`. The second
one's own output:

```
add-vat: waiting — no-slot: this machine runs 1 session at once and add-vat/design holds it
  attempt 1 on fake: passed
add-vat: design passed
```

And the page, read from another terminal while it was happening:

```json
{
  "held":  [{"slug": "add-vat", "step": "design", "account": "fake", "project": ".../live/one",
             "since": "2026-08-24T12:19:30+00:00"}],
  "queue": [{"slug": "add-vat", "step": "design", "account": "fake", "project": ".../live/two",
             "since": "2026-08-24T12:19:32+00:00"}],
  "limits": [], "runs": [{"slug": "add-vat", ...}, {"slug": "add-vat", ...}]
}
```

Waited for, not slept through: the second run said what it was waiting for, once, and took the
slot the moment the first gave it back. Both landed.

## Two defects the live run found, and nothing else would have

**One sqlite connection, several threads.** The daemon sweeps on one thread and answers the page
on another, and sqlite refuses a connection outside the thread that opened it. The first `curl`
got an empty reply and the log got a stack trace nobody was reading. Every test passed
throughout: they are all one thread. A connection per thread now, and two tests that ask the
ledger from four at once.

**A daemon that could not be stopped.** `shutdown()` waits for `serve_forever()` to come back,
and a signal handler runs on the very thread standing inside it. So `daemon stop` said it had
asked, and the process stayed up holding the port until it was killed. The shutdown is asked for
from another thread now. The test is a real subprocess, a real signal, and a deadline.

Both are the same shape and it is worth naming: **the daemon is the first thing in this kit with
more than one thread in it**, and the whole suite was written for a program that has one.

## Breaking the seven by hand

| What was broken | What said so |
|---|---|
| the machine ceiling never binds | `the-machine-is-full` **and** `the-machine-frees-up` |
| a run never waits for a slot | `the-machine-frees-up` |
| a standing limit is not consulted before a session | `an-account-that-is-already-limited` |
| a limit a session found is not written down | `a-session-that-says-it-is-limited` |
| every pid looks alive, so a dead driver keeps its lease | `a-slot-whose-driver-is-gone` |
| a stop is never read | `a-stop-while-the-run-is-going` |
| a second driver is let onto a run somebody holds | `a-second-driver-on-one-run` |

Six of the seven light exactly one case. The ceiling lights two, and that is the pair being
right rather than a case measuring the wrong thing: the ceiling has two sides — refusing when
there is no time to wait, and being waited for when there is — and a case that covered both
would be a case that cannot say which one broke.

Two of the breaks also tripped a second guard on the way past. The three cases about a run that
never gets as far as a session carry one reply file, and it is `!refuse
a-session-nobody-should-have-started`. When the mechanism was broken the run *did* start a
session, and that reply is what it met. A trap that costs one line and answers the question
*"and what if it does?"* is worth more than a judge that only reads the end state.

The bench was also run from `git archive HEAD` unpacked elsewhere — the check that caught S5's
blocker. Thirty of thirty there too.

## What changed on the way, against the note above

**`run stop` grew a second half rather than a second command.** As decided. What was not decided
is how it tells them apart: it asks the ledger whether a run lease stands for that project and
slug. A run nobody is driving is written directly, exactly as before.

**`slot hold` and `slot take --pid`**, which the note did not name. A case has to stand where a
driver would: hold a slot as a process that is alive and is not the run, hold a run as somebody
else, and hold a slot as a driver that has died. All three are one flag and one subcommand, and
their reader is the bench and a person untangling a machine that will not start anything.

**A case may declare `wait`.** Three of the traps need a run that refuses at once and one needs a
run that waits, and the alternative was a case that could pass arbitrary arguments to the kit,
which is a wide door for a narrow need.

**The green case about a dead lease reads the ledger with sqlite rather than through `machine`.**
Its first version asked `agent-kit machine` to prove the ghost lease was planted — and `machine`
reaps before it prints, so the proof killed what it was proving. The judge now reads the row out
of the file. A judge that cannot see what it is judging is the S5 lesson in a new costume.

## What is open, said out loud

**The queue is per account; the machine's own ceiling is not queued.** Two runs waiting on
*different* accounts, both held back by `machine.max_sessions`, are ordered by whoever polls
first rather than by who asked first. Nothing has measured that this matters — with one provider
configured there is one account — and the fix is a second ordering rule with its own trap. Named
here rather than built on a guess.

**Autostart is written and not proven.** `daemon install` writes the unit; this machine's kit
runs in a container with no systemd, so nothing here has watched it come up on boot. What is
proven is the process it starts: it serves, it sweeps, and it goes away when it is asked to.

**No authentication, deliberately.** The page binds loopback and reaches a phone through the
server's own proxy, which is inside Tailscale. That holds exactly as long as the page has nothing
to press. The day it grows a button, this sentence is what has to be revisited first.

**The limit is believed, not checked.** If a provider says it resets at 17:00 and it does not,
the ledger says 17:00 and a run wakes to be refused again. The alternative — asking the provider
whether it is still limited — is a session, which is the thing being saved.

**Still no `full` case.** Every one of the thirty answers from `providers/fake/`. S9 owns it, as
S5 and S6 both wrote down.
