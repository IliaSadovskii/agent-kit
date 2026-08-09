<!--
Stack — what this is built with, and the rules the build follows.

Derived, not interviewed: versions come from the dependency manifests, the per-area decisions
from the code and from research into what this framework's current major actually recommends.
The owner corrects the draft and adds the rules only they know.

Every rule is one line with its reason. A rule without a reason gets ignored or misapplied.

The library map is the highest-value section: it is what stops a run hand-rolling something the
ecosystem already solved.

The application type lives in product.md; do not restate it. The test, lint and run commands
live in .agent-kit/project.yml; do not restate them either.

Done when a run can build inside this without asking: it knows the versions to target, the
patterns to follow, where to look for a ready-made answer, and what this project does not do.
-->

# Stack

## Versions

<!-- Languages, framework, package manager, the majors actually installed. From the manifests. -->

## Principles

<!-- The owner's own rules, one line each with the reason. -->

## Decisions per area

<!-- Layering, validation, error handling, background work, data access. One line each, with
     why. Derived from the code and from research; corrected by the owner. -->

## Library map

<!-- What this ecosystem's ready-made answer is, per problem. Name the package and what it
     covers, so a run reaches for it instead of writing its own. -->

## Testing

<!-- Which layers this project tests, at which seams, and where a test has to be proven able to
     fail. State the bar, so runs neither skip it nor gold-plate it.

     One line here is not derived like the rest: WHAT RUNS THE SCENARIOS END TO END. The layers,
     the seams and the bar all come from the code and the manifests; a harness nobody has built
     yet comes from nowhere, so it has to be asked. Name the tool and where it runs — or write
     that there is none and the scenarios are proved by hand. Both are legitimate; the absence of
     either is not. `mvp` finishes only when every scenario inside the bounds passes, so a run
     that finds this silent reads it as "not done here" and builds a whole product before anyone
     notices. -->

## What we do not do

<!-- Anti-patterns for this project specifically. -->
