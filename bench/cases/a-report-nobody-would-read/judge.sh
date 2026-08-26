#!/bin/sh
# The trap first: the build really answered with an essay. A judge that only
# measures the open half is green in a night where nobody wrote a long one.
RAW="$RUN_DIR/steps/1-build/attempt-1/raw.txt"
test -s "$RAW" || { echo "the build left nothing to read"; exit 1; }
said=$(wc -c < "$RAW")
test "$said" -gt 10000 || { echo "the build answered in $said bytes, so no essay was ever planted"; exit 1; }

BODY="$RUN_DIR/pull-request.md"
test -s "$BODY" || { echo "no pull request was composed"; exit 1; }
sed -n '1,/^<details>/p' "$BODY" > "$BENCH/open-half.txt"
open=$(wc -c < "$BENCH/open-half.txt")
test "$open" -lt 5000 || { echo "the open half is $open bytes: nothing cut it"; exit 1; }

# Cut, not thrown away: the reader still gets the beginning, and the end of the
# essay is in the body — under the spoiler, which is where the excess belongs.
grep -q 'ESSAY-BEGINS-HERE' "$BENCH/open-half.txt" || { echo "the open half lost the beginning of what was said"; exit 1; }
grep -q 'ESSAY-ENDS-HERE' "$BENCH/open-half.txt" && { echo "the whole essay is still open"; exit 1; }
grep -q 'ESSAY-ENDS-HERE' "$BODY" || { echo "the essay was dropped rather than folded away"; exit 1; }
exit 0
