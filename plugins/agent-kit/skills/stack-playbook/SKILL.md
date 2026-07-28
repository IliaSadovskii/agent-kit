---
name: stack-playbook
description: Generate or refresh the stack playbook inside the project's registered coding standards — detect the stack and application type, record the owner's architecture stance for each area that has its own, research the framework's current idioms and ecosystem libraries, and write short justified rules the pipelines load before every feature. Invoked by idea-interview at bootstrap, or when the user asks to create or update stack standards or the playbook.
---

# Stack playbook

Make the agent know where it is. The playbook turns "a codebase" into "a Laravel 11 API with DDD
modules, tested with Pest" — and turns generic good intentions into this stack's concrete rules.
It lives inside the document registered as `manifest.sources.coding_standards` (project-owned;
default `docs/coding-standards.md`), which `brainstorming` loads at design and `reviewer` checks
against — that placement, not repetition in prompts, is what makes the rules impossible to forget.

## Steps

1. **Detect, from evidence.** Dependency manifests and lockfiles give the languages, frameworks,
   and the *installed* versions; the repository gives the application type — web app, API, mobile,
   CLI, library. Record versions as found. Write rules for the installed versions, not the newest
   ones: a version upgrade is a feature for the roadmap, never a playbook side effect.
2. **Mine the codebase for the real conventions.** How modules are laid out, how errors flow, how
   tests are written here. In an existing project the playbook describes the house style before it
   prescribes anything; where existing code contradicts the framework's idiom, note which one wins
   and why rather than silently picking.
3. **Record the architecture stances — proposed from evidence, decided by the owner.** Nothing here
   is preset by the kit, and there is rarely only one. A project answers the architecture question
   separately in each area where its answer actually differs — the domain, the HTTP surface,
   background work, the client, how data is reached. A CRUD app has one line; a layered product has
   three or four. Derive the areas from the application type and from what this codebase already
   separates, never from a checklist: inventing areas a project does not have is the failure mode
   here, because every line becomes a rule somebody has to obey forever.

   Make it answerable by defaulting. **The framework's own idiom holds everywhere the owner does not
   deviate**, so the question is never "choose an architecture" — nobody answers that well at
   bootstrap, before the code that would inform it exists — but "here is where I would depart from
   the framework, and what that buys and costs". Areas where the framework's default is plainly
   right are declared in *taken as given*, not asked.

   Put the set up in one round per `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md` — one fork per area,
   recommendation marked, each with its concrete reading attached. A stance answered "DDD" and
   nothing else leaves you to invent where boundaries sit, what a module is, and what may cross one,
   and that invented part is what the owner will feel in every later review. These are the most
   expensive decisions the kit records and every future feature inherits them, so they earn a screen
   of the owner's attention where a feature decision earns a line.

   An area the project does not have yet is not asked about. When it appears — the product grows
   background work it never had — that is one question at the refresh that meets it, and one new row.

   If the owner is absent, derive the stances from the code, mark them `derived` in the document, and
   surface them where the run's decisions are actually read — the PR's Assumptions, the sprint report
   — not only in a log. A stance nobody chose is the first thing the owner should be offered the
   chance to correct, rather than a line they discover months later.

   Once recorded they are followed consistently and change only on the owner's word — never as a side
   effect of a refresh; proportionality applies *inside* them — boundaries per the stance of that
   area, no ceremony around a five-line helper.
4. **Research the ecosystem, don't recall it.** With network access, check the official
   documentation and release notes for the installed framework version, and the ecosystem's own
   catalogues (Packagist, npm, crates.io, pub.dev — whatever the stack uses) for the library map
   below. Prefer sources over memory: training-data knowledge of an ecosystem is stale by
   definition. Without network, write from knowledge and mark the library map `unverified` so the
   next connected session knows to check it.
5. **Write the playbook into the registered document**, updating in place and preserving the
   owner's own edits — reconcile, never clobber. End it with a **fingerprint**: the dependency
   manifests and lockfiles it was generated from, with the framework versions read from them, and
   the generation date — that is what makes the freshness check below cost seconds instead of a
   re-research. Sections:
   - **Stack profile** — languages, frameworks, installed versions, application type. One block.
   - **Architecture stances** — a table, one row per area: the area, the stance, and what it means
     concretely in this repository. `brainstorming` designs inside it and `reviewer` checks against
     it, and both need the row for the area they are touching — a feature changing the HTTP surface
     should not have to read a paragraph about the whole product to find its rule.
   - **Patterns this framework rewards** — the idioms this stack is designed around (for a Laravel
     app: form requests, policies, jobs; for the stack at hand: its own list), and the line each
     earns its place with. Include when a heavier pattern is warranted, stated as an entry
     condition, not a mood.
   - **Library map** — problem domain → where this ecosystem already solved it, keyed to the
     domains this product actually has (read the roadmap): auth, payments, media, search, whatever
     is real here. This is what the Design step's ecosystem scan and the Build step consult before
     writing anything by hand.
   - **Testing idioms** — how this stack's community actually tests, mapped to the layers in
     `.agent-kit/project/instructions.md`.
6. **Keep it loadable.** Every rule is one line with its justification; the whole playbook should
   be readable in a minute, because it is read before every feature. Depth belongs in the linked
   official docs, not here.

The always-on proportionality rule (engine: "Reaching for what already exists") is the frame for
everything the playbook recommends — the library map says *where to look*, that rule says *when
taking is right*. The playbook must not restate it, only rely on it.

## The freshness check

`ship` runs this at the start of every run (and `sprint`'s features inherit it through
`ship --brief`), so the owner never has to remember the playbook exists. Three outcomes, and only
one of them costs anything:

- **Current** — the registered document exists, carries a fingerprint, and the fingerprint still
  matches the dependency manifests. Say nothing and move on; this is the outcome almost every run
  hits, and it must cost seconds.
- **Missing** — no playbook, or a standards document with no fingerprint (written before this
  skill existed). Run the full generation above. Interactive runs put the stance round up with each
  area's concrete reading; headless ones derive them, mark them `derived`, and surface them as step
  3 requires.
- **Stale** — the fingerprint no longer matches: dependencies were added or removed, a framework
  version moved. Refresh what the drift touches — the stack profile and the library map, plus a
  patterns look when the framework itself changed — and leave the recorded stances untouched;
  they change only when the owner says so. Note the refresh in one line so the run's record shows
  why the standards moved.

  Two things a refresh looks at without touching. Whether the code still matches the stance recorded
  for each area — where they have visibly parted, say so in one line naming the area, because which
  of the two is wrong is the owner's call and they cannot make it while nobody tells them the two
  diverged. And whether the project has grown an area the table has no row for; that is the one
  question a refresh may ask.

The owner can still ask for a refresh at any time — after adopting a new library worth
generalizing, or when changing a recorded stance, which only ever happens by their word.
