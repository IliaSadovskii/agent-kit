# Codex adapter instructions

Before taking any task action, read these files completely and obey them in this order:

1. `.agent-kit/engine.md`
2. `.agent-kit/project/instructions.md`
3. `.agent-kit/platforms/codex.md`
4. `.agent-kit/project/manifest.yml`

The files under `.agent-kit/` are the provider-neutral source of truth. `.agents/skills/` and
`.codex/` are discovery/runtime adapters only. When a canonical workflow or skill is selected, read
that canonical file completely before acting.

Treat `$go`, `go`, and a user request to "route me" / "what can I do" as the same entry-point
router; likewise `$ship`/`ship`, `$infra`, `$plan-next`, and `$riff` each map to their workflow.
This keeps hosted tasks usable even when the surface does not render an explicit skill picker.
