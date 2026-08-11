# What the check found, and what you do about it

Every build command runs the knowledge check before it starts, and every one of them meets the same
findings. This is that reaction, in one place: it was written twice, in `ship` and in `sprint`, in
different words — and when a third kind of block was added, one of the two did not learn about it
and its runs met a record they had no instruction for.

The command line itself stays in each command, because what they ask for differs.

| What it found | What you do |
|---|---|
| a slot in scope unsettled, or an entry incomplete | stop, name what is missing, offer `/agent-kit:blueprint` — the owner is here and closes it in a minute |
| no `docs/knowledge/` at all | **carry on.** Work from the task as written, and say once that without an entry the tests can only aim at what the task says done means. A project's first command should not be an hour of interview |
| `[assumed …]` blocks on the entries in scope | with `gate: owner`, show them and offer to settle them now — this is the last moment anyone is here. **When they answer, write it into the entry and delete the block**, in its own `docs(knowledge):` commit before you start: you are transcribing their answer, not deciding, and a block left open is a question asked twice. With `gate: none`, follow them as written |
| `[stale …]` blocks on those entries | an earlier feature outdated a sentence and could not correct it. The block says what the entry claims and what is true now, so with `gate: owner` apply it — same commit, same rule: transcribe, never decide. With `gate: none` leave it, and read the entry as the block corrects it |
| an entry's state line behind its merged pull request | not yours. `/agent-kit:next` and `blueprint --check` move it, and a build command that started by writing to knowledge would fail its own clean-tree rule |
| a run file at a step no reader knows, or fields the template does not have | history from an earlier run, and not a reason to stop. It is said so the drift is visible while it is still happening |
| **knowledge written by an older kit** — a record declaring fewer fields than the template, a file with fewer sections | **not a reason to stop, and not yours.** Say it in one line with the count, so the owner learns it exists, and carry on: the entries you are about to build are answerable as they stand, they were written that way on purpose, and only `/agent-kit:blueprint` may change what a record requires. Never fill the missing field yourself — that is deciding what the product must describe, which is the one thing no build command may do |
| nothing | continue without a word about it |

**Promises the product does not keep are read differently by each command**, so that row lives in the
command rather than here: `ship` reads the marked test for the entry it is about to touch; `sprint`
counts them, and with no theme offers them as a batch of their own.

Two things this table never does. It never turns a finding into a reason to stop, except the first
row — everything else is a statement about the project, and a command that halted on one would be
halting over its own memory. And it never rewrites what an entry *requires*: settling a block means
writing down an answer the owner has just given, and nothing else.
