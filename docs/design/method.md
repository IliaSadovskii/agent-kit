# How a command gets written, and how it gets trustworthy

Written 2026-08-04, after `blueprint`, `ship` and `audit`. Eleven corrections were paid for with
live runs on a real project; none of them came from re-reading the text. `fix`, `sprint` and `mvp`
should not pay for them again.

## The loop

Write it, run it on a real project, **check its claims by hand**, correct, run again. Every
correction the kit has was found this way. A command that has never run is a hypothesis, however
carefully argued — the first `audit` run cost 1.7M and produced seventeen verdicts that turned out to
be guesses.

Measure each run with `scripts/measure.py <project>` and verify a sample of what it claims — pick two
or three findings and try to disprove them. Two of the four false verdicts we found were caught by
one grep each.

## Instructions lose to the cheap path

The most expensive lesson, learned three times on the same lens.

For any step there is a cheaper way to produce output that looks the same. Telling the agent not to
take it does not work: the instruction is followed in letter and the substance is skipped, because
the cheap path genuinely produces plausible output.

- "Read the file, don't stop at a grep hit" → it stopped at a grep hit.
- Written again, more sharply → it indexed the *names* of tests and judged from those.
- Only a **format** worked: a covered line must name the test and line number proving it. A citation
  cannot be written without opening the file, so the cheap path stopped being available rather than
  being discouraged.

> Name the cheapest way to produce plausible output, then demand an artefact that path cannot
> produce.

## And demand the artefact be complete

The format closed one path and opened the next one down: cite what can be cited, quietly omit the
rest. A dense map of citations reads as thorough and says nothing about what is missing from it.

> Every unit walked gets a row — including the clean ones and the ones that could not be judged.
> Anything with no evidence is written `none`, never left out.

Completeness must be countable without reading: the entry declares its fields, the scenario declares
its steps, `stack.md` declares its rules. A short map is then a defect in the report, found by
arithmetic.

## Fix the verdicts, or a new one gets invented

Given `covered` and `gaps`, a run invented `n/a` for lines whose entry says nothing happens. Honest
there, and an escape hatch everywhere else: a marker that needs neither evidence nor an admission
reads as a verdict. State the set, state the one exception, and say a fourth may not be invented.

## Uncertainty resolves toward the finding

The two mistakes are not symmetrical. A finding that turns out to be fine costs ten seconds of
reading. A gap recorded as clean costs a bug nobody will look for again. So doubt goes to the gap
column, and the report says so out loud.

For the same reason: no verification pass. A second agent re-checking the first doubles the price
against a ten-second mistake, and stacking checks is what once produced thirty findings and then
twenty more.

## Extrapolate before the next first run

From the fourth lens onward, corrections were carried across instead of re-earned. Before running a
new command, walk the list above and ask what each one looks like here. Three of four applied to the
security lens unchanged; the fourth — "exists is not reachable", learned on scenarios — became
"a policy can be correct and never called", which is how it found a live session surviving an account
takeover.

The general shapes worth translating each time:

- a name is not the thing (a test's name, a policy's name, a method called `withRelations`);
- exists is not reachable (an action nothing links to, a check nothing invokes, an eager load the
  view does not use);
- one consumer is not all of them;
- stopping at the first finding leaves the rest to be found one per fix;
- a tool's silence is scope, not safety.

## Prose in a command is re-read on every step

A file costs its size multiplied by the steps left in the run. `audit` reached 466 lines, of which
301 described six lenses, and a single-lens run carried five it would never use. Reference material
belongs in files loaded when needed — `skills/audit/references/<lens>.md`,
`templates/knowledge/<slot>.md` — leaving the command with what every run needs.

## Say what the command cannot see

Every report ends with its own blind spot: what the reference does not cover, what was judged by
reading rather than running, what was excluded and why. A report that reads as exhaustive cannot be
used, because the reader has to re-check everything or nothing.
