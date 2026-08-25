#!/bin/sh
# A person, mid-night: the only moment a skip means anything. quote is being
# built right now — its own session is waiting for this line to happen.
$KIT -C "$REPO" batch skip vat quote "the rates table is not settled yet" > "$BENCH/skip-said" 2>&1
printf 'asked\n' > "$BENCH/skip-asked"
printf 'RATE = 20\n' >> rates.py
