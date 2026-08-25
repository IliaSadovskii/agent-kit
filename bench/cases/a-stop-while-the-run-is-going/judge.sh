#!/bin/sh
# The trap first: the stop was really asked for, and it went to the driver
# rather than into the file the driver was writing.
test -s "$BENCH/stop-said" || { echo "nothing ever asked this run to stop"; exit 1; }
grep -q '^stop-asked:' "$BENCH/stop-said" ||
  { echo "the stop was written into the state under a driver that holds it"; exit 1; }

# The step that was running when it was asked finished; the ones after it did not.
test -f "$RUN_DIR/steps/1-build/output.json" || { echo "the build never finished"; exit 1; }
test ! -d "$RUN_DIR/steps/2-verify" || { echo "a step ran after the run was told to stop"; exit 1; }
test -z "$(find "$BENCH" -maxdepth 1 -name "gh-opened-*" -print -quit)" || { echo "a pull request was opened for a run that was stopped"; exit 1; }
exit 0
