**English** · [Русский](README.ru.md)

# agent-kit

A Claude Code plugin. You describe the project once, and the commands build from that description.

The description lives in `docs/knowledge/`, one file per slot: what the product is and deliberately
is not, the actors, the entities and their states, the actions, the screens, the integrations, the
scenarios, the stack — and what is in the first version. `blueprint` writes it. `ship`, `fix`,
`sprint` and `epic` read it and write code. `audit` compares the code back to it. And `advise` looks
the whole thing over — the product, the code and the money — and says where it is weak and where it
could grow.

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

Needs `git` and `python3`, plus `gh` for pull requests. The other five commands stop there;
`sprint` and `epic` also need `tmux`, because they give each feature its own live session.

Those two run for a night or a day and wait out account limits by sleeping until the reset, so they
want a machine that does not sleep either — any server will do. If you would rather not arrange one,
[agent-vps](https://github.com/IliaSadovskii/agent-vps) is a server already set up for this: sessions
survive reboots and are reachable from the mobile app. The kit does not need it and knows nothing
about it.

## Describe it

### `blueprint`

Interviews you and writes the description. Each slot is committed as it is finished, so you can stop
and come back.

- `blueprint` — continue with whatever is empty, stale, or flagged by an earlier run
- `blueprint "rework the map"` — add or rethink one thing
- `blueprint --check` — where the project stands: built, planned, open questions, assumptions
  waiting on you

On an existing codebase it reads the code and brings you a draft to correct. It does not start your
application, and it does not restate documents you already have — it links to them.

### `advise [product | code | money] [area]`

**Where the project is weak, and where it could grow.** Not whether the code matches the description
— that is `audit`. This one questions the idea itself and the way it is built.

| | What it looks for |
|---|---|
| `product` | the idea and the people using it — what a user cannot finish because a step is missing, what is built and nobody needs, what people like these expect from a product like this and do not find here, who is one field away from being served, and what to drop because a narrower product is the better one |
| `code` | how it is built — where the present approach quietly stops working as the project grows and at what number, and what would make it simpler, harder to break and faster to change, including how long you wait on the tests and the environment |
| `money` | what it costs to run and what it could earn — what is given away that costs you per use, limits that exist in the plan and nowhere in the code, and what people would pay for that there is no way to pay for |

Each area is looked at twice: close up, walking your own files and citing them, and from a step back,
including what similar products do now on the live web, with links and dates. **Every line says
which of the two it came from**, so judgement is never dressed up as evidence. Nothing already
planned, already found by an audit, already in the debt list or already refused comes up again.

Then you say **yes** — and it is written into the description properly while you are still there, so
`ship` can build it like anything else; **no** — recorded with your reason, and a refusal over a
number keeps the number, so the next run checks whether it has moved; or **later** — it returns as an
old question rather than a fresh idea.

## Build it

The same pipeline at three sizes, and one command for repairs. Each designs against the description,
writes the tests from it, reviews itself and opens a pull request; what differs is how much it takes
on before it stops asking you anything.

### `epic`

Everything that is left, built while nobody watches, then audited, then proved — one pull request
you open and click through. The MVP bounds the first time; run it again once those are built and it
offers what is still planned, or what the project owes, each with its own finish line.

One question, at the start: this scope or narrower, with the price in hours of each. Then it runs in
batches of about five features, and after every batch the pull request says what now works.

### `sprint <theme>`

Several features briefed in one sitting, then built unattended — each as its own visible session,
one after another, chained so the batch arrives as a single mergeable pull request. A control
session stands beside the run to say how it is going and to take *skip* and *stop*.

### `ship <action key | what to build>`

One feature, one pull request. Designs against the entry, builds, tests, reviews, opens the PR.

You are asked only about forks that are expensive to reverse: stored data, public contracts,
permissions, money. Tests come from the entry and are written before the code. The PR lists what was
assumed and what was proven. Also works with no blueprint, from a written task.

### `fix <what is wrong>` · `fix --pr <n>`

A small change: something you describe, a failure you hit, or a round of review comments. The cause
is found first, then proved by a test that fails before the change and passes after — and the fix is
undone once to watch that test fail again. It changes the least that makes it pass; the tidy-up next
to it goes to the ledger.

## Check it

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

Findings carry the file and line proving them, so a verdict can be checked in ten seconds. The list
lives in `docs/audits/<lens>.md`, grouped into batches of one `ship` run each; mark an item declined
and later runs leave it alone.

### `accept [pull request number]`

For the moment a long run has ended and its pull request is too big to read. It reads the
description, the run files and the state — never the diff, which was reviewed twice already — and
answers in the order you act: can this be merged, what needs your hands and how to tell each step
worked, what is still waiting on you, what was decided without you, and what is not proven or was
never exercised at all.

Changes nothing. Run it before merging, and again after, when it becomes the list of what to go and do.

## Find your bearings

### `next`

For a session opened after a break: where the project stands, what is in the way, and the one command
to run, with the reason. Reads branches, pull requests and their CI, runs left mid-flight, the debt
and the audits; changes nothing but the bookkeeping it has just verified.

## Order of work

| You have | Order |
|---|---|
| an idea | `blueprint` → `advise` → `epic` → `accept` |
| a half-built skeleton | `blueprint` → `audit` → `ship` / `sprint` |
| a finished application | `blueprint` → `audit` → `advise` → `sprint` → `fix` |
| no idea where you stopped | `next` |

`audit` is for code nobody watched being written — an inherited project, or a batch that landed
overnight. After `ship` it is redundant.

`advise` pays best at two moments: straight after `blueprint`, while nothing is built and changing
your mind is free; and after a sprint, when the product is real enough to be judged honestly.

`accept` comes after any run long enough that its pull request stopped being readable — usually an
`epic`, sometimes a large `sprint`.

`ship`, `fix` and `sprint` work with no blueprint at all, from a written task — a project's first
command should not be an hour of interview. `epic` requires one, because bounds are what tell it when
to stop. `audit` requires one too, with a single exception: the `deps` lens has the registries as its
reference and needs no description. `advise` requires one as well — with nothing written down, there
is nothing for it to be about. And `next` will run, but with nothing to rank it will only tell you to
write the blueprint.

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
