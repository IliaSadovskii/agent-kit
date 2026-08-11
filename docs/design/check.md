# What the check does, rule by rule

Moved out of `skills/blueprint/SKILL.md` in 2.4.0. It described a program rather than instructing a
run: no step of an interview ever acted on it, and every step re-read it — forty-five lines against
a command that had grown past the ceiling this kit sets for itself. The rules live in `check.py`,
which is why every command can run them and why one rule cannot mean two things.

## The rules

Mechanical only. No reading for quality, no grader, no research — that is what makes it cheap
enough to run ahead of everything.

- **States.** For every entry marked `building`, read its pull request: merged makes it `built`,
  closed unmerged puts it back to `planned`.
- **Fields.** Every record has the `fields:` its file's header declares, each with content. A field
  runs until the next field or the next heading, so one whose answer is a list on the lines below it
  is filled — reading only the label's own line reports every scenario in the file as empty.
- **References.** Every key resolves: the actor exists, the entity exists, an action named in a
  screen transition or a scenario step exists. Whether a status an action sets is one the entity
  declares is **not** checked — the program says so in its own closing line, and reading it as
  checked is how a wrong status survives.
- **Orphans.** An actor with no action, an entity nothing creates, a screen nothing leads to and
  which is not an entry point.
- **Sources.** For every `source:`, the file and heading exist and the hash still matches.
- **Stack age.** The direct dependency manifests against their recorded hash; and
  `stack_researched` past six months, named once.
- **Notes.** Count the `[assumed …]`, `[found …]`, `[stale …]` and `[accepted …]` blocks and list
  them.
- **Verdicts.** Slots with no verdict in `project.yml`.
- **Unmet promises.** Every test carrying `agent-kit:unmet` outside `docs/`, with the entry it
  names — flagging a key no entry defines, and a project that has marks but no `tests.unmet`.
- **Hashes it can compute itself.** `--record` rewrites every `source:` and every dependency hash in
  place. Use it rather than copying a printed value into a file: a hash carried by hand is how the
  pre-4-August ones came to be invented, and a value nobody can recompute proves nothing. A recorded
  hash shorter than eight characters is from that era — re-record and move on, no document changed.
- **Debt.** The open items of `docs/technical_debt.md` — work earlier runs decided not to do.

Silent when clean, exit code 1 when not — with one exception: unmet promises are listed whenever
they exist and change no exit code, because a recorded promise is a statement about the product, not
a defect in the knowledge. Otherwise one screen: what is open, what is stale, what does not line up,
and what it could not see. `epic` refuses to start when a slot in its scope is not settled; the other
three report and carry on.

Your job around it is the part a program cannot do: say which of its findings matter for what the
owner is about to do, and offer to fix them here and now.
