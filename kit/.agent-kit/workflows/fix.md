# Fix workflow

The light path for a genuinely small, local, low-risk change — a bug fix, a copy tweak, a small
refactor, a dependency bump. Choosing `fix` over `ship` is the user's call; there is no automatic
heuristic.

1. **Understand** — read the request and the surrounding code until the change is clear, and
   confirm the scope really is small and local.
2. **Change** — make it on a branch, following the project's conventions. Keep the blast radius
   small.
3. **Test** — cover the changed behavior and run the relevant tests and lint.
4. **Review** — delegate an independent diff review to `reviewer`, fix critical and major findings,
   and rerun the affected verification. Scan the diff for obvious security risks — injected input,
   exposed secrets, unsafe file or process use — as part of this pass; it stands in for `ship`'s
   full security stage, not for a deep audit.
5. **PR** — push the branch and open a pull request per `.agent-kit/rules/pull-requests.md`.

Relative to `ship` this skips ideation, the design gate, the written plan, and the dedicated
security pass. Everything else holds.

If the task turns out to need a design, a new domain model, or contract changes, stop and offer to
switch to `ship` rather than forcing it through the light path. The user decides.
