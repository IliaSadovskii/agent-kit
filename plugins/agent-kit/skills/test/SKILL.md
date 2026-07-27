---
name: test
description: Add or improve tests for a named target — a file, a module, or a behavior — then run the project's declared test and lint suite and report the result.
argument-hint: "[target]"
disable-model-invocation: true
---

# Test

"Cover this with tests" for a target the user names, without running a whole feature build.

Target: `$ARGUMENTS`

1. Delegate to the `agent-kit:tester` agent; its method lives there.
2. Run the project's declared test and lint suite and report the result.
3. If the target has a runnable surface and the tests are the only evidence it works, confirm it
   against the running app with `/verify`. Tests passing against an app that does not start is the
   gap this closes.

If a test exposes a real defect, report the defect rather than bending the test.
