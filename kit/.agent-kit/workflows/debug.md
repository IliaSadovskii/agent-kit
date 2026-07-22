# Debug workflow

A distinct discipline for tracking down a failure to its root cause — not a lighter `ship`. It is
systematic: confirm the failure, narrow it to the smallest reproduction, form and test hypotheses,
and only then fix at the root cause rather than the symptom. Follow `.agent-kit/engine.md` and the
active provider adapter. Never merge PRs.

## Shape

```
reproduce → isolate → find root cause → (fix + regression test) | diagnosis
```

## Pipeline

1. **Reproduce** — confirm the failure firsthand. Establish exactly what is broken, the conditions
   that trigger it, and what "fixed" will look like. Do not theorize before you can reproduce.
2. **Isolate** — narrow to the smallest reliable reproduction. Remove variables until the failing
   surface is as small as possible.
3. **Root cause** — form hypotheses about the cause and test them one at a time against the
   reproduction. Follow the evidence down to the actual root cause; reject explanations the evidence
   does not support. Do not stop at the first plausible symptom.
4. **Resolve** — choose one of two outcomes:
   - **Fix** — when the fix is clear and within scope, correct the root cause (not the symptom), add
     a regression test that fails without the fix and passes with it, then continue through the tail
     of the `fix` workflow: test the affected paths, get an independent diff review from `reviewer`,
     and open a PR. Never merge.
   - **Diagnosis** — when the cause requires the owner's decision (a product trade-off, a risky
     architectural change, or work beyond this scope), stop and report a clear diagnosis: the root
     cause, the reproduction, and the options — without changing code.