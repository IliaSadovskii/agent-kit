**English** · [Русский](README.ru.md)

# agent-kit

A Claude Code plugin. You describe the project once, and the commands build from that description.

The description lives in `docs/knowledge/`: actors, entities, actions, screens, integrations,
scenarios, the stack, and what is in the first version. `blueprint` writes it. `ship`, `fix`,
`sprint` and `mvp` read it and write code. `audit` compares the code back to it.

> Being rebuilt. All seven commands are written; `fix` and `mvp` have not yet met a live run.
> The last version of the line before the rewrite is the `v0.17.0` tag.

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

Needs `git`, plus `gh` for pull requests.

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

## Order of work

| You have | Order |
|---|---|
| an idea | `blueprint` → `mvp` → `sprint` |
| a half-built skeleton | `blueprint` → `audit` → `ship` / `sprint` |
| a finished application | `blueprint` → `audit` → `sprint` → `fix` |
| no idea where you stopped | `next` |

`audit` is for code nobody watched being written — an inherited project, or a batch that landed
overnight. After `ship` it is redundant.

Only `mvp` requires a blueprint. The rest work without one.

## Files

| Path | What | In git |
|---|---|---|
| `docs/knowledge/` | the description, one file per slot | yes |
| `.agent-kit/project.yml` | language, the project's commands, one verdict per slot | yes |
| `.agent-kit/runs/<slug>/` | run state and event log | no |

The kit works on branches and never merges a pull request.

## Developing the kit

`scripts/validate.sh` checks layout, manifests, versions and internal references; CI runs the same
script. `scripts/measure.py <project>` reports what runs cost, by session or by branch. Design notes
in [docs/design/](docs/design/), releases in [CHANGELOG.md](CHANGELOG.md).

MIT.
