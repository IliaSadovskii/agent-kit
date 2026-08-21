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
