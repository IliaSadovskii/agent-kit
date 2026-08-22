#!/bin/sh
before=$(wc -c < "$BENCH/still-alive" 2>/dev/null || echo 0)
sleep 1.5
after=$(wc -c < "$BENCH/still-alive" 2>/dev/null || echo 0)
test "$before" = "$after" || { echo "the child outlived the command it belonged to"; exit 1; }
