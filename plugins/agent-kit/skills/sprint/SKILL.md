---
name: sprint
description: Build a batch of features one after another while nobody watches — compose the batch with the owner in one sitting, then let a driver run each feature as its own visible session and deliver the whole batch as one pull request.
argument-hint: "[theme, or a list of work]"
disable-model-invocation: true
---

# Sprint

A batch of features around one theme, built by `ship` one at a time, delivered as one pull request.

You are the **brief**: you compose the batch with the owner, write a run file per feature, and start
the driver. You do not build anything and you do not design the features — `ship` does both, and it
will have read more of the code than you have.

| Invocation | You are |
|---|---|
| `/agent-kit:sprint <theme>` | the brief — this file, and afterwards the window |
| `/agent-kit:sprint` | the same, over work the project already has written down — see *With no theme* |
| `/agent-kit:sprint --resume <run dir>` | the brief, restarting a driver over children already written |
| `/agent-kit:sprint --close <run dir>` | the closing session, started by the driver — `${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/close.md` |
| `/agent-kit:sprint --window <run dir>` | stand beside a run somebody else started — `${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/window.md` |

Read the file named for you and nothing else in this table.

## What the brief is for

Two things, and they are the only two a child cannot supply: you see the whole batch, and the owner
is here. A child cannot notice that two features write to the same table or that an audit item was
fixed last month, and once the run starts there is nobody to answer anything.

So your job is to **pre-answer the questions the night will have nobody to ask** — and then get out
of the way.

## Before you ask anything

Run the knowledge check — mechanical, seconds, quiet unless something is open or the product owes a
promise. `--status` because composing a batch is the one moment where what is `planned` against
`built` is worth the line, and it names the planned entries:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
```

| What it found | What you do |
|---|---|
| an entry in the batch incomplete, or a slot unsettled | name it and offer `/agent-kit:blueprint` — the owner is here and closes it in a minute |
| `[assumed …]` blocks on entries you are about to build | show them; this is the last moment anyone can answer |
| promises the product does not keep | one line with the count, then go on composing the batch the owner came for. With no theme they are one of the candidates you put up — see below |
| no `docs/knowledge/` at all | carry on from the owner's own words, and say once that without entries the tests can only aim at what each task says done means |
| nothing | continue without a word about it |

Then read, in one message: `.agent-kit/project.yml`, the batch's source (an audit's work list, the
roadmap, whatever the owner named), and **a section per candidate entry** — never the whole file.
Read `docs/knowledge/stack.md` once. Read code only where you are in doubt, and only to answer *does
this already exist?* and *who else touches these files?* The deep read belongs to the child.

## Compose the batch

Ask only what different answers would send down different roads, where the rework is expensive.
Anything the blueprint already answers is not a question. Finding nothing to ask is an honest
outcome — say what you are taking and in what order, and start.

What is worth asking, when it applies:

1. **Composition** — which items of a long list are taken now. Propose a set that is one topic.
2. **Order and collisions** — which features touch the same ground, and therefore which must follow
   which.
3. **A fork found early** — an entry that stores something, crosses a contract, moves a permission
   boundary or touches money without saying how. Overnight that becomes an assumption and then a
   migration; ask it now, with a recommendation.
4. **An open assumption** from an earlier run, under an entry in the batch.
5. **Whether the owner is reachable while it runs.** This is the only thing that decides whether a
   child waits on an expensive fork or takes it as an assumption.

Ask per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md` — with options, the recommendation first, one at a
time. Then present the batch and its order as one screen, with what you take as given. Do not sketch
the features: the owner sees each design in the pull request, not before the run.

### With no theme

Called with nothing, you do not ask the owner to think one up. The project has already written down
what it owes, in four places:

- the entries still **`state: planned`** — described and not built. `--status` names them, so you
  need no entry file to list them;
- the **open `[assumed …]` notes** and the **promises the product does not keep** — both printed by
  the same check;
- the **work lists of the audits** in `docs/audits/`. The check does not open those, so read the
  newest file per lens yourself — the unchecked boxes only, never the covered half.

A work list written before the last batch may already be done — nothing marks an audit's boxes when
a sprint closes them. Cheapest check there is: the entry's state line. An item whose entry is
`built` and whose lens has not run since is stale, and stale items go at the bottom, named as such,
rather than into the batch.

Put them up as one screen, a line per candidate with its size, and ask which batch to take. That is
the composition question you would have asked anyway; there is no separate command for debt, because
debt is just the part of the list nobody chose yet.

A batch of unkept promises is composed differently from the rest, and this is the whole of it: read
the marked test and the entry it names together, and have the owner say **which side is wrong**. The
product — the feature makes the entry true and unmarks the test. Or the entry — the feature deletes
the test and hands the wording to `blueprint`. That answer is the design; a child inherits it in
`task` and settles nothing on its own.

What the owner leaves undecided stays marked and stays on the list. Nothing here is ever closed by
removing a mark alone: an unmarked test that nobody made pass is a promise quietly withdrawn.

## Write the run files

One directory per feature under `.agent-kit/runs/`, plus one for the batch, all shaped like
`${CLAUDE_PLUGIN_ROOT}/templates/run.json`.

The batch — `.agent-kit/runs/<date>-<theme>/run.json`:

```json
{ "slug": "2026-08-05-offers", "command": "sprint", "gate": "owner", "base": "main",
  "window": "cc-sprint-offers",
  "children": ["2026-08-05-offers-01-create", "2026-08-05-offers-02-accept"] }
```

`children` is the order of the run. There is no queue file: this is the queue.

`window` is **your own session** — the driver types its news there, which is what reaches the owner
as a notification. Take it from `tmux display-message -p '#{session_name}'` and leave the field out
if that fails, because a run with no narrator is fine and a wrong address is not.

Each feature — `.agent-kit/runs/<batch>-NN-<feature>/run.json`:

- `command: "ship"`, plus `entries` or a `task`. Fill `approach` and `tasks` **only if the owner
  settled them** — left empty, `ship` designs the feature properly.
- `gate: "owner"` when the owner said they are reachable, `"none"` when they did not. That one field
  decides whether a child waits on an expensive fork or records it as an assumption.
- `branch: "claude/<feature-slug>"`.
- `base` and `parent` — **the previous feature in the list**, always: its branch and its run slug,
  whether or not this feature depends on it. The first child takes the batch's `base` and
  `parent: null`.
- `deliver: "branch"` — a feature inside a batch pushes and stops; the batch gets one pull request.
- `step: "queued"`.

**Every child chains to the previous one.** That is what makes integration a property instead of a
step: the last branch already holds the batch, and each child's suite runs on everything before it.
Its cost is that a feature cannot be dropped out of the middle afterwards — it is amended or
reverted by a commit.

Add `.agent-kit/runs/` to `.gitignore` if it is not there.

## Start the driver

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" .agent-kit/runs/<batch>/ >/dev/null 2>&1 &
```

It builds the children in order, each as its own visible session. It survives the account limit by
sleeping until the reset named in the record and typing one line into the session, which is still
alive with its context — so a limit costs the wait and nothing more.

## Then stay, as the window

You are the only session the owner has for this batch, and you already know why it looks the way it
does — a session raised later would have to read that back out of files. So say in one line that the
run has started and that they can ask you how it is going, and then **stop and wait**.

From here on you follow `${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/window.md`: you answer when
asked, you say the driver's news when it types a `[driver]` line at you, and you relay *pause*,
*skip* and *stop*. You do not narrate on your own, you do not poll anything, and you never take work
back on yourself — the run does not depend on you, and if the owner closes you it carries on without
a narrator.

Close per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md` before you go quiet.

## `--resume`

Start the driver again over the same directory. Children that already reached a pull request or a
blocker are left alone and the rest run in order. Rewrite nothing: a run file is the memory of its
own run, and the only reason to touch one is that the owner changed their mind about that feature.

## What this command does not do

It does not design features, write code, run tests, merge anything, or watch the run once the driver
has it. It never opens a pull request itself — the closing session does that, once, for the batch.
And it does not run `/agent-kit:audit` over its own output: a batch of a few features is small
enough for the owner to read, and the sweep would cost more than the batch. That belongs to `mvp`.
