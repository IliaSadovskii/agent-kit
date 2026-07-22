#!/usr/bin/env bash
#
# Validate the kit repository itself: the payload, the installer, and one real install.
# Run locally before a release; CI runs the same script.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

errors=0
fail() { printf 'ERROR: %s\n' "$1" >&2; errors=$((errors + 1)); }
step() { printf '\n== %s ==\n' "$1"; }

# --------------------------------------------------------------------------------------------
step "repository layout"

for path in install.sh VERSION CHANGELOG.md README.md catalog.tsv \
            kit/.agent-kit/engine.md kit/root/CLAUDE.block.md kit/root/AGENTS.block.md \
            templates/CLAUDE.md templates/AGENTS.md \
            templates/.agent-kit/project/manifest.yml templates/.agent-kit/project/instructions.md \
            templates/.claude/settings.json templates/.codex/hooks.json; do
  [ -e "$path" ] || fail "missing: $path"
done

VERSION="$(cat VERSION 2>/dev/null || echo)"
printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || fail "VERSION is not semver: $VERSION"
grep -q "## $VERSION" CHANGELOG.md 2>/dev/null || fail "CHANGELOG.md has no entry for $VERSION"

# The project-owned corner must never ship inside the payload — an update would overwrite it.
[ ! -e kit/.agent-kit/project ] || fail "kit/.agent-kit/project must not exist (user-owned)"
[ ! -e kit/.claude/settings.json ] || fail "kit/.claude/settings.json must live in templates/ (shared file)"
[ ! -e kit/.codex/hooks.json ] || fail "kit/.codex/hooks.json must live in templates/ (shared file)"

for template in templates/CLAUDE.md templates/AGENTS.md; do
  grep -q 'kit:managed:start' "$template" || fail "$template has no managed-block start marker"
  grep -q 'kit:managed:end' "$template" || fail "$template has no managed-block end marker"
done

grep -q '^bootstrapped: false' templates/.agent-kit/project/manifest.yml \
  || fail "the manifest template must ship unbootstrapped"

# --------------------------------------------------------------------------------------------
step "no project-specific leakage in the payload"

leaks="$(grep -rniE 'beeplish|english push tutor' kit templates 2>/dev/null || true)"
if [ -n "$leaks" ]; then
  printf '%s\n' "$leaks" >&2
  fail "payload mentions a specific project"
fi

# --------------------------------------------------------------------------------------------
step "shell syntax"

while IFS= read -r script; do
  bash -n "$script" || fail "syntax error: $script"
done < <(find . -name '*.sh' -not -path './.git/*')

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning install.sh kit/.agent-kit/scripts/*.sh scripts/*.sh \
    || fail "shellcheck reported problems"
else
  printf 'shellcheck not installed — skipped\n'
fi

# --------------------------------------------------------------------------------------------
step "adapters match catalog.tsv"

python3 scripts/generate-adapters.py --check || fail "adapter wrappers drifted from catalog.tsv"

# --------------------------------------------------------------------------------------------
step "install into a scratch project"

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

git -C "$SANDBOX" init -q
printf '# Scratch\n' > "$SANDBOX/README.md"

if ! bash install.sh install --from "$REPO" --dir "$SANDBOX" > "$SANDBOX/install.log" 2>&1; then
  cat "$SANDBOX/install.log" >&2
  fail "install failed"
fi
grep -qE '^  conflict ' "$SANDBOX/install.log" && fail "a fresh install reported conflicts"

# The kit ships its own in-project validator; a fresh install must satisfy it.
if [ -f "$SANDBOX/.agent-kit/scripts/validate.sh" ]; then
  (cd "$SANDBOX" && bash .agent-kit/scripts/validate.sh) \
    || fail "in-project validation failed after install"
else
  fail "installed kit has no .agent-kit/scripts/validate.sh"
fi

step "update is idempotent"

if ! bash install.sh update --from "$REPO" --dir "$SANDBOX" > "$SANDBOX/update.log" 2>&1; then
  cat "$SANDBOX/update.log" >&2
  fail "update failed"
fi
grep -qE '^  (create|update|remove) ' "$SANDBOX/update.log" \
  && { grep -E '^  (create|update|remove) ' "$SANDBOX/update.log" >&2
       fail "re-running update on an unchanged kit changed files"; }
grep -qE '^  conflict ' "$SANDBOX/update.log" \
  && fail "update reported conflicts on an unchanged project"

step "local edits survive an update"

printf '\nProject-local edit.\n' >> "$SANDBOX/.agent-kit/workflows/ship.md"
bash install.sh update --from "$REPO" --dir "$SANDBOX" > "$SANDBOX/update2.log" 2>&1
grep -q 'conflict .agent-kit/workflows/ship.md' "$SANDBOX/update2.log" \
  || fail "a locally edited file was not reported as a conflict"
grep -q 'Project-local edit' "$SANDBOX/.agent-kit/workflows/ship.md" \
  || fail "a locally edited file was overwritten by update"
[ -f "$SANDBOX/.agent-kit/workflows/ship.md.kit-new" ] \
  || fail "no .kit-new copy was written for the conflicting file"

step "single-provider install"

SANDBOX_CLAUDE="$(mktemp -d)"
git -C "$SANDBOX_CLAUDE" init -q
if ! bash install.sh install --from "$REPO" --dir "$SANDBOX_CLAUDE" --providers claude \
     > "$SANDBOX_CLAUDE/install.log" 2>&1; then
  cat "$SANDBOX_CLAUDE/install.log" >&2
  fail "claude-only install failed"
fi
[ ! -e "$SANDBOX_CLAUDE/.codex" ] || fail "claude-only install created .codex/"
[ ! -e "$SANDBOX_CLAUDE/AGENTS.md" ] || fail "claude-only install created AGENTS.md"
(cd "$SANDBOX_CLAUDE" && bash .agent-kit/scripts/validate.sh) \
  || fail "in-project validation failed for a claude-only install"
rm -rf "$SANDBOX_CLAUDE"

step "user-owned files are never overwritten"

printf 'MINE\n' > "$SANDBOX/.agent-kit/project/instructions.md"
bash install.sh update --from "$REPO" --dir "$SANDBOX" >/dev/null 2>&1
grep -qx 'MINE' "$SANDBOX/.agent-kit/project/instructions.md" \
  || fail "update overwrote the user-owned project instructions"

# --------------------------------------------------------------------------------------------
printf '\n'
if [ "$errors" -ne 0 ]; then
  printf 'Kit validation failed with %s error(s).\n' "$errors" >&2
  exit 1
fi
printf 'Kit validation passed.\n'
