#!/bin/sh
# The trap must have sprung before there is anything to judge: a child that
# never ran leaves the file missing, and two absences compare equal.
test -s "$BENCH/still-alive" || { echo "no child ever ran, so nothing was killed"; exit 1; }
before=$(wc -c < "$BENCH/still-alive")
sleep 1.5
after=$(wc -c < "$BENCH/still-alive")
test "$before" = "$after" || { echo "the child outlived the command it belonged to"; exit 1; }
