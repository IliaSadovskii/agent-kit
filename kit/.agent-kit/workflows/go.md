# Go — entry-point router

`/go` reads project state and routes to the right workflow. It builds nothing itself.

1. Read `.agent-kit/project/manifest.yml`.
2. **Not bootstrapped** (missing manifest or `bootstrapped: false`) — run `idea-interview`. There
   is only one sensible action, so don't show a menu.
3. **Bootstrapped** — with free-text arguments, classify the intent, name the branch you will take,
   and confirm before entering it. Without arguments, show the menu.
4. Hand off to the chosen workflow or skill, carrying the context you already gathered. From there
   its own rules apply.

| Intent | Routes to |
|---|---|
| Build a feature — autonomous to PR | `ship` |
| Build a feature with me involved | `ship --manual` |
| Make a small change or fix | `fix` |
| Debug a failure | `debug` |
| Think about the product, roadmap the ideas | `riff` |
| Review my changes | `review` |
| Add or improve tests | `test` |
| Reconcile the docs | `docs` |
| Set up infrastructure | `infra` |
| Just help me in the terminal | nothing — continue as a normal collaborator |

Invoking `/go` is explicit routing. Plain free text without a command never triggers this router;
see `.agent-kit/engine.md` → "When these rules apply".
