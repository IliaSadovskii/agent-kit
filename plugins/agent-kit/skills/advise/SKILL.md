---
name: advise
description: Look the project over and say where it is weak and where it could grow — in the product itself (what users cannot finish, what nobody needs, who is nearly served and is not), in the code (what stops working as it grows, what would be simpler or faster to change), and in the money (what is given away that costs per use, what people would pay for). Proposes; the owner decides at the end; whatever they accept is written down while they are still there.
argument-hint: "[product|code|money] [area] — or what you are wondering about"
disable-model-invocation: true
---

# Advise

**Look the project over and say where it is weak and where it could grow.** Not whether the code
matches the description — that is `audit`. This is the description itself, and the approach under it,
put in question.

Every other command in the kit takes the knowledge as true: `blueprint` writes down what the owner
means, `audit` measures code against it, the build commands make it real. So a mediocre idea gets
built carefully and audited as correct. This command is the one that doubts it.

It proposes. The owner decides, in one round at the end, and what they accept is written down while
they are still there.

**It changes no code and no tests, and it decides nothing about the product.** What it writes is its
own list, plus — for the rows the owner accepted in front of it — what they answered.

## Invocation

| You type | What happens |
|---|---|
| `advise` | every lens, `product` first, each writing its file as it finishes |
| `advise product` | one lens. Names are recognised in either language |
| `advise product checkout` | one lens, narrowed to an area |
| `advise "why does signup feel so long"` | free text: map it to a lens, **say in one line what you understood**, then start |

Three lenses exist — **`product`, `code`, `money`** — one reference file each under
`${CLAUDE_PLUGIN_ROOT}/skills/advise/references/`. **Read the one you are running and no others.**
Nothing here names a lens that does not exist.

If the first word is neither a lens nor clearly about one, **stop before doing anything**: print the
three and ask the one clarification worth making — whether they meant an area, which goes second.

Lens files are named in English whatever language the lens was typed in.

## Preflight

Run the check once, for the four lists below and for what the knowledge is missing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
```

**Its findings are not a reason to stop here**, and this is the one command in the kit where that is
true — `rules/preflight.md` is written for the build commands, which must not build over an unsettled
slot. Thin knowledge is this command's subject matter. An `open_question` slot, an entry with empty
fields, a `product.md` that says nothing about money: name each one in the report, run the halves
that do not need it, and never fill it by invention.

What each lens needs: `product` reads `scenarios.md` and `actions.md` for its close half,
`product.md` and `actors.md` for its wide half; `code` reads `stack.md`; `money` usually finds that
nobody wrote down how the product earns, which is its own first finding.

With nothing written at all, this command has nothing to be about: say so and name `blueprint`.

The tree must be clean before the closing round, because that round commits into `docs/knowledge/`.
Check it there rather than here — a run that refused to read a project over uncommitted work would
be refusing to do the only part that costs nothing.

**Note which branch you are on while you are looking anyway**, and say it in the report if it is not
the default one. The round branches off the default whatever is checked out, so this changes nothing
about the writing — it is worth a line because a spent feature branch left behind by the last sprint
is a fact the owner usually wants to hear about.

## Each lens has two halves, and every row says which it came from

**The close half** walks the files and finds what they omit or contradict. **The wide half** steps
away from the files and proposes what is not in them at all — the reading of the domain, the
adjacent audience, the approach nobody reconsidered.

Both are wanted. Mixing them silently ruins both, because a list where half the rows carry evidence
and half carry judgement gets read at the weaker standard throughout. So **every row carries its
origin, one word**:

| Tag | What it rests on |
|---|---|
| `from the files` | something read in this repository, cited |
| `from the domain` | judgement about this kind of product, resting on the reading of the domain the report states |
| `from research` | something found outside, carrying a link and a date |

Completeness differs by half, and the report says so:

- **The close half's walk is complete.** Every item on its list gets a row — a proposal, `clean`, or
  `unjudged` with the reason. Never truncated: a walk that caps itself is lying about coverage.
- **The wide half raises what passed a bar**, so it ends with a **considered and rejected** section.
  Without it, five proposals cannot be told apart from a walk that stopped after five.

## Three orderings that are load-bearing

How you work is yours. Three sequences are not, because each one is wrong in only one direction:

- **The previous `docs/advice/<lens>.md` is read before anything is proposed.** Declined rows are
  not raised again; rows left open are carried forward as open rather than presented as new.
- **The reading of the domain is written down before the research pass is briefed.** Search first
  and the reading becomes a summary of the first page of results; write it first and the search can
  be checked against it — and a disagreement is itself a finding.
- **Everything passes the five lists below before it reaches the report**, and the report is written
  before the closing round.

## Nothing is raised that was already decided

Five lists, and three of them the check already prints, so the filter costs nothing:

- **`planned` entries** — described and not yet built. Proposing one is proposing what already
  exists on paper.
- **open boxes in `docs/audits/*`** — already found and already sized into `ship` runs.
- **`docs/technical_debt.md`** — already decided on by a run.
- **the previous `docs/advice/<lens>.md`** — already refused, or already open.

A proposal that restates one of these is not raised as a proposal. It may be raised once as a
**priority remark** — *this is already planned, and it is the thing standing between you and the
adjacent audience* — which is a different claim and is marked as one.

The fifth is the sharpest: **"what it deliberately does not do", in `product.md`.** Read it before
the wide half, always. A lens that cheerfully proposes what the owner already ruled out wastes the
round and makes the exclusion look unread. **A proposal that reopens an exclusion must quote the
recorded reason and say what changed** — a number, a market, a capability that did not exist when
the line was written. No answer to *what changed* and the exclusion stands. With one, it is the most
valuable row in the report, because a deliberate decision is the one thing an owner never revisits
unprompted.

## The report

`docs/advice/<lens>.md`, one file per lens, rewritten by each run of that lens. Git holds the
history. Written in the project's language.

```markdown
# Продукт — 2026-08-09

Прочтение области: 6 строк. Обойдено: 9 сценариев, 34 действия. 5 предложений, 2 отложены с прошлого
раза, 3 отклонены раньше и не поднимаются.

## Мелкие правки с непропорциональным эффектом
- **Импорт каталога одним файлом** · из области
  кому — продавцы с готовым каталогом (их 40 из 60)
  сегодня — перегоняют позиции в телеграм руками, по вечерам
  меняется — вечер работы превращается в одну загрузку
  трогает — actions: seller.import_catalogue (нет) · entities: offer (есть)

## Сценарии и действия
...

## Рассмотрел и отклонил
- Реферальная программа — не смог назвать, что эти люди делают вместо, и чем она лучше
  прямого приглашения, которое уже есть

## Отклонено раньше
- [2026-07-02] Публичный рейтинг продавцов — владелец: «превращает площадку в рынок отзывов»

## Чего я не вижу
Про эту область знаю: ... . Три вопроса, ответы на которые изменят список: ...
```

**Sort by what matters and never truncate.** Sorting is what lets the owner read the top and stop.

**State the blind spot every time**, and in the wide half that is two specific lines: what you know
about this domain and where from, and three questions whose answers would change the list. Model
knowledge of a marketplace is good and of niche B2B is nearly absent, and there it invents fluently.

**If there was no network, or the search found nothing, say so** and mark those rows unresearched.
Silence must mean *nothing was found* and nothing else.

## The closing round

Put the rows to the owner per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md` — options, the recommendation
first, everything independent in one batch. Three answers, each with one home.

### Accepted, and it changes what the product is or what the code is held to

**Write it now, complete, in this round.** Not a marker for a later session: the owner is here, they
have just decided, and this is the cheapest moment the fields will ever be answerable.

Follow `${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md` — read the slot's template and write from
it, `state: planned`, the project's language, one commit per slot, the check afterwards.

The interview is short because the proposal already did most of it: the row names the actor, which
entities exist and which are missing, what changes and what happens without it. Confirm what you
derived and ask only what cannot be derived.

**All or nothing, per item.** Every field is either the owner's own words from this round or
something you derived and put in front of them to correct. **A field with no answer means the item
does not become an entry — it becomes a block.** There is no mostly-written entry here: a day later
an invented field is indistinguishable from an answered one, and a run is confident around a record
that looks complete.

**Two questions that are not the entry's own fields, and both fail silently if skipped:**

- **Which scenario covers it** — an existing one gains a step in the owner's words, or a new
  scenario is written. `epic` stops on *every scenario inside the bounds passes*, so an entry in no
  scenario is built, marked `built`, and proved by nothing.
- **Inside the MVP bounds, or outside** — `epic` reads those bounds to know where to stop, and a new
  entry silently widens them or does not. Outside the bounds, the scenario question can wait.

A stance rather than a feature — *money in minor units*, *every outbound call idempotent* — is two
lines in `stack.md`, written the same way.

### Accepted, and it is work under rules that already hold

**A line in `docs/technical_debt.md`**, in that file's own format. Most of what `code` and `money`
produce is this: apply the stance in eleven places, enforce the limit the plan already states, cache
the metered call. No rule changes, so there is nothing to write into the knowledge — it is work
somebody has to do, and that ledger is read before every command and closed by whoever does it.

**The fork is one question: does this change a rule, or follow one?**

### Declined, or not now

**A line in `docs/advice/<lens>.md`, never a block** — the proposal, the reason, the date. Its one
reader is the next run of this lens, which must not raise it again.

*Not now* is not a decline: the row stays open in the file and the next run carries it forward rather
than presenting it as new. Refusing the same idea twice is what teaches an owner to stop running a
command.

**`code` and `money` decline until a condition, not for ever.** *No sharding needed, we have 400
rows* stops being true at 400 000. Those refusals record the number they rested on, and the next
run's first act is to check whether it moved.

### An accepted row leaves the file

The moment its entry, its block or its ledger line is written. From then the fact lives in the
knowledge or in the ledger, and two homes for one fact is what this kit keeps paying for.

### Where the writing lands: a branch of its own, and one pull request

**Branch from the default branch before the first commit — never onto whatever is checked out.**
After a sprint that is a spent feature branch whose pull request has already merged, and right after
a sprint is one of the two best moments to run this command. `docs/advise-<date>` off the default
branch, one commit per item as each is settled, so a round that dies costs one item.

**Then one pull request for the round**, per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, opened
after the round rather than during it. Not because anything in it is in doubt — the owner accepted
every line — but because they accepted proposals of one sentence and you wrote the record's fields
around them. That prose becomes what every later run builds from, and this is the only moment
anybody reads it as a diff.

It is a knowledge pull request, so most of that file's sections have nothing to say: no **Proven**,
no **Review**, no **What was hard**. What it carries instead:

- **What & why** — what the owner accepted, and what changed in the description because of it.
- **Manual actions** — normally "None.", and that file's bar still applies: nothing here is written
  as a task for the owner.
- **Assumptions** — every field you derived rather than took from them in the round. The one place a
  wrong reading can hide is then the first thing they read.
- **Changes** — slot by slot, as a table.

Say in the closing line that the pull request is open, and that the entries in it are invisible to
`ship` and `sprint` until it merges. That is the one cost of this shape, and it should not be a
surprise a week later.

`blueprint` commits differently — onto the branch that is checked out, with no pull request — and its
reason is in its own file. **Do not copy it here.** It rests on an interview that may span days and
on the owner having dictated every slot; neither is true of a round that took twenty minutes and
composed nine fields around a one-line yes.

### Nobody in the room: write the list and stop

No entry, no block, no ledger line, nothing accepted — and the closing line says the round is
outstanding. Acceptance is a decision about what the product must do, and only the owner makes one.
A run that wrote an entry on its own judgement would produce something indistinguishable from an
answered one, which is the one failure here that would never be noticed.

`[accepted …]` is written only when the owner said yes and left the fields for later, or tired
partway through a long round. It goes in the slot the proposal names, carries the proposal, why they
accepted it, the date and the row it came from — and `blueprint` finishes it.

## Closing

Per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is thin — which halves could not run for missing
knowledge, what the search could not reach, where the domain is outside what you know — then the one
line naming what to run next.

When the round wrote anything, that line is **merge the pull request** — nothing downstream can see
an entry until it lands, so naming `ship` on what was just written would name a command that cannot
find it yet. Otherwise it is the next lens, or `blueprint` if blocks were left.
