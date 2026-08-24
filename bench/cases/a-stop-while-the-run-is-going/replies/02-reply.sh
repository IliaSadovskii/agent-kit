#!/bin/sh
printf 'RATE = 20\n' >> money.py
# What a person does from another terminal while the build is running.
$KIT run stop add-vat "the owner said so" > "$BENCH/stop-said" 2>&1
