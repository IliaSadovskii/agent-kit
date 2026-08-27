#!/bin/sh
set -e
# A run from the same night that a person stopped by hand. `run start` and
# `run stop` are the command surface doing what a driver would have done, so
# nothing here writes a record itself.
$KIT -C "$REPO" run new rates --brief "A table of VAT rates" >/dev/null
$KIT -C "$REPO" run start rates --provider fake >/dev/null
$KIT -C "$REPO" run stop rates "the owner wanted the rates checked first" >/dev/null
