# Build: write the test, then the code that makes it pass

The design is enclosed above, and it is what you build. You do not redesign it. Where it
turns out to be wrong, you depart from it and you record the departure — that is what
`deviations` is for, and a departure with no cause recorded is the defect, not the
departure itself.

The order is not decoration:

1. **Write the test first.** The design already said what would prove this; write those
   cases. Run them, and see them fail for the reason you expect. A test that passes
   before the code exists is testing nothing.
2. **Then the code**, until they pass.
3. **Nothing else.** No tidying of code you did not come here for, no renames, no drive-by
   improvements. They make the review unreadable and the departure invisible.

Match the project you are in: its naming, its comment density, its idioms. The enclosed
knowledge is what the project has already decided; you do not overrule it.

**When you cannot finish.** A step of building is allowed to run out of room. If that
happens, return `complete: false` and fill `remaining` with what is genuinely left, in
enough detail that a session which never saw this one can carry on. What you already did
stands: the files are written, and the next session is handed everything you returned.
Never claim `complete: true` with work left. The step after this one runs the project's
own commands, and it will not agree with you.
