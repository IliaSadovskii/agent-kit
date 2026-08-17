<!-- The block `blueprint` keeps in the project's own CLAUDE.md, and the only thing this kit ever
     writes into that file.

     Why it exists: every command of this kit finds the knowledge by path, so none of them needs a
     map. What needs one is everything that is *not* a command — a plain conversation in the
     project's directory, an outside agent, a person who has just been handed the repository. Claude
     Code loads CLAUDE.md into every session there without being asked, which makes it the one place
     a map is read for free. Measured across three live projects using this kit: one had such a
     section, written by the owner's own hand, and two had nothing.

     Rules for writing it:

     - **Only between the markers.** That file is the project's, and on some servers it also carries
       a section the host's own contract requires. Rewrite what is inside; never touch a line
       outside.
     - **In the project's language** (`.agent-kit/project.yml` → `language`), because its readers are
       people and sessions working on that project — unlike the rest of this payload.
     - **Only the lines that are true today.** A project with no audits yet has no `docs/audits/`,
       and a map naming an empty directory teaches the reader that the map is approximate.
     - **One line each, and no explaining.** This is an address list, not documentation. What each
       record is for is written in the record.
     - The full version of this, with who may write and who may close each one, is
       `${CLAUDE_PLUGIN_ROOT}/rules/channels.md` — that file is for the kit's own sessions; this
       block is the short form for everyone else.
-->

<!-- agent-kit:where -->

## Where this project keeps what it knows

Built with `agent-kit` (`/agent-kit:*`). What the commands write and read:

- `docs/knowledge/` — the description of the product every build works from: the product itself, the
  actors, the entities, the actions, the screens, the integrations, the scenarios, the MVP bounds.
  Written by `/agent-kit:blueprint` with the owner, and by nothing else.
- `docs/technical_debt.md` — work that was understood and deliberately not done.
- `docs/manual.md` — what only the owner can do: a secret, an account, a device. Each line carries a
  command that proves it has been done.
- `docs/audits/` — the work lists the audit lenses wrote.
- `docs/runs/` — one small record per delivered batch: its pull request, its branches, what it cost.
- `.agent-kit/project.yml` — this project's corner of the kit: its language, its commands, a verdict
  per slot of the knowledge.
- `.agent-kit/runs/` — the working state of runs. Not in git, and it dies with this machine.

Reading the knowledge before answering anything about the product is cheaper than deriving it from
the code, and it is what the product is held to.

<!-- /agent-kit:where -->
