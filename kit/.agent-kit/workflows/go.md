# Go — entry-point router

`/go` is the single entry point to the kit. It reads project state and routes the user to the right
workflow or skill, or stays out of the way. It builds nothing itself — it only dispatches. Follow
`.agent-kit/engine.md` and the active provider adapter.

## Behavior

1. **Read state** — read `.agent-kit/project/manifest.yml`.
2. **Not bootstrapped** (manifest missing or `bootstrapped: false`): there is only one sensible
   action — run canonical skill `idea-interview`. Do NOT show a menu.
3. **Bootstrapped** — determine intent:
   - With free-text arguments: classify the intent, name the branch you will take, and **confirm
     with the user before entering it**. Never enter a workflow silently.
   - Without arguments: present the menu below and let the user choose.
4. **Dispatch** — hand off to the chosen canonical workflow/skill, carrying any context already
   gathered. From that point the target's own rules apply.

## Menu (bootstrapped projects)

| Intent | Routes to |
|---|---|
| Build a feature — autonomous to PR | `ship` |
| Build a feature with me involved | `ship --manual` |
| Make a small change / fix | `fix` |
| Debug a failure | `debug` |
| Think about a feature / product | `riff` |
| Review my changes | `review` |
| Add or improve tests | `test` |
| Reconcile the docs | `docs` |
| Preview the roadmap | `plan-next` |
| Set up infrastructure | `infra` (opens a local / cloud / status / update sub-menu) |
| Just help me in the terminal | dormant — no workflow |

"Just help me in the terminal" is not a workflow: acknowledge and continue as a normal collaborator
under the project baseline (see `.agent-kit/engine.md` → "When these rules apply").

## Default without `/go`

Invoking `/go` is explicit routing. If the user simply types a request without any command, do NOT
auto-run this router or any workflow — behave as a normal collaborator under the project baseline,
and at most *offer* the relevant branch. The router never hijacks free-text input.

## Extending

All designed menu entries are implemented. When adding a new one later, register the target in
`.agent-kit/catalog.txt` first, then add its row here — never point the menu at a workflow/skill that
does not yet exist.