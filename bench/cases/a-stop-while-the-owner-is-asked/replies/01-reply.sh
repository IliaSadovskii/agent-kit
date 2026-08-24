#!/bin/sh
# What a person does from another terminal while the run is about to wait on
# them. The driver holds the run, so this goes to the driver rather than into
# the file the driver is writing.
$KIT run stop add-vat "the owner said so" > "$BENCH/stop-said" 2>&1
