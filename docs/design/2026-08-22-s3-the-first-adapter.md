# S3 — the first adapter, and a level that is measured

Built 22 August 2026 on top of S2. The plan's words: *level A first — start, send, stop, and the
session's real name reported rather than guessed. Then level B — alive, context size, limit and its
reset.* Done when the machinery of S2 runs one real step in a real session, and the driver can say
how much context that session holds. Both were done, on the real CLI, and the run below is the
proof.

## How Claude Code is driven

**Headless, one composed input on stdin, one JSON answer on stdout.** Not tmux. The second version
scraped a pane because it lived inside a session; the third version composes a step's input and
wants exactly one answer back, which is the shape `claude -p --output-format json` already has.

That answer carries more than the text: the session's own id, the model it actually used, the
window that model has, the tokens it was carrying when it answered, and the cost. Level B falls out
of reading it — no transcript parsing at all, which is the cheapest level B the plan hoped for and
did not expect from this provider.

**The session is named, not hunted.** The kit passes `--session-id`, so there is nothing to guess
and no race with a file appearing on disk. If the answer comes back under a different name, the
answer wins and the transcript is filed under what the CLI actually used: the name it *reports* is
the real one, the name we asked for was a wish.

## What is declared and what is code

`provider.toml` holds everything that is true about the tool: the binary, the flags (headless,
full access, model, effort, session, version), where each fact lives in the answer, where the
transcript lands, and the phrases by which a limited account announces itself. `adapter.py` holds
only what cannot be declared — running the process, reading the answer, turning a limit into a
refusal. Nothing outside `providers/claude_code/` names Claude Code.

Failures are named, never traced: `binary-missing`, `session-failed`, `session-timeout`,
`unreadable-answer`, `session-error`, `empty-answer`, `provider-limited` — and the last one carries
the hour it resets, because "come back later" is not an answer a night can act on.

## The level is measured

`agent-kit provider check <name>` climbs a ladder and says which rung failed:

| Rung | What it proves |
|---|---|
| `binary` | the thing is there and can be run |
| `answers` | it answers when asked what it is |
| `one_shot` | given a step's input, it returns something |
| `contract` | what it returned satisfies the step's contract |
| `observed` | it can say how much context that session holds |

The first three are level A; all five are level B. The step it asks is `probe` — which is why
`probe` was built at S2 rather than invented here. A provider that starts and answers but cannot
say how much context it holds earns A, and the command says so out loud when a provider earns less
than its own `provider.toml` declares.

Measured on this machine, 22 August:

```
  ok  binary     /home/dev/.local/bin/claude
  ok  answers    2.1.239 (Claude Code)
  ok  one_shot   617 characters came back
  ok  contract   the answer satisfied the probe's contract
  ok  observed   80,694 of 1,000,000 tokens

claude_code: level B, declared B
```

## What the first real step found

The whole of S2's machinery, one real session, a real repository:

```
see-the-tree: probe passed
```

and in `steps/0-probe/meta.json`: model `claude-sonnet-5`, session
`eada778f-…`, 54,075 tokens of a 1,000,000 window, $0.059, 11.4 seconds, and the transcript's path.
The driver can say how much context the session holds, which is what S3 was for.

The probe also did its job, and found two defects in the kit rather than in the project:

1. **The session was run in the step's own directory.** `run new` recorded no project, so the
   driver fell back to where it keeps its paperwork — six levels deep inside
   `.agent-kit/v3/runs/…/attempt-1`. The agent noticed and said so. A run now always knows where it
   is: `create_run` records the project root, and the driver falls back to the store's root rather
   than to the attempt directory.
2. **The kit dirtied the tree it was working in.** `.agent-kit/` showed up as untracked, and the
   probe reported it as something a longer job would trip over. The kit now writes
   `.agent-kit/.gitignore` containing `*` the first time it writes any state — beside its own
   files rather than into the project's `.gitignore`, so removing the kit removes every trace of it.

Neither was found by 168 passing tests. That is the argument for a step whose only job is to look
around, and the argument for running one against something real before building anything on top.

## What two reviews changed, the same day

Two reviewers read S3 — one the code, one the plan — and between them found seven blocking
defects. Six of the seven share a shape: **the kit believed something it had not measured.**

**A good answer that talks about limits was read as a limited account.** The adapter grepped the
*successful* result text for "usage limit reached" and "rate limit". A probe whose notes said *the
endpoint has no rate limit* therefore refused itself. The reviewer proved it by running the driver:
three real sessions spent, three valid answers discarded, the run failed. A limit is a thing that
happens on the failure path — `is_error`, or a non-zero exit — and that is now the only place it is
read. Reading the model's prose as if it were the account's state was the whole mistake.

**The context number was three times the truth.** The counters in the result JSON are totals over
every turn of the session, and the cached prefix is re-counted in each one, so the number grows with
the number of turns while the context does not — it can exceed the very window it is compared
against. The honest occupancy is the *last* assistant turn, and only the transcript carries it. The
same session that reported 80,694 tokens above was carrying 27,249. The totals are kept, renamed to
what they are: `tokens_billed`, spend rather than fullness.

**Two more that cost money to be wrong about.** A line of anything before the JSON — a node warning,
a shell notice — lost the whole answer, and the runner paid for it three more times; the JSON is now
found inside whatever stream it arrives in. And a byte that is not UTF-8 escaped as a decode error
nothing caught; the stream is decoded with `errors="replace"`, because an odd byte is not worth
losing an answer over.

**The ladder measured three rungs of five and printed level B.** The plan's list is *the binary is
on PATH, the login answers, the full-access flag is accepted, a one-shot job returns something, the
session's context and limit are readable.* The login had no rung of its own — a logged-out CLI
answers `--version` perfectly well — and nothing measured whether a limit could be read at all,
which is half of level B's own definition. Both are rungs now, and a rung a provider cannot be
asked is marked so rather than counted as passed: the fake climbed one rung and was being credited
with three.

**The measured level was printed and thrown away.** It is written to
`~/.local/state/agent-kit/providers.json` now, and `provider list` says *measured B on 2026-08-22*
or *not measured — A is what it claims*. A level nobody wrote down is a claim again by morning.

**A folder with only a `provider.toml` did not work**, though the plan says that is exactly what
level A is, and the registry's own docstring repeated the claim. The process runner moved to
`providers/process.py` and is built from the declaration, so a provider with no Python at all now
runs; `claude_code/adapter.py` is what is left after that — the transcript, the model, the limit,
which is precisely "what cannot be declared".

The rest, each small and each paid for in real money if left: a timeout killed the session but not
the tools it had started (the child gets its own process group now); a second model in the answer
mislabelled the model and shrank the window fivefold; what a refused attempt cost was thrown away,
so spend was invisible exactly while the kit was burning it; failures that can never come right —
a missing binary, an exhausted account — were retried three times each and now say so; the fields
in `meta.json` had no reader, and `run show` is now it; `config.toml`'s answers never reached the
provider they configure; and `check.py` moved to `driver/`, because a module that composes an input
and runs an executor is driver work, and `providers/` importing `driver/` pointed the arrow
backwards.

Measured again afterwards, on the real CLI:

```
  ok  binary     /home/dev/.local/bin/claude
  ok  answers    2.1.239 (Claude Code)
  ok  login      the account answered
  ok  one_shot   584 characters came back
  ok  contract   the answer satisfied the probe's contract
  ok  observed   26,983 of 1,000,000 tokens
  ok  limits     a limited account is read, with the hour it resets (5pm (UTC))
```

**The lesson, and it is not "write more tests".** All 169 tests passed while every one of these was
true. They passed because every fake answer in them was a clean success or a clean failure, and
nothing outside is clean. S3 is the first code that runs somebody else's process: a stream that can
carry anything, a text that can say anything, a child that can outlive its parent, and a bill. The
tests that now exist are the dirty cases, and they are the ones worth having.

**One number that is not a budget.** `context_window` is 1,000,000 for this provider and nothing in
the kit treats it as a ceiling. The plan is explicit that the old 210k was fitted to the price of a
token and the cache rather than the size of a window, and that every provider is measured again.
Until something measures it, this number is what the window holds, not what a step should be allowed
to spend.

## Open, and it wants a decision at S4

**A driven session inherits instructions the kit did not compose.** The probe's first real answer
came back in Russian, because the operator's own `~/.claude/CLAUDE.md` says to write in Russian —
and that file is read by every Claude Code session on this machine, including one the kit started.
Harmless in a note; not harmless when the method's prose and a personal instruction disagree about
how work is done.

The plan's principle is unambiguous — *the driver composes a step's input* — and today the driver
composes most of it. Claude Code offers `--setting-sources` and `--bare` to control what else is
read. The project's own `CLAUDE.md` is knowledge the step genuinely wants; the operator's global
one is not. S4 decides where that line goes, because S4 is where prose starts changing what gets
built.
