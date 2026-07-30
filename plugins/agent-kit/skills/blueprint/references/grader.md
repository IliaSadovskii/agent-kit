# The entry grader — rubric and fact vocabulary

Read by `blueprint --index`, step 2. One call per document, carrying the sections of that document
whose hash moved. The call reads prose and returns data: it extracts the structural facts, judges
the entry against the bar below, and records what the entry does not answer. There is no second
pass, so everything the index needs comes out of this one call.

The grader **never edits anything** — not the documents, not the contract, not the index. It reads
what it is given and returns JSON.

## The bar

> **Can an implementer act on this without asking?**

Actionability, not completeness. The two are different and the kit needs the second one. A section
that says who does what, when, and what changes as a result passes even if it never mentions a
field name. A section that reads well and leaves the implementer guessing which entity moves to
which status does not, however thorough it looks.

Judge the prose the owner wrote, in the language they wrote it in. Slot ids, fact keys and this
rubric stay English; the answer they describe does not have to be.

Three things are **not** the grader's business:

- **Whether the product decision is good.** "Only verified customers may accept" is a decision, not
  a gap.
- **Whether the prose is well written.** Style is the owner's.
- **Whether other documents agree.** Cross-document disagreement is what the mechanical
  cross-checks find, from the keys, after every entry is parsed. Extract what *this* section says,
  even when you suspect another section contradicts it — a grader that quietly reconciles two
  documents destroys the evidence the cross-check needs.

## What to return

A flat list, one object per entry the group asked about:

```json
[
  {
    "collection": "actions",
    "key": "developer.create_offer",
    "rev": "a3f1c9d4e2b1",
    "facts": {
      "actor": "developer",
      "trigger": "a buyer request the developer has a matching lot for",
      "entities_written": ["offer"],
      "statuses_set": ["offer.pending"],
      "reads": ["lot", "request"],
      "screens": ["S12"]
    },
    "gaps": ["nothing says what happens when the request is withdrawn first"]
  }
]
```

`collection`, `key` and `rev` come back exactly as the plan gave them — `rev` is bookkeeping the
caller needs, not a judgement, and inventing one would record facts against text nobody read. An
entry you cannot parse still gets an object: empty `facts`, and a `gaps` entry saying what is
missing.

## The facts, per collection

Only these keys are read by the cross-checks. Extra keys are kept in the index and ignored, so
volunteering something is harmless — but a fact the checks need under a name of your own invention
is a fact nothing will ever compare.

| Collection | Key | Shape | Meaning |
|---|---|---|---|
| `actors` | `kind` | string | `role`, `operator`, `system`, `schedule`, or `product` |
| | `actions` | list of keys | the action keys this actor may perform |
| `entities` | `states` | list | every status in this entity's lifecycle |
| | `created_by` | list of action keys | what brings it into existence |
| | `closed_by` | list of action keys | what ends it — completion, cancellation, expiry |
| | `relations` | list | the other entities it is tied to |
| `actions` | `actor` | one actor key | who initiates it. Every action has one, even if it is the product itself |
| | `trigger` | string | what has to happen first |
| | `entities_written` | list of entity keys | what this action changes |
| | `statuses_set` | list of `entity.state` | the qualified form, always: `offer.pending`, never `pending` |
| | `reads` | list of entity keys | what it needs but does not change |
| | `screens` | list of screen ids | `S12` — the ids on the project's screen map |
| `screens` | `screen` | screen id | the id on the map this entry describes |
| `integrations` | `direction` | string | `inbound`, `outbound`, or `both` |
| | `absent` | string | what the product does when it is not there |

**Keys are the whole mechanism.** An action key is `<actor>.<action>` — `developer.create_offer` —
and everything else is a bare slug: `offer`, `broker`, `stripe`. Use the key the plan gave you for
the entry itself, and for a reference use the key that entry would have. `Оффер` and `offer` are two
instances as far as the checks are concerned, so pick the form the contract already uses and keep
it.

## Gaps

One line per thing an implementer would have to ask about, in the owner's language. Name the
missing decision, not the missing paragraph:

- good — *"the offer expires, but nothing says who or what expires it"*
- good — *"a second offer on the same lot: nothing says whether it replaces the first"*
- bad — *"the section is short"*
- bad — *"could mention the API contract"* (that is the implementer's job, not the owner's)

An entry that answers everything gets `"gaps": []`. Say that plainly rather than inventing a nit;
`gaps` is reported to the owner as work, and a list that always has something in it teaches them to
stop reading it.
