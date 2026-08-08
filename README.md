**English** · [Русский](README.ru.md)

# agent-kit

A Claude Code plugin. You describe the project once, and the commands build from that description.

The description lives in `docs/knowledge/`, one file per slot: what the product is and deliberately
is not, the actors, the entities and their states, the actions, the screens, the integrations, the
scenarios, the stack — and what is in the first version. `blueprint` writes it. `ship`, `fix`,
`sprint` and `mvp` read it and write code. `audit` compares the code back to it.

## Install

```text
/plugin marketplace add IliaSadovskii/agent-kit
/plugin install agent-kit@agent-kit
```

For a whole repository, in `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agent-kit": { "source": { "source": "github", "repo": "IliaSadovskii/agent-kit" } }
  },
  "enabledPlugins": { "agent-kit@agent-kit": true }
}
```

Needs `git` and `python3`, plus `gh` for pull requests. `sprint` and `mvp` also need `tmux`: they build each feature in its own visible session.

## Commands

### `blueprint`

Interviews you and writes the description. Each slot is committed as it is finished, so you can stop
and come back.

- `blueprint` — continue with whatever is empty, stale, or flagged by an earlier run
- `blueprint "rework the map"` — add or rethink one thing
- `blueprint --check` — where the project stands: built, planned, open questions, assumptions
  waiting on you

On an existing codebase it reads the code and brings you a draft to correct. It does not start your
application, and it does not restate documents you already have — it links to them.

### `ship <action key | what to build>`

One feature, one pull request. Designs against the entry, builds, tests, reviews, opens the PR.

You are asked only about forks that are expensive to reverse: stored data, public contracts,
permissions, money. Tests come from the entry and are written before the code. The PR lists what was
assumed and what was proven.

Also works with no blueprint, from a written task.

### `fix <what is wrong>` · `fix --pr <n>`

A small change: something you describe, a failure you hit, or a round of review comments. The cause
is found first, then proved by a test that fails before the change and passes after — and the fix is
undone once to watch that test fail again. It changes the least that makes it pass; the tidy-up next
to it goes to the ledger.

### `sprint <theme>`

Several features briefed in one sitting, then built unattended — each as its own visible session,
one after another, chained so the batch arrives as a single mergeable pull request. A control
session stands beside the run to say how it is going and to take *skip* and *stop*.

### `mvp`

Everything inside the MVP bounds, built while nobody watches, then audited, then proved by the
scenarios against the running application — one pull request you open and click through.

It asks one question, at the start: this scope, or narrower, with the price of each. After that it
runs in batches — each a sprint of about five features — and after every batch the pull request says
what now works. It owns no build logic of its own: it composes the batches and the same driver,
`ship` and closing session do the rest.

### `next`

For a session opened after a break: where the project stands, what is in the way, and the one command
to run, with the reason. Reads branches, pull requests and their CI, runs left mid-flight, the debt
and the audits; changes nothing but the bookkeeping it has just verified.

### `audit [lens] [area]`

Compares existing code to what the description says should be true, and writes a work list.
Changes nothing.

| Lens | What it checks |
|---|---|
| `tests` | what the code promises and no test checks — and where a test exists but proves something else |
| `deps` | which packages are outdated or have known holes, and whether it actually matters here |
| `scenarios` | whether a user can get through a whole path, and at which step it breaks |
| `security` | who can see or do something they should not |
| `performance` | where the code is slow for a plain reason: extra queries, unbounded selects, work inside a loop |
| `conventions` | where the code drifted from the rules you wrote for it yourself |

- `audit` — every lens, cheapest first
- `audit tests` — one lens; `тесты` and `tests` are the same one
- `audit tests moderation` — narrowed to an area
- `audit "why is moderation slow"` — says which lens it understood, then runs it

Every run also checks the code for surfaces the description does not have, and the reverse. Findings
carry the file and line proving them, so a verdict can be checked in ten seconds. The list lives in
`docs/audits/<lens>.md`, grouped into batches of one `ship` run each; mark an item declined and later
runs leave it alone.

## Where it runs

The kit is prompts, two Python scripts and a hook. What differs between machines is one thing: can
it give every feature its own live session.

| Where | What works | What it costs you |
|---|---|---|
| a server left running | all seven commands | you need a machine that stays up |
| your own machine, with `tmux` | all seven commands | the run stops when the machine sleeps, and you are the one watching it |
| your own machine without `tmux`, or Windows | five: `blueprint`, `ship`, `fix`, `audit`, `next` | no `sprint`, no `mvp` — features go one at a time |

**Why a server suits the unattended half.** A sprint is a night and an `mvp` can be a day. When the
account limit is reached the driver reads the reset time, sleeps until it, and types one line into
the session, whose context is still intact — that costs the wait and nothing else, but only if the
machine is awake. A laptop that sleeps turns the same limit into a run you restart by hand.

**What you keep, wherever it runs.** Every feature is built in a real session you can attach to,
read, and type into — that is what makes a stalled run rescuable and a question at two in the
morning answerable. Headless children would drop the `tmux` requirement and take all of that with
them, which is why they were rejected.

**Nothing else is assumed.** A logged-in Claude Code, `git`, `python3`, `gh`, and `tmux` for the two
unattended commands. If you would rather not assemble that yourself, the server this kit was built
on is a separate project of its own: [IliaSadovskii/agent-vps](https://github.com/IliaSadovskii/agent-vps) — it
keeps sessions alive across reboots and reachable from the mobile app. The kit neither needs it nor
knows about it.

## Order of work

| You have | Order |
|---|---|
| an idea | `blueprint` → `mvp` → `sprint` |
| a half-built skeleton | `blueprint` → `audit` → `ship` / `sprint` |
| a finished application | `blueprint` → `audit` → `sprint` → `fix` |
| no idea where you stopped | `next` |

`audit` is for code nobody watched being written — an inherited project, or a batch that landed
overnight. After `ship` it is redundant.

`ship`, `fix` and `sprint` work with no blueprint at all, from a written task — a project's first
command should not be an hour of interview. `mvp` requires one, because bounds are what tell it when
to stop. `audit` requires one too, with a single exception: the `deps` lens has the registries as its
reference and needs no description. And `next` will run, but with nothing to rank it will only tell
you to write the blueprint.

## Files

| Path | What | In git |
|---|---|---|
| `docs/knowledge/` | the description, one file per slot | yes |
| `.agent-kit/project.yml` | language, the project's commands, one verdict per slot | yes |
| `.agent-kit/runs/<slug>/` | run state and event log | no |

The kit works on branches and never merges a pull request, and since 1.0.0 that is machinery
rather than instruction: while a run is in flight, a hook outside the model refuses to merge, to
force-push, and to push to the default branch. Your own sessions never meet it.

## Developing the kit

`scripts/validate.sh` checks layout, manifests, versions, internal references, the shape of a run
file, the payload's own markdown, the guard's registration, and that both READMEs match the commands
that ship; CI runs the same script. `scripts/measure.py <project>` reports what runs cost, by session or by branch. Design notes
in [docs/design/](docs/design/), releases in [CHANGELOG.md](CHANGELOG.md).

MIT.
