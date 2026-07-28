---
name: stack-playbook
description: Generate or refresh the stack playbook inside the project's registered coding standards — detect the stack and application type, research the framework's current idioms and ecosystem libraries, derive each area's architecture stance from the code and that research, write short justified rules the pipelines load before every feature, and close by showing the owner what was concluded and inviting the rules only they know. Invoked by idea-interview at bootstrap, or when the user asks to create or update stack standards or the playbook.
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
   prescribes anything; where existing code contradicts the stack's idiom, record both sides — step
   4 decides what it means for new work, and the close-out puts that decision to the owner.
3. **Research the ecosystem, don't recall it.** With network access, check the official
   documentation and release notes for the installed framework version, and the ecosystem's own
   catalogues (Packagist, npm, crates.io, pub.dev — whatever the stack uses) for the library map
   below. Prefer sources over memory: training-data knowledge of an ecosystem is stale by
   definition. Without network, write from knowledge and mark the library map `unverified` so the
   next connected session knows to check it.
4. **Write down the architecture stances — observed and researched, not interviewed.** Nothing here
   is preset by the kit, and there is rarely only one. A project answers the architecture question
   separately in each area where its answer actually differs — the domain, the HTTP surface,
   background work, the client, how data is reached. A CRUD app has one line; a layered product has
   three or four. Derive the areas from the application type and from what this codebase already
   separates, never from a checklist: inventing areas a project does not have is the failure mode
   here, because every line becomes a rule somebody has to obey forever.

   Each row is filled from the two sources above it: what the code already does, and what this stack
   is understood to do well. Nothing here is asked. Choosing an architecture is not a question anyone
   answers well at bootstrap, before the code that would inform the answer exists, and a stance the
   owner does have will land far better against a finished playbook than against a blank prompt —
   which is what the close-out in step 6 is for.

   Where the code and the stack's practice disagree, follow the code, record the idiom as the rule
   for new work, and carry the disagreement into the close-out as a line the owner can overturn.
   Silently picking either side is the one thing not allowed.

   Once recorded, stances are followed consistently and change only on the owner's word — never as a
   side effect of a refresh; proportionality applies *inside* them — boundaries per the stance of
   that area, no ceremony around a five-line helper.
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
7. **Close out: show what you concluded, then invite what only the owner knows.** This replaces the
   interview that used to open this skill, and it is the better trade — an owner reacting to a
   finished playbook remembers what they actually care about, where the same person facing a blank
   architecture question at bootstrap does not.

   Put up one screen: the stack profile in a line, the stance table, the library map's picks, the
   testing idioms, and any disagreement step 4 carried here — each of those as one line with what
   you did about it. Then invite the addition. Phrase it so the invitation is concrete about *where*
   an answer would go and open about *what* it could be — the shape being roughly *this was derived
   from your code and from the practice of this stack; none of your own rules are in it yet — what
   is wrong, and what is missing?* Render it in the project's language and its own words rather than
   translating a fixed sentence.

   That wording is doing specific work, so keep its two halves. Naming the sources is what invites
   disagreement with a conclusion rather than deference to it. Saying that nothing of theirs is in
   the document yet is what makes the owner scan the table for the gap — which is the moment a
   preference the code could never have shown gets remembered and said out loud.

   Silence is consent: no answer means the playbook stands as written, and an owner who does not
   care has paid one screen. Whatever they add is written into the document as their rule, in their
   words, attributed so a later refresh preserves it rather than reconciling it away. Headless runs
   ask nothing — the same summary goes to the run record.

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
  skill existed). Run the full generation above, close-out included: this is the one moment the
  owner is invited to put their own rules in, and it costs a screen.
- **Stale** — the fingerprint no longer matches: dependencies were added or removed, a framework
  version moved. Refresh what the drift touches — the stack profile and the library map, plus a
  patterns look when the framework itself changed — and leave the recorded stances untouched;
  they change only when the owner says so. Note the refresh in one line so the run's record shows
  why the standards moved.

  Two things a refresh reports without touching: an area where the code has visibly parted from the
  stance recorded for it, and an area the project has grown that the table has no row for. Both are
  lines in that one-line note, not questions — the owner is mid-feature, and neither is urgent
  enough to interrupt it. They can act on either by asking for a refresh.

The owner can still ask for a refresh at any time — after adopting a new library worth
generalizing, or when changing a recorded stance, which only ever happens by their word.
