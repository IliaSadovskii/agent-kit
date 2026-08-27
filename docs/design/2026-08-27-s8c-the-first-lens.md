# S8c — the audit, and the first lens

Written after building it, 27 August 2026, like the notes for S8a and S8b. The step was cut
small on purpose: the machinery of the audit plus **one lens end to end**, which is what the
plan's own *done when* asks for. The other five lenses are named and nothing more. The two steps
before it took seven hours each; a smaller piece makes the build-review-fix loop shorter, and
that was the owner's instruction rather than a discovery.

The plan's words:

> **S8c · The audit: lenses whose output is work.** Six lenses over the code against the
> description — tests, dependencies, scenarios, security, performance, conventions — each
> writing its own report and changing nothing. It is read-only by construction: the moment an
> audit starts fixing what it finds it loses its stopping condition.
>
> *Done when* one lens over a project produces a report and a candidate list a sitting can
> compose from, and a bench trap proves a lens that found nothing says so rather than inventing
> a finding.

## 1 · The shape: a third caller, and no state of its own

The audit is not a run and not a sitting. It is the third thing that calls
`driver/session.py` — the attempt chain, the slot, the growing pause, the fallback provider, the
refusal enclosed in the next input — and it keeps no record of its own. The reason is S8a's,
word for word: it does not resume, it cannot be stopped from elsewhere, and it has no graph.
State with no reader is not written.

Nothing below the audit learns the word *audit*. One new noun in the whole step: the **lens**.

## 2 · Which lens, and why that one

`dependencies`, chosen on one criterion: **its findings are checkable by a program**.

- *Declared and imported nowhere* is arithmetic — parse the manifests, scan the tree for import
  tokens. Neither half needs a second model.
- The finding is already the work: *remove `requests` from `[project].dependencies`* is a
  candidate line, not a topic.
- The other five are weaker. `tests` needs a coverage instrument per ecosystem, and the kit
  names no tools. `security` and `performance` are not checkable at all — they are prose with a
  green tick. `scenarios` and `conventions` measure code against the description, and a
  violation there is a judgement nothing can recount.

Two narrowings, said out loud rather than discovered later:

**`derived` still has no writer.** S8a's note named the audit as the writer of the mark that
separates *what the owner told* from *what an agent worked out*. The dependencies lens writes no
part of the product, so it pays none of that. The lens that infers the description from the code
pays it, and it is not built.

**One ecosystem.** Only `pyproject.toml`. A project with no manifest the kit can read gets a
named refusal — `nothing-to-measure` — not a quiet zero, which is the defect findings 9, 10 and
25 are about.

## 3 · The program measures, the session sorts, the program recounts

This is the whole of the step's honesty. Before any session, the program writes
`inventory.json`: the commit, every declared dependency with its group and where it was
declared, every top-level import with a count and a first sighting, and `skipped` — what was
filtered out and why. `skipped` is printed as a denominator, because a silent filter is the same
silence the whole layer is written against.

The session finds nothing. It returns one row per measured entry, and the program recounts every
verdict against the inventory it already holds. Five refusal codes, and they are one judge seen
from five sides: `not-declared`, `named-twice`, `not-accounted-for`,
`verdict-against-the-inventory`, `no-reason-to-remove`. The proposal had nine; four of them were
the same error in a second field, and the kit's idiom for that is a place in the detail
(`bad-field: status`), not another code.

`no-reason-to-remove` is enforced by the judge and not by the contract, and the reason is
mechanical: `required_when` reads a sibling for truthiness, and `verdict` is never empty, so
"required when the verdict is `unused`" cannot be expressed there. Declaring it `required=True`
would have made the code unreachable — the defect S8b spent a round on.

## 4 · Read-only as a removed possibility, and the hole a trap found

Three levels, all three subtraction rather than a rule in prose: the session stands in an
unpacked `git archive HEAD`; the files are written by the program; the inventory is a white
list, so a row can only name what was measured.

**And the first version of that was wrong.** The unpack sat under `.agent-kit/v3/audits/`, and
git searches for a repository *upward*: two directories up it found the project's `.git`, and
commit, branch and push all came back. The trap `an-audit-that-changes-nothing` caught it — it
asks the session what git says where it stands. Reading the diff did not catch it, and neither
did the argument that a directory with no `.git` cannot be a repository.

The unpack is now outside the project, and that it really is outside is *asked* rather than
assumed: `tree-inside-a-repository`, raised before anything is unpacked, so a refusal writes
nothing rather than writing and cleaning up.

The judge was strengthened for the same reason. An empty `git status --porcelain` cannot tell
*the possibility was removed* from *the possibility was moved* — it is equally empty after a
worktree whose directory was deleted. It now counts refs and commits before and after.

## 5 · The finding that can be hidden, and the one that cannot

Inventing a finding is structurally impossible: a row can only name a measured entry. **Hiding
one was possible until the review**, and that is the direction that matters, because the lens
exists to find work rather than to avoid it.

The hole: everything the session named in a package's `imports` was trusted, so a real
undeclared import could be hung on somebody else's package — `{"name": "PyYAML", "verdict":
"imported", "imports": ["yaml", "requests"]}` — and `requests` vanished. Findings: zero. Report:
nothing to do.

Three rules closed it, and no new code was added: a measured module belongs to one package
(`named-twice`); an `imported` row may name only measured modules (`not-declared`); and a module
bound to a package whose name it does not share stands on the session's word, so it owes a
reason and is printed as an open counter. The old refusal *"imported, yet nothing is imported"*
became unreachable under those rules and was **deleted** rather than left as a branch no test
can distinguish — the defect S8b paid for.

One instruction of mine was wrong and the builder said so instead of building it: *refuse any
name in `imports` that is not in the inventory* refuses the truth, because an unused package's
module is by definition not imported anywhere. It holds only for `imported` rows, which is where
the hole was.

**Two things remain uncheckable, and the manifest now says both.** *Needed but never imported* —
a pytest plugin, a linter, a build backend. And the binding of a module to a package whose name
differs: `PyYAML` really does arrive as `yaml`, and a stranger's import hung on a stranger's
package looks exactly the same. The first lets a lens invent empty work; the second lets it hide
real work, which is worse. Both owe a reason and both stand in the open half of the report as
counters beside the findings.

## 6 · Where the candidate list goes

A file the owner passes to `batch compose --from`, and not a line of code on S8b's side.

`batch compose` reads a *telling* — numbered text in which every feature must point at a line.
So the candidate list is written as a telling: a header with the date, the commit and the
counts, then one line per candidate. `said: L4` then traces a feature back to a *measured*
finding rather than to somebody's memory. That the file really is a valid telling is proved by a
test that feeds it to `Telling` and resolves a range through `said`.

Its first line says the text is the kit's measurement and not the owner's words. In S8a `said`
means *a line the owner spoke*, and the substitution has to be visible to whoever reads it.

Rejected: a `candidates.toml` and a `--candidates` flag on `compose` — a second door into the
sitting and a field whose reader lives in somebody else's step.

## 7 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1019 | **1073** |
| `make bench` | 93 of 93 | **103 of 103** |
| `make armed` | 89 + 4 in words | **98 + 5 in words** |

Run by me after the work landed, and the bench also from `git archive HEAD` unpacked elsewhere.
Every one of the eighteen commits imports and answers `--help`.

**One measurement of mine was void and is recorded rather than quietly re-taken.** I ran the
suite while the builder still owned the tree; one bench test failed with *the fake provider was
asked once more than it was scripted*, because the replies under it were being edited as it ran.
The rule that the tree is not touched during a break round cuts both ways, and I broke it. The
numbers above are from a stable tree.

## 8 · Breaking it by hand

Twelve breaks, one at a time, each reverted before the next; exactly one case reddened for each:

| broken | what said so |
|---|---|
| a row may contradict the inventory | `a-finding-nobody-measured` |
| the candidate list is written even with no findings | `a-lens-that-found-nothing` |
| the commit is unpacked inside the project | `an-audit-that-changes-nothing` |
| the candidate list is never written | `a-candidate-list-a-sitting-can-compose-from` |
| no manifest means measure nothing rather than refuse | `a-project-with-nothing-to-measure` |
| completeness of the reading is not required | `a-lens-that-leaves-one-dependency-unanswered` |
| a verdict other than `imported` needs no reason | `a-plugin-nobody-explained` |
| a binding under another name needs no reason | `a-module-hidden-under-a-package` |
| one module may be claimed by two packages | `a-module-claimed-by-two-packages` |
| an `imported` row may name the unmeasured | `a-module-nobody-measured-on-an-imported-row` |
| the binding counter is not printed | `a-candidate-list-a-sitting-can-compose-from` |
| the *used without importing* counter is not printed | `a-candidate-list-a-sitting-can-compose-from` |

Two judges had to be narrowed on the way. One proved its finding through `candidates.md`, so it
reddened when a neighbour's mechanism broke; it reads the report now. Another measured a refusal
both halves of the contract could raise, so it could not say which one it was about.

## 9 · What is held by words, not by a trap

- **`a-lens-that-found-nothing` carries `no_disarm` in words.** The world in which the lens finds
  nothing *is* that case's baseline, and the reply the disarm substitutes is the same reply.
  There is nothing to take away, and the words are printed on every `make armed` rather than
  agreed once in a note. This is the half of the plan's *done when* that could not honestly be a
  mechanical trap, and it is said here rather than swapped for a test in silence.
- **The binding stands on the session's word.** Having written a reason, a session can still hang
  a stranger's module on a stranger's package. It is moved from silent to declared, not from
  possible to impossible.
- **Nothing was driven by a live model.** Everything answers from `providers/fake/`. The same
  honest half as S6's `0 of 197`, S8a's fifteen parts and S8b's graph.
- **One judge greps the report's Russian heading** (`## Объявить`). The rule about codes rather
  than phrases is written for refusals, and this is the kit's own report prose — but rewriting
  one word there would redden the bench for no reason, and it is worth knowing.
- **Commit order, one pair.** `SHIPPED = 93 → 100` landed in a `tests:` commit *after* the
  `bench:` commit that added the cases, so the red commit in that pair was the code one rather
  than the test one. A counter is an assertion, so one of the two is red whichever way round they
  go; the rule wants the test to be the red one. It stands, recorded here rather than rewritten
  at midnight.

## 10 · Where the plan was wrong

1. **"Read-only by construction" does not follow from "no `.git` in the directory."** Git looks
   upward. Taken as written, that sentence would have shipped as a false claim in code; a trap
   caught it, not an argument.
2. **"Read-only" and "leaves a commit on the branch its record names" are in one step and
   contradict each other.** The narrowing: the audit changes no *code*; the only thing it could
   ever commit is its own report, and today it commits nothing.
3. **"Six lenses over the code against the description" is not true of this one.** Dependencies
   are measured against the manifest; enclosing the knowledge index here would be an enclosure
   with no reader.
4. **"The same preflight every other command runs" describes a preflight that does not exist.**
   The run has two checks, each tied to its own reader — `no-such-command` only where the method
   has `verify`, `no-description` only where it has `design`. Copying them into the audit would
   be adding checks with no reader. What finding 34 actually asks for is *refuse before spending
   a session and say what is missing*, and that is `nothing-to-measure`, `no-commit`,
   `tree-inside-a-repository`.
5. **"Its output is the candidate list S8b composes from" implies a data handover.** S8b's input
   is a telling, so the honest seam is text a person reads and edits — and then the seam needs no
   code at all.

## 11 · What was deliberately not built

The other five lenses; the audit as a child of a batch (a second kind of child in `batch.json`,
the batch driver learning the word *audit*, and a commit that would undo the removed possibility
of §4 — while the loop the step exists for, audit → candidates → sitting → batch, works without
it); `audit.json`; automatic handover of the candidates; a second ecosystem, lock files, version
comparison, vulnerabilities; writing `derived`; a non-zero exit code when findings exist — the
audit is not a gate, its output is work rather than a verdict; `audit list` and `audit show`.
