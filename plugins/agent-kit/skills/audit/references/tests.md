# Lens: tests

Reference: the entries. Walks: every entry in scope.

Run the project's declared suite once first, from `project.yml` → `commands.test`, so the report
knows whether the existing tests even pass. Report the result; never fix it.

Then, per entry, per line — what changes, what the initiator sees, what others see, what can go
wrong — answer four questions about the test that claims to prove it, in order, stopping at the
first "no":

1. **Is there one at all?** No match anywhere is a finding, and needs no reading.
2. **Is it about this line?** Read it. A hit inside fixture data or an assertion about neighbouring
   behavior is not coverage.
3. **Is the assertion strong enough to observe what the line claims?** A line saying the buyer is
   notified is not proven by `assertStatus(200)`.
4. **Does it cover the conditions the line names?** Three ways to go wrong and one of them asserted
   is a partial, and the partials are worth more than the absences — they are the ones that look
   covered.

**A test marked unmet is not coverage, and not a gap either.** The mark is the comment
`agent-kit:unmet <entry key>` beside the test; a line whose only test carries it gets its own
marker, `unmet`, with the citation. The
promise is written down and proven absent — the work it asks for is a product change, not a test,
so filing it among the gaps would send the next run to write a test that already exists.

**Covered is claimed with a citation, never with a word.** Every line credited as covered names the
test and the line number that proves it; a line with nothing to cite is a gap. A test's *name* is
not a citation — `it('shows the link to readers and not to the author')` is the test's claim about
itself, and the line it is credited for may be a different claim entirely.

```
author.report_post
  what changes         → ReportButtonTest.php:57
  initiator sees       → ReportButtonTest.php:64
  others see           → ReportTest.php:85
  can go wrong
    repeat report      → ReportButtonTest.php:140
    report count hidden from the author → none
```

The citation is what makes the verdict checkable in ten seconds and impossible to produce without
opening the file. An entry summarised as "covered" with no map behind it can only be believed, and
this lens exists so that nothing has to be.

**The map carries every line of the entry, and a line with nothing to cite is written `none`.**
Past `unmet` above, one further marker, `n/a`, is allowed **only where the entry's line itself
states that nothing happens** — "what changes: nothing", "others see: nothing". Anywhere else it is
`none` with extra steps: a marker that needs neither a citation nor an admission is the next cheap
path, and it looks like a verdict.
Leaving it out instead is the cheap way to satisfy a citation rule: what remains looks dense and
proves nothing about what is absent. Each distinct claim inside a line gets its own row — "can go
wrong" listing three ways is three rows, not one.

**A citation whose proof runs through a double says so, in the same line:** `(stand-in: the payment
gateway)`. Not a marker and not a gap — the test is coverage, and what it covers is the fake. The
lens is the only pass that opens these files one line at a time, so it is the only place the list
can come from; without it the question is asked once, at the end of a whole run, by a session
reading nothing but run files. Measured on one such run, every proof it had went through a fake
gateway, a fake sign-in and a fake clock, and the real model was never called once in thirty hours.

**An entry with a single `none` is not covered.** It belongs among the gaps, however much of it is
cited. Covered means covered whole; anything else is a partial dressed as a verdict. An entry whose
only shortfall is `unmet` is not covered either, but its work list is a separate one — those lines
are the product's, and they are reported together so the owner sees in one place everything this
project promises and does not do.

The map's completeness is arithmetic, not trust: the file's header declares its `fields:`, so a map
with fewer rows than the entry has lines is a defect in the report rather than an absence of
problems. The same arithmetic one level up is the file's own line of counters, which the check adds
up: `walked` here is every entry that has a line to prove — an actor has none, and saying so in the
header is what keeps the number from looking short.

What this lens does **not** judge: how the test is built — brittle, slow, duplicated, sitting at the
wrong seam. That has a different reference, the project's own testing rules, and belongs to the
conventions lens. Nor does it invent conditions the entry never named: a missing edge case that no line mentions
is a hole in the description, and `blueprint` closes it.
