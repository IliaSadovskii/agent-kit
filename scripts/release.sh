#!/usr/bin/env bash
#
# Cut a kit release: bump every version marker, validate, commit, tag.
#
#   scripts/release.sh 0.4.0
#
# Push with `git push && git push --tags`. The plugin's own `version` field is what pins installs:
# Claude Code treats a plugin without one as changing on every commit, so it must be bumped here.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

VERSION="${1:-}"
[ -n "$VERSION" ] || { printf 'usage: scripts/release.sh <version>\n' >&2; exit 1; }
printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' \
  || { printf 'error: %s is not a semver version\n' "$VERSION" >&2; exit 1; }

[ -z "$(git status --porcelain)" ] \
  || { printf 'error: working tree is dirty — commit or stash first\n' >&2; exit 1; }

git rev-parse --verify --quiet "refs/tags/v$VERSION" >/dev/null \
  && { printf 'error: tag v%s already exists\n' "$VERSION" >&2; exit 1; }

grep -q "^## $VERSION" CHANGELOG.md \
  || { printf 'error: CHANGELOG.md has no "## %s" section\n' "$VERSION" >&2; exit 1; }

printf '%s\n' "$VERSION" > VERSION

# The validator checks that these three agree, so bump them together rather than by hand.
python3 - "$VERSION" <<'PY'
import json, sys

version = sys.argv[1]

for path, apply in (
    ("plugins/agent-kit/.claude-plugin/plugin.json", lambda d: d.update(version=version)),
    (".claude-plugin/marketplace.json", lambda d: d.setdefault("metadata", {}).update(version=version)),
):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    apply(data)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
PY

bash scripts/validate.sh

git add VERSION CHANGELOG.md plugins/agent-kit/.claude-plugin/plugin.json .claude-plugin/marketplace.json
# VERSION may already hold this value (the first release of a version prepared in advance);
# tagging is still the point of this script, so an empty commit is not an error.
if ! git diff --cached --quiet; then
  git commit -m "release: v$VERSION"
fi
git tag -a "v$VERSION" -m "agent-kit v$VERSION"

printf '\nTagged v%s. Publish with:\n  git push && git push --tags\n' "$VERSION"
