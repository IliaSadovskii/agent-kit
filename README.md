**English** · [Русский](README.ru.md)

# agent-kit

A Claude Code plugin for building applications with an agent: one place the project is described,
and commands that build from that description — a bug fix, a feature, a batch, a whole MVP.

Built for programmers. It assumes you read diffs, run tests, and want to know what a command will
cost before you type it.

> **Being rebuilt.** Today `/agent-kit:blueprint` and `/agent-kit:ship` work; the rest are declared
> and do nothing. For the last complete version install the `v0.17.0` tag.

## Install

```text
/plugin marketplace add IliaSadovskii/agent-kit
/plugin install agent-kit@agent-kit
```

Pin it for a repository in `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agent-kit": { "source": { "source": "github", "repo": "IliaSadovskii/agent-kit" } }
  },
  "enabledPlugins": { "agent-kit@agent-kit": true }
}
```

Needs `git`, and `gh` for pull requests.

## Commands

### `/agent-kit:blueprint [what to add or reconsider] [--check]`

Describes the project: what it is and deliberately is not, the stack and the rules the build
follows, actors, entities, actions, screens, integrations, scenarios, MVP bounds. Interviews you,
writes `docs/knowledge/`, commits each slot as it is settled — stop whenever, it resumes.

| Form | Does |
|---|---|
| `blueprint` | continues where the last session stopped: what is empty, stale, or flagged by an earlier run |
| `blueprint "rework the map"` | takes something you thought of after the fact into the right slots |
| `blueprint --check` | run by hand: where the project stands — built, planned, open questions, assumptions waiting. Run by another command: silent when clean |

On a project with existing code it reads the code first and brings you a draft to correct. It never
starts your application, and it does not restate documents you already have — it links to them by
section.

### `/agent-kit:ship [action key, or what to build]`

One feature to a pull request: design against the entry, build, verify, review, open the PR.

Asks only when a fork is expensive to reverse — stored data, a public contract, permissions, money.
Everything else is decided and recorded in the PR. Tests come from the entry's own lines, and the
risky ones are written before the code. One review pass reads the diff against the entry; a security
pass runs when the diff touches auth, untrusted input, money, files, migrations or outbound calls.

Works without a blueprint too, from a written task; it says once what that costs.

### `/agent-kit:fix [what is wrong] [--pr <n>]` — not written yet

Something is wrong and it is small: your description of it, a failure you observed, or a review
round on an open pull request.

### `/agent-kit:sprint [theme]` — not written yet

A batch of features briefed in one sitting, then built autonomously and delivered as one mergeable
pull request.

### `/agent-kit:mvp [scope]` — not written yet

From the blueprint to a running prototype: composes batches from the MVP bounds and runs them until
every scenario passes against the live application.

### `/agent-kit:audit <lens> [area]` — designed, not written yet

Reads existing code, compares it to the blueprint, writes a work list — tests, security,
performance, debt, production readiness — and changes nothing. For code nobody watched being
written: an adopted project, or a batch an autonomous run landed overnight.

## The loop

**Know → build → check → build.** Enter wherever you are:

| You have | Order |
|---|---|
| an idea | `blueprint` → `mvp` → `audit` → `sprint` |
| a half-built skeleton | `blueprint` → `audit` → `ship` / `sprint` |
| a finished application | `blueprint` → `audit` → `sprint` → `fix` |

Every command works with the knowledge missing except `mvp`, which refuses — without the MVP bounds
and the scenarios it has no stopping condition. You do not have to start with `blueprint`: a bug fix
today is a fine first command.

## Where things live

| Path | What | Committed |
|---|---|---|
| `docs/knowledge/` | the project's description, one file per slot | yes |
| `.agent-kit/project.yml` | language, the project's own commands, one verdict per slot | yes |
| `.agent-kit/runs/<slug>/` | a run's state and its event log | no |

The kit works on branches, never merges a pull request, and writes prose nowhere except
`docs/knowledge/`.

## Working on the kit itself

`scripts/validate.sh` checks layout, manifests, versions and internal references; CI runs the same
script. `scripts/measure.py <project>` reports what runs cost, per session or per branch. Design
notes are in [docs/design/](docs/design/), release notes in [CHANGELOG.md](CHANGELOG.md).

MIT licensed.
