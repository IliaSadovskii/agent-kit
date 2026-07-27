#!/usr/bin/env bash
set -uo pipefail

# Resolve the project root from this script's own location: the validator must check the
# project it is installed in, whatever directory it is called from.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
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
  CLAUDE.md \
  .claude/settings.json \
  .agent-kit/engine.md \
  .agent-kit/project/instructions.md \
  .agent-kit/project/manifest.yml \
  .agent-kit/GUIDE.md \
  .agent-kit/catalog.txt \
  .agent-kit/scripts/session-setup.sh \
  .agent-kit/rules/autonomous-mode.md \
  .agent-kit/rules/pull-requests.md; do
  require_file "$file"
done

while read -r kind name; do
  case "$kind" in
    ''|'#'*) continue ;;
    workflow)
      require_file ".agent-kit/workflows/$name.md"
      require_file ".claude/commands/$name.md"
      ;;
    skill)
      require_file ".agent-kit/skills/$name.md"
      require_file ".claude/skills/$name/SKILL.md"
      ;;
    role)
      require_file ".agent-kit/roles/$name.md"
      require_file ".claude/agents/$name.md"
      ;;
    *) fail "unknown catalog kind: $kind" ;;
  esac
done < .agent-kit/catalog.txt

# Canonical behavior must not name a provider surface directly — wrappers own that.
# The dollar sign is intentionally literal in this validation pattern.
# shellcheck disable=SC2016
canonical_matches="$(grep -R -n -E '\.claude/project\.yml|\$CLAUDE_PROJECT_DIR|/security-review|/code-review' \
  .agent-kit/engine.md .agent-kit/workflows .agent-kit/skills .agent-kit/roles .agent-kit/rules \
  2>/dev/null || true)"
if [ -n "$canonical_matches" ]; then
  printf '%s\n' "$canonical_matches" >&2
  fail "provider-specific reference found in canonical behavior"
fi

for wrapper in .claude/commands/*.md .claude/skills/*/SKILL.md .claude/agents/*.md; do
  [ -f "$wrapper" ] || continue
  lines="$(wc -l < "$wrapper" | tr -d ' ')"
  [ "$lines" -le 20 ] || fail "adapter owns too much behavior ($lines lines): $wrapper"
  grep -q '\.agent-kit/' "$wrapper" || fail "adapter does not point to canonical kit: $wrapper"
done

grep -q '@.agent-kit/engine.md' CLAUDE.md || fail "CLAUDE.md does not import the engine"

if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool .claude/settings.json >/dev/null || fail "invalid .claude/settings.json"
fi

[ ! -f scripts/cloud-setup.sh ] || bash -n scripts/cloud-setup.sh || fail "invalid scripts/cloud-setup.sh"
bash -n .agent-kit/scripts/session-setup.sh || fail "invalid session setup wrapper"

if [ "$errors" -ne 0 ]; then
  printf '\nAgent kit validation failed with %s error(s).\n' "$errors" >&2
  exit 1
fi

printf 'Agent kit validation passed.\n'
