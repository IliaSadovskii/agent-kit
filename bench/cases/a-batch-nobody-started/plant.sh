#!/bin/sh
set -e
cat > "$BENCH/batch.toml" <<'TOML'
name = "vat"

[mvp]
inside = ["a price with VAT on it"]
outside = ["everything the owner did not name"]

[[scenarios]]
what = "the money is quoted and the quote is read back"
ends = "the declared command comes back green"

[features.add-vat]
brief = "Money quotes a price with VAT"

[features.rates]
brief = "A table of VAT rates"
TOML
$KIT -C "$REPO" batch new "$BENCH/batch.toml" >/dev/null
# The second feature has a run and nothing has started it. Left alone it is a
# `run-created`; owned by a batch that has not run, it is the batch's to start.
$KIT -C "$REPO" run new rates --brief "A table of VAT rates" >/dev/null
