#!/bin/sh
# Each feature owes the knowledge a block, and each builds in a worktree of its
# own. The block belongs on the branch that feature opens, not in the checkout
# the owner is standing in.
KNOWLEDGE=docs/knowledge/entities.md

# The trap first, read out of the commit the world was made from: a judge that
# reads only the result is green in a project where nobody planted anything.
BEFORE=$(git show "main:$KNOWLEDGE" 2>/dev/null) || { echo "no knowledge was planted at all"; exit 1; }
test -n "$BEFORE" || { echo "the planted knowledge is empty"; exit 1; }
case "$BEFORE" in *kit/rates*|*kit/quote*) echo "a block was already there before the batch ran"; exit 1;; esac

for slug in rates quote; do
  # A tree per run is what makes this case different from the lone run: without
  # one, the checkout that `record` writes into is the one `deliver` commits in.
  grep -q "trees/$slug" "$BATCH_FILE" || { echo "$slug never had a tree of its own"; exit 1; }
  git rev-parse --verify --quiet "refs/heads/kit/$slug" >/dev/null ||
    { echo "$slug opened no branch"; exit 1; }
done

# Each block is in its own feature's commit, on its own branch, under the record
# the design addressed.
for slug in rates quote; do
  git show --name-only --format= "kit/$slug" | grep -q "$KNOWLEDGE" ||
    { echo "$slug's commit does not hold the knowledge it wrote"; exit 1; }
  git show "kit/$slug:$KNOWLEDGE" > "$BENCH/$slug-knowledge.md" ||
    { echo "$slug's branch has no knowledge file at all"; exit 1; }
  grep -q "kit/$slug" "$BENCH/$slug-knowledge.md" ||
    { echo "$slug's block never reached the branch"; exit 1; }
done

# The identifiers are derived, not drawn: the kit can say what they must be.
RATES_ID=$(python3 -c "from agent_kit.knowledge import identifier; print(identifier('rates', 'the rate is a whole percent'))") ||
  { echo "the kit could not say what the identifier should be"; exit 3; }
QUOTE_ID=$(python3 -c "from agent_kit.knowledge import identifier; print(identifier('quote', 'a discount applies before the tax'))") ||
  { echo "the kit could not say what the identifier should be"; exit 3; }
grep -q "id: $RATES_ID\]" "$BENCH/rates-knowledge.md" ||
  { echo "rates' block carries an identifier this run would not produce again"; exit 1; }
grep -q "id: $QUOTE_ID\]" "$BENCH/quote-knowledge.md" ||
  { echo "quote's block carries an identifier this run would not produce again"; exit 1; }

# Under the record it addressed, and not merely somewhere in the file.
awk '/^### Налог/{seen=1; next} /^### /{seen=0} seen && /kit\/rates/{found=1} END{exit !found}' "$BENCH/rates-knowledge.md" ||
  { echo "rates' block is not under the record it addressed"; exit 1; }
awk '/^### Скидка/{seen=1} /^### /{if (!/^### Скидка/) seen=0} seen && /kit\/quote/{found=1} END{exit !found}' "$BENCH/quote-knowledge.md" ||
  { echo "quote's block is not under the record it addressed"; exit 1; }

# Neither branch carries the other's block: two trees that cannot see each other.
grep -q 'kit/quote' "$BENCH/rates-knowledge.md" && { echo "rates' branch carries quote's block"; exit 1; }
grep -q 'kit/rates' "$BENCH/quote-knowledge.md" && { echo "quote's branch carries rates' block"; exit 1; }

# And the checkout the owner is standing in was never written into.
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the project was left on somebody's branch"; exit 1; }
test -z "$(git status --porcelain)" || { echo "the project's own working copy was written into"; exit 1; }
exit 0
