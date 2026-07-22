#!/usr/bin/env bash
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 1

errors=0

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  errors=$((errors + 1))
}

require_file() {
  [ -f "$1" ] || fail "missing required file: $1"
}

for file in \
  .agent-kit/engine.md \
  .agent-kit/project/instructions.md \
  .agent-kit/project/manifest.yml \
  .agent-kit/GUIDE.md \
  .agent-kit/catalog.txt \
  .agent-kit/scripts/session-setup.sh \
  .agent-kit/platforms/claude.md \
  .agent-kit/platforms/codex.md \
  .agent-kit/rules/autonomous-mode.md \
  .agent-kit/rules/pull-requests.md \
  CLAUDE.md AGENTS.md \
  .claude/settings.json .codex/hooks.json; do
  require_file "$file"
done

while read -r kind name; do
  case "$kind" in
    ''|'#'*) continue ;;
    workflow)
      require_file ".agent-kit/workflows/$name.md"
      require_file ".claude/commands/$name.md"
      require_file ".agents/skills/$name/SKILL.md"
      ;;
    skill)
      require_file ".agent-kit/skills/$name.md"
      require_file ".claude/skills/$name/SKILL.md"
      require_file ".agents/skills/$name/SKILL.md"
      ;;
    role)
      require_file ".agent-kit/roles/$name.md"
      require_file ".claude/agents/$name.md"
      require_file ".codex/agents/$name.toml"
      ;;
    *) fail "unknown catalog kind: $kind" ;;
  esac
done < .agent-kit/catalog.txt

common_paths=(
  .agent-kit/engine.md
  .agent-kit/workflows
  .agent-kit/skills
  .agent-kit/roles
  .agent-kit/rules
)

# The dollar sign is intentionally literal in these validation patterns.
# shellcheck disable=SC2016
canonical_matches="$(grep -R -n -E '\.Codex|\.claude/project\.yml|\$CLAUDE_PROJECT_DIR|/security-review|/code-review' \
  "${common_paths[@]}" 2>/dev/null || true)"
if [ -n "$canonical_matches" ]; then
  printf '%s\n' "$canonical_matches" >&2
  fail "provider-specific reference found in canonical behavior"
fi

# shellcheck disable=SC2016
codex_matches="$(grep -R -n -E '\.Codex|\.claude/project\.yml|\$CLAUDE_PROJECT_DIR' \
  .agents .codex AGENTS.md 2>/dev/null || true)"
if [ -n "$codex_matches" ]; then
  printf '%s\n' "$codex_matches" >&2
  fail "stale Claude/Codex path found in the Codex adapter"
fi

for wrapper in .claude/commands/*.md .claude/skills/*/SKILL.md .claude/agents/*.md \
  .agents/skills/*/SKILL.md .codex/agents/*.toml; do
  [ -f "$wrapper" ] || continue
  lines="$(wc -l < "$wrapper" | tr -d ' ')"
  [ "$lines" -le 20 ] || fail "adapter owns too much behavior ($lines lines): $wrapper"
  grep -q '\.agent-kit/' "$wrapper" || fail "adapter does not point to canonical kit: $wrapper"
done

grep -q '@.agent-kit/engine.md' CLAUDE.md || fail "CLAUDE.md does not import the neutral engine"
grep -q '\.agent-kit/engine.md' AGENTS.md || fail "AGENTS.md does not bootstrap the neutral engine"

if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool .claude/settings.json >/dev/null || fail "invalid .claude/settings.json"
  python3 -m json.tool .codex/hooks.json >/dev/null || fail "invalid .codex/hooks.json"
  if python3 -c 'import tomllib' >/dev/null 2>&1; then
    python3 -c 'import glob, tomllib; [tomllib.load(open(path, "rb")) for path in glob.glob(".codex/agents/*.toml")]' \
      || fail "invalid Codex agent TOML"
  else
    for agent in .codex/agents/*.toml; do
      grep -q '^name = ' "$agent" || fail "Codex agent has no name: $agent"
      grep -q '^description = ' "$agent" || fail "Codex agent has no description: $agent"
      grep -q '^developer_instructions = ' "$agent" || fail "Codex agent has no instructions: $agent"
    done
  fi
fi

[ ! -f scripts/cloud-setup.sh ] || bash -n scripts/cloud-setup.sh || fail "invalid scripts/cloud-setup.sh"
bash -n .agent-kit/scripts/session-setup.sh || fail "invalid session setup wrapper"

if [ "$errors" -ne 0 ]; then
  printf '\nAgent kit validation failed with %s error(s).\n' "$errors" >&2
  exit 1
fi

printf 'Agent kit validation passed.\n'
