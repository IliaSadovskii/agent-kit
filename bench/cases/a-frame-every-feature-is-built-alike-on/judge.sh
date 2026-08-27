#!/bin/sh
# Read out of the input the driver actually composed, and not out of an answer
# that would be grepping itself: what is measured is that the line reached the
# session, which is the one thing a feature cannot work out for itself.
for slug in rates quote; do
  input=".agent-kit/v3/runs/$slug/steps/0-design/attempt-1/input.md"
  test -f "$input" || { echo "$slug never had a design composed at all"; exit 1; }
  # The frame's own words, which the case itself declared — never the heading
  # the kit prints above them. A judge measuring the kit's prose goes red the
  # day somebody rewrites a sentence, and says nothing about the mechanism.
  grep -q 'ставка живёт одной константой' "$input" ||
    { echo "$slug was designed without the frame its neighbours are held to"; exit 1; }
done
exit 0
