# agent-kit

A development kit for building software with long-running Claude Code sessions. It is being
rebuilt: version 1 starts from an empty command set and adds one command at a time, each on its own
argument. What the rewrite concluded, and why, is in
[docs/design/kit-v1.md](../../docs/design/kit-v1.md).

## Commands

| Command | What it does |
|---|---|
| `/agent-kit:blueprint` | the project's knowledge layer: an interview that writes what the project knows, and `--check` that audits it |
| `/agent-kit:fix` | something is wrong and it is small — **not written yet** |
| `/agent-kit:ship` | one feature end to end: design against the blueprint, build, verify, review, pull request |
| `/agent-kit:sprint` | a batch of features, autonomous — **not written yet** |
| `/agent-kit:mvp` | from the blueprint to a running prototype — **not written yet** |

`blueprint` and `ship` work today. The other three are declared so the shape of the kit is visible,
and they do nothing when invoked.

## Blueprint

Everything the project knows about itself, written before anything is built: what the product is
and deliberately is not, the stack and the rules the build follows, the actors, the entities and
their states, the actions, the screens, the integrations, the scenarios that have to pass, and the
MVP bounds.

It writes into `docs/knowledge/`, one file per slot, copied from `templates/knowledge/` — the
templates carry the shape of a record, so the format and its description cannot drift apart. The
project's language, its commands, and one verdict per slot live in `.agent-kit/project.yml`.

Two modes:

- `blueprint` — the interview, resuming wherever the last session stopped. It works only on what is
  empty, stale, or marked by an earlier run, so a second run costs minutes rather than hours.
- `blueprint --check` — mechanical audit: fields, key references, orphans, stale sources, the state
  of the pull requests behind entries being built. Seconds, asks nothing, silent when clean.

**One writer, one trigger.** Only blueprint rewrites knowledge, and only you start blueprint. A
build command may leave a marked note where it had to assume something, and `--check` may flag what
went stale — but nothing revises knowledge on its own.

## Ship

One feature — an action from the blueprint, or a small group of actions and screens — to a pull
request that can be merged without reading the diff.

Blueprint says what the feature does; ship decides how, here: which files, which layer, which
existing helper, which seam the tests sit at. It asks only where a fork is expensive to reverse and
someone is present; everything else is decided and recorded. The tests are the entry's own lines —
what changes, what the initiator sees, what others see, what can go wrong — written before the code
where the risk is, so a test that cannot fail cannot pass unnoticed. One review pass reads the diff
against the entry that was approved, a security pass runs on a diff trigger, and the pull request is
opened after the fixes rather than before.

Why it is shaped this way, and what was rejected: [docs/design/ship.md](../../docs/design/ship.md).

## Working in a repository

The kit works on branches and never merges a pull request. A `PreToolUse` hook will return in v1 to
enforce that mechanically rather than by instruction.
