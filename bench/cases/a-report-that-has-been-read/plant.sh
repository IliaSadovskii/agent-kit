#!/bin/sh
set -e
cd "$REPO"
git checkout -q -b kit/old-work
printf 'DISCOUNT = 5\n' >> money.py
git add -A
git commit -qm "the discount"
COMMIT=$(git rev-parse HEAD)
git checkout -q main
git merge -q --squash kit/old-work
git commit -qm "the discount, squashed"
$KIT -C "$REPO" run new old-work --steps design,deliver --brief "A discount before the tax" >/dev/null
for _ in 1 2; do
  $KIT -C "$REPO" run start old-work --provider fake >/dev/null
  $KIT -C "$REPO" run pass old-work >/dev/null
done
WHERE="$REPO/.agent-kit/v3/runs/old-work/steps/1-deliver"
mkdir -p "$WHERE"
cat > "$WHERE/output.json" <<JSON
{
  "branch": "kit/old-work",
  "base": "main",
  "commit": "$COMMIT",
  "pull_request": "https://github.com/owner/project/pull/11"
}
JSON
