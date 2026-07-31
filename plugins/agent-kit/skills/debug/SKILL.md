---
name: debug
description: Track a failure to its root cause — reproduce, isolate, form and test hypotheses, then either fix the cause with a regression test or report the diagnosis. Invoked by fix when a symptom's cause is not yet known.
---

# Debug

Tracking a failure to its root cause. This is a distinct discipline, not a lighter `ship`:
reproduce, isolate, find the cause, and only then decide what to do about it.

Symptom: `$ARGUMENTS`, or the failure `fix` handed you.

1. **Reproduce** — confirm the failure firsthand. Establish what is broken, what triggers it, and
   what "fixed" will look like. Don't theorize before you can reproduce. If the failure is only
   visible in the running app, `/run` gets you there faster than reasoning about the code.
2. **Isolate** — narrow to the smallest reliable reproduction, removing variables until the failing
   surface is as small as it gets.
3. **Root cause** — form hypotheses and test them one at a time against the reproduction. Follow the
   evidence; reject explanations it does not support. Don't stop at the first plausible symptom.
4. **Resolve** — one of two outcomes:
   - **Fix** — when the fix is clear and in scope, correct the root cause rather than the symptom,
     add a regression test that fails without the fix, then continue through the tail of `fix`:
     test, review, PR.
   - **Diagnosis** — when the cause needs the owner's decision (a product trade-off, a risky
     architectural change, work beyond this scope), stop and report the root cause, the
     reproduction, and the options, without changing code.
