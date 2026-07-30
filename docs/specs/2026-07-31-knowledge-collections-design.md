# Collections, anchors, the derived index, and cross-checks

Expanded from the owner-approved brief at
`.agent-kit/sprint/2026-07-31-knowledge-and-gates/03-knowledge-collections/spec.md`, stage 2 of
`docs/design/knowledge-and-gates.md`. Depth: deep — the brief settled both the shape and the
mechanics. Run under `--brief`, so this expansion settles what the brief left open and re-decides
nothing it closed.

## What ships

Stage 1 made a project's *slots* checkable. This makes its *instances* checkable, and that is where
the contract starts finding problems nobody would find by reading:

```text
docs/**.md ──anchor or heading──► section ──grader──► index.yml (facts + rev + gaps)
                                                            │
                                                    cross-checks on keys
                                                            │
   ⚠ broker.accept_offer sets deal.created — no `created` state in entities/deal
```

Six pieces: the entry map in `contract.yml`, the anchor convention and the resolver that reads it,
the derived `index.yml`, `blueprint --index` (the one mode that spends grader calls), the
cross-checks, and the anchor-placement flow that is the only moment the kit writes into the owner's
prose.

## The entry map

A collection keeps its stage-1 `sources` globs — they say which documents to look in — and gains
`entries`, one line per instance:

```yaml
collections:
  actions:
    status: filled
    sources:
      - docs/user-stories/*.md
      - docs/OFFERS.md
    criterion: >-
      each one says who, what triggers it, what happens step by step, which entities change and to
      which status, and what can go wrong
    entries:
      developer.create_offer:
        at: docs/user-stories/DEVELOPER_SELLER.md#kit:developer.create_offer
      agency.create_offer:
        at: docs/OFFERS.md#Оффер от агентства
```

`at:` is the stage-1 `path#…` grammar with one addition: **a fragment beginning `kit:` names an
anchor**, anything else is a heading's literal text. One field, one grammar, and the two binding
kinds sit side by side in the file so an owner can see which entries drift when a heading is
renamed. The cost of the shortcut is a heading whose literal text begins `kit:`: that
binding is read as an anchor, and the check reports a missing anchor rather than a missing heading.
A documented limit with a loud symptom, not a silent misread — and rare enough that paying for it
with a second field on every entry would be the worse trade.

Entries are **proposed by a grader and recorded here** — the brief settled that. A mechanical
heading-level rule does not survive real documents, where entries sit at different depths or inside
lists, and recording the result is what makes the list reviewable and hand-fixable.

## Anchors

```markdown
### Создание оффера застройщиком
<!-- kit: developer.create_offer -->
```

On its own line, invisible when rendered, and it survives a heading rename — which is the whole
reason it exists. The bound section is the section the anchor sits in: the nearest heading at or
above the anchor line, and the body runs to the next heading of that level or shallower. That is
stage 1's `section_body` with a different way of finding the heading, not a second resolver.

An anchor before any heading binds to the document's preamble, from the top of the file to the first
heading. Duplicate anchors for one key are a structural failure, exactly as an ambiguous heading is:
a binding that resolves to two places resolves to neither.

## The derived index

```yaml
# .agent-kit/knowledge/index.yml — derived by `/agent-kit:blueprint --index`
version: 1

actions:
  developer.create_offer:
    at: docs/user-stories/DEVELOPER_SELLER.md#kit:developer.create_offer
    line: 47
    rev: a3f1c9d4e2b1
    facts:
      actor: developer
      trigger: opened a buyer request
      entities_written:
        - offer
      statuses_set:
        - offer.pending
      reads:
        - lot
        - request
      screens:
        - S12
    gaps: []

entities:
  offer:
    at: docs/ENTITIES.md#kit:offer
    line: 12
    rev: 77c0be31aa04
    facts:
      states:
        - pending
        - accepted
      created_by:
        - developer.create_offer
      closed_by:
        - broker.accept_offer
    gaps:
      - no transition is named out of `accepted`
```

`rev` is the hash of the same section text stage 1 hashes, so one function answers "is this stale"
for a slot and for an entry. The parse cache is this file and nothing else: an entry whose `rev`
matches the document is not re-parsed, and there is no second cache to fall out of step with it.

`index.yml` is committed. It is derived, but derived by dozens of grader calls, and a clone, a CI
run and every headless sprint child should inherit the cache rather than pay for it again.

### The fact vocabulary

Cross-checks are key comparisons, so the keys have to be fixed. The grader fills exactly these, and
the rubric ships beside the skill at `skills/blueprint/references/grader.md`:

| Collection | Facts |
|---|---|
| `actors` | `kind`, `actions` — the action keys this actor may perform |
| `entities` | `states`, `created_by`, `closed_by`, `relations` |
| `actions` | `actor`, `trigger`, `entities_written`, `statuses_set` (`entity.state`), `reads`, `screens` |
| `screens` | `screen` — the id on the map this entry describes |
| `integrations` | `direction`, `absent` — what happens when it is not there |

Unknown fact keys are kept in the index and ignored by the checks. A grader that volunteers
something extra should not fail the parse; a check that silently depends on a key nobody declared
should not exist.

`gaps` is where the same call records what the entry does not answer, judged against the design's
own bar — *"can an implementer act on this without asking?"*. Actionability, not completeness.

## `blueprint --index`

The one mode that spends money. It is two script invocations with the grader between them, because
the script is stdlib Python and cannot call a model, and pretending otherwise would put the cache
proof out of reach of the tests:

```bash
python3 blueprint_index.py --plan            # → JSON: the calls that need making
#                                              (the agent runs one grader per group)
python3 blueprint_index.py --apply results.json
```

`--plan` resolves every entry, compares its section hash against the index, and groups what is stale
**by document**: one call per document, carrying only the sections that need a parse. First parse of
a document is one call; editing one section later is one call carrying that one section. The cache
stays per-section, so a rewritten paragraph never re-parses fifty entries. One code path, both
properties.

`--apply` merges the results and drops index entries the contract no longer lists. Each entry
records the `rev` the plan handed the grader — the hash of the text that was actually read, not the
file's hash at apply time. A document edited while the grader was running therefore comes back stale
on the next check, instead of being recorded as parsed at a hash whose text nobody has seen.

The module also exposes `refresh(root, grader)` — plan, call, apply — which is how the tests count
grader calls with a fake grader, and how the cache behaviour is proven mechanically rather than
argued.

## The cross-checks

Mechanical, over the index's keys plus `screens.data.js`. Reported as findings, exit 1.

| Check | Fires when |
|---|---|
| set completeness | an entry references an instance no entry describes |
| statuses | an action sets `entity.state` and that state is not in the entity's `states` |
| rights | an action names an actor who does not list it, or an actor lists an action that has no entry |
| screens | an action references a screen id absent from the map, or a live screen on the map is reached by no action |
| lifecycle | an entity that some action writes has no creating action or no closing action |

Set completeness runs first and the others skip a key it already reported: a document that never
described `deal` should produce one finding, not four. The screen map stays the authority for
screens — actions reference ids and the check validates the reference, with no duplication. A
`rejected` screen on the map is not expected to be reachable.

## `--check`, unchanged in cost

`--check` still never calls a grader. It resolves every entry's binding, compares hashes, reads the
index it finds and runs the cross-checks over it — all string and dict work, in the seconds stage 6
needs it to stay inside:

```text
slots        5 filled · 1 open_question
collections  1 filled · 4 not_applicable
actions      23 entries · 2 findings
entities      7 entries · 1 finding

⚠ actions/broker.accept_offer
  sets deal.created — no `created` state in entities/deal
  (states are: draft, active, closed, cancelled)

stale        docs/OFFERS.md changed since last parse (3 entries)
```

Exit codes are stage 1's. Cross-check findings, `gaps`, and an entry whose binding no longer
resolves are `1`; the contract being unreadable, a source document being gone, or a duplicate anchor
are `2`.

**An entry whose binding does not resolve is a finding, not a structural failure**, and this is the
one place the expansion departs from stage 1's instinct. A slot is the project's answer to a
question and an unresolved one leaves the check with nothing to say; an entry is one instance among
twenty-three, and the other twenty-two are still checkable. Anchor drift and heading drift are
reported under separate headings, because the fix differs: a removed anchor is re-proposed, a
renamed heading is repointed.

A removed anchor is never silently re-added. `--check` reports it, `--index` refuses to parse the
entry, and putting it back goes through the placement flow with its own yes.

## The placement flow

The only moment the kit writes into the owner's documents, and it asks:

1. the grader proposes boundaries — "found 23 actions, here is where the anchors go";
2. the agent shows the list, one line per anchor, and waits for an explicit yes;
3. `blueprint_index.py --anchors proposal.json` writes them, each on its own line directly under
   the heading it belongs to, and records the matching `entries:` block in `contract.yml`;
4. one commit.

The script does the writing rather than the agent, so "on its own line" is a property of the code
and not of the agent's care. It refuses a proposal that would place a second anchor for a key that
already has one, or that would write outside the project.

Writing `entries:` into `contract.yml` is a **surgical text edit**: the block under one collection
is replaced and every other byte of the file — including the owner's comments, which no dumper
preserves — is left alone. Statuses, reasons and criteria are never touched; those are the owner's
verdicts and stage 1 promised the kit would not write them.

## What this repository does with it

Nothing, deliberately. agent-kit is a plugin without a product domain model, so its own collections
stay `not_applicable` and it grows no `index.yml`. The machinery is proven against fixtures here and
measured against `/projects/realest`, which is read-only: two documents parsed through the
`file#heading` path, the real cost recorded, and the extrapolation to the whole corpus labelled as
an extrapolation.

## Verification

- **Property-based**, because this is all parsing and invariants: a section resolved by anchor and
  the same section resolved by heading are the same section until the heading is renamed, and an
  entry's `rev` changes exactly when its section's text does.
- **Fixture-driven** executable checks, one fixture that violates each cross-check and one that does
  not, wired into `scripts/validate.sh`.
- **A grader-call counter** the tests assert on: zero calls on an unchanged second run, one call
  carrying one section after one section is edited.
- No runnable app surface — this is a script and a skill, and the suite is what proves it.
