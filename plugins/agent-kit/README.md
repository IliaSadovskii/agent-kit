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
| `/agent-kit:ship` | one feature, end to end — **not written yet** |
| `/agent-kit:sprint` | a batch of features, autonomous — **not written yet** |
| `/agent-kit:mvp` | from the blueprint to a running prototype — **not written yet** |

Only `blueprint` works today. The other four are declared so the shape of the kit is visible, and
they do nothing when invoked.

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

## Working in a repository

The kit works on branches and never merges a pull request. A `PreToolUse` hook will return in v1 to
enforce that mechanically rather than by instruction.
