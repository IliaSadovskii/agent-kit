---
name: stack-playbook
description: Generate or refresh the stack playbook inside the project's registered coding standards — detect the stack and application type, record the owner's architecture stance, research the framework's current idioms and ecosystem libraries, and write short justified rules the pipelines load before every feature. Invoked by idea-interview at bootstrap, or when the user asks to create or update stack standards or the playbook.
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
3. **Record the architecture stance — the owner's call, not a detection.** One structured question
   when the owner is present: the style this project is built in — the framework's own idiom,
   DDD-style modules, or whatever the owner names — with what that means concretely for this repo
   (where boundaries live, what a "module" is). If the owner is absent, derive the stance from the
   code and log it as an assumption. The stance is followed consistently once recorded;
   proportionality applies *inside* it — module boundaries per the stance, no ceremony around a
   five-line helper.
4. **Research the ecosystem, don't recall it.** With network access, check the official
   documentation and release notes for the installed framework version, and the ecosystem's own
   catalogues (Packagist, npm, crates.io, pub.dev — whatever the stack uses) for the library map
   below. Prefer sources over memory: training-data knowledge of an ecosystem is stale by
   definition. Without network, write from knowledge and mark the library map `unverified` so the
   next connected session knows to check it.
5. **Write the playbook into the registered document**, updating in place and preserving the
   owner's own edits — reconcile, never clobber. Sections:
   - **Stack profile** — languages, frameworks, installed versions, application type. One block.
   - **Architecture stance** — the recorded style and its concrete meaning here.
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

Refresh is manual: rerun this skill when the owner asks, or when bootstrap runs again. No
automatic staleness checking.
