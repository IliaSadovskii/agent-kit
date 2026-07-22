#!/usr/bin/env bash
#
# Cut a kit release: validate, bump VERSION, commit, tag.
#
#   scripts/release.sh 0.3.0
#
# Push with `git push && git push --tags`. Projects install the highest semver tag by default, so
# the tag is what makes a release live.

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
bash scripts/validate.sh

git add VERSION CHANGELOG.md
git commit -m "release: v$VERSION"
git tag -a "v$VERSION" -m "agent-kit v$VERSION"

printf '\nTagged v%s. Publish with:\n  git push && git push --tags\n' "$VERSION"
