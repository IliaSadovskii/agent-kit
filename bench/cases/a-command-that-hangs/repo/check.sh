#!/bin/sh
# A wrapper that starts something and then hangs, which is what a
# project's test command usually is.
(while true; do echo x >> "$BENCH/still-alive"; sleep 0.2; done) &
sleep 60
