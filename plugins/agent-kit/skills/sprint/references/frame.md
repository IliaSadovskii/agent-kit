# The frame child

You are the first child of a batch and you are not a feature. Nobody is present. Three things come
out of you and nothing else:

1. **What the batch's features must build alike** — a `[frame …]` block under `docs/knowledge/stack.md`.
2. **Which feature cannot be built without which** — the `frame` field of your own run file.
3. **A feature that is two features, split in half** — see below. You are the only reader who sees
   the whole batch before a line of it is written, and the driver re-reads the list before every
   child, so this is the last and cheapest moment it can happen.

**You write no product code.** The features are not written yet, so anything you build for them in
advance is built against a guess: the third feature does not fit it, breaks it, and now two runs
have paid for it. What bends costs nothing to be wrong about; what is compiled does.

That is also why this is not a `ship`. There is no entry, no test, no diff to review.

## What you read

Your run file names the batch, and if it does not, the batch is the run directory beside yours whose
`children` names you. From its `children`, the features — and for each, its entry, pulled as a
section rather than by opening the file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --brief <entry key>
```

That call prints `stack.md` whole every time, so read the map from the first one and pass
`--brief` the remaining entries in the same message rather than one turn each.

Then the code where two features look like they meet: the same table, the same model, the same
screen, the same outbound call. **Only there.** Reading the codebase because it might be relevant
is how this step comes to cost what a feature costs, and it has no diff to show for it.

## A feature that is two

The composing session groups by topic and nothing stops it putting two deliverables in one child.
Measured on a live batch: `user.open_rule` and `scheduler.generate_session` went into one feature —
a person's action and a background job — and it took **four sessions** and seven tasks, spending
about 40% of its wall clock handing itself over, while three single-deliverable features next to it
took one session each.

**The test is the kind of thing, not the count.** Two entries in one child are usually right:

| in one child | what it is | verdict |
|---|---|---|
| an action and the screen it fills — `user.open_rules` + `screen.rules` | one thing a person does | leave it |
| an entity and the action that first writes it | one thing that starts existing | leave it |
| a person's action and a scheduler, a queue, a webhook | two places, two proofs | **split** |
| something stored and something displayed, in different parts of the product | two deliverables | **split** |

The signal is readable without judgement: the entries live in different files of the knowledge, or
their keys name different actors — a person against `scheduler.*`, `push_*`, an integration.

Read the numbers before you decide. `docs/runs/*.json` carries what past features of this project
cost, per feature, in `spent.sessions`; a shape that took three or more sessions before is the
shape to split now. With no history yet, split only on the table above.

**To split**, write a second run file beside the first, exactly as
`${CLAUDE_PLUGIN_ROOT}/skills/sprint/SKILL.md` writes one — the same `base`, `model`, `deliver`,
`gate`, `step: "queued"` — move the entries that belong to it, put its slug into the batch's
`children` directly after the original, and set its `needs` to the original. Say in your report
which feature you split and why, in one line.

**Split at most one per batch, and never a feature already begun.** A frame child that halves
everything turns five features into nine, and every split costs a session's whole reading set —
90k of context before a line is written. One is the case where the evidence is plain; two is a
rewrite of the batch, which is the composing session's job and not yours.

## The block

Under `stack.md`, at the end, one line per agreement:

```markdown
> **[frame 2026-08-12 · <batch slug> · pr: ?]** <what every feature here does the same way>, beside
> `<path/to/the/file.ext>` or `<the symbol it follows>`. Why: <the reason, in this codebase>.
> Without it: <what these features would each do instead>.
```

Four rules, and each of them is the difference between a rule that is followed and one that is read
past:

- **Every line cites a path or a symbol that exists today**, and you have opened it. Not the file
  the feature will create — the one it will sit beside, extend or copy. This is the rule that makes
  the rest true: the three below can all be written from the entries alone, without opening the
  repository once, and the result reads exactly like work. A citation cannot.
- **Checkable against a diff.** *"We use DDD"* cannot be obeyed or broken — nobody can say which
  side of it a file is on. *"Order logic lives in `app/Domain/Order`; the controller only calls
  it"* can. The reviewer already judges a diff against `stack.md`, so a checkable line brings its
  own enforcement and a slogan brings none.
- **The reason, in this codebase.** A rule with no reason is followed to the letter and missed in
  substance — this kit has paid for that three times. Say why here, not why in general.
- **Only what more than one feature touches.** You are not describing the batch. A line that
  applies to one feature belongs to that feature, and it will be there in an hour with more of the
  code read than you have.

`pr: ?` stays as it is. The batch's closing session fills in the number, which is what lets
`blueprint` tell later whether this batch ever merged — by then the run directory is long gone.

**Nothing to say is a result** — and it is the one that costs nothing to reach, so it is the one to
be honest about. Five features that share no ground get an empty block and a sentence saying which
files you opened to find that out. Without those, *nothing to say* and *nobody looked* are the same
sentence. An agreement invented to fill the section is the opposite mistake and just as expensive:
a rule every later run must hold and nobody needed.

Commit it on the branch in your own run file's `branch`, off your `base`, and push. The features
chain off that branch, so a block left uncommitted reaches nobody.

## The map

In your run file, `frame`: for every feature in the batch, which of the others it cannot be built
without.

```json
"frame": { "b-02-accept": ["b-01-create"], "b-03-notify": [] }
```

Read as: *accept needs create; notify needs nothing.* Name every feature — one you leave out is
read as needing nothing, which is the same answer with no one behind it.

**Doubt goes to the dependency.** Getting this wrong in one direction costs a feature that waits
for another it did not need; in the other it costs a feature built without the ground it stood on,
and that surfaces at the merge. They are not the same mistake.

The dependency is *cannot be built without* — the other feature's table, endpoint, permission or
type has to exist first. Two features that merely touch the same file are not dependent: they chain
anyway, because every feature branches off the last one built.

Do not reorder `children` yourself and do not write into another run's file. The driver reads this
map, writes each feature's `needs`, and re-sorts the queue by it.

## Then stop

Close your run file: `step: "done"`, the branch, and `notes` — **the files you opened**, by path,
and what you deliberately said nothing about. The list of paths is the whole of it: this step has
no diff and no reviewer, so what you read is the only thing anybody can check you by.

The driver is watching `step` and starts the first feature the moment it turns terminal.
