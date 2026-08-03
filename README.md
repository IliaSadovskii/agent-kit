**English** · [Русский](README.ru.md)

# agent-kit

A Claude Code plugin. You describe the project once, and the commands build from that description.

The description lives in `docs/knowledge/`: actors, entities, actions, screens, integrations,
scenarios, the stack, and what is in the first version. `blueprint` writes it. `ship`, `fix`,
`sprint` and `mvp` read it and write code. `audit` compares the code back to it.

> Being rebuilt. `blueprint` and `ship` work today; the rest are declared and do nothing. The last
> complete version is the `v0.17.0` tag.

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

### `fix <what is wrong>` · `fix --pr <n>` — not written yet

A small change: something you describe, a failure you hit, or a round of review comments.

### `sprint <theme>` — not written yet

Several features briefed in one sitting, then built unattended and delivered as one mergeable PR.

### `mvp` — not written yet

Builds everything inside the MVP bounds and keeps going until the scenarios pass against the running
application.

### `audit <lens> [area]` — designed, not written yet

Compares existing code to the description and writes a work list: tests, security, performance,
debt, production readiness. Changes nothing. Lenses run one at a time.

## Order of work

| You have | Order |
|---|---|
| an idea | `blueprint` → `mvp` → `audit` → `sprint` |
| a half-built skeleton | `blueprint` → `audit` → `ship` / `sprint` |
| a finished application | `blueprint` → `audit` → `sprint` → `fix` |

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
