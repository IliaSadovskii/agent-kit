# Test workflow

`test` surfaces the kit's testing capability as a directly-invocable entry: "cover this with tests"
outside the full `ship` pipeline. Follow `.agent-kit/engine.md` and the active provider adapter.

## When to use

When you want to add or improve tests for a target the user names — a file, module, or behavior —
without running a whole feature build.

## Behavior

Delegate to the canonical `tester` role; do not duplicate its method here. The role reads the named
target and its existing tests, identifies uncovered behavior (edge cases, boundary values,
validation, authorization, empty/invalid input, failure paths, regressions in neighboring code),
and adds missing tests using the project's existing frameworks and conventions. It writes only tests
and the minimally necessary fixtures; it does not change business code.

Run the project's declared test and lint suite and report the result. Never weaken or delete a valid
assertion to obtain green output — if a test exposes a real defect, report the defect rather than
bending the test.