#!/bin/sh
grep -q '"passed": false' "$RUN_DIR/steps/2-verify/output.json" || { echo "verify did not record what it saw"; exit 1; }
grep -q "one check failed" "$RUN_DIR/steps/2-verify/output.json" || { echo "what the command printed was not kept"; exit 1; }
