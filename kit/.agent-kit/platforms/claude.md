# Claude Code adapter

- Invocation: repository commands are `/ship`, `/infra`, `/plan-next`, and `/riff`.
- Skills are discovered under `.claude/skills/`; commands under `.claude/commands/`; custom
  subagents under `.claude/agents/`.
- The root `CLAUDE.md` imports the neutral engine and shared project instructions.
- Prefer a branch prefix `claude/` unless the user or repository requires another prefix.
- For independent security review, use Claude Code's dedicated security review capability when
  available; otherwise run a separate adversarial security pass with a fresh subagent/context.
- Open pull requests with the available GitHub integration; fall back to `gh` only when installed
  and authenticated.
- `$ARGUMENTS` in command wrappers is user input for the invoked workflow.
