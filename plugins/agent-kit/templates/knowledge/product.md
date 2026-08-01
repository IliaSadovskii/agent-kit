<!--
Product — what this is and what it is deliberately not.

The first section is the owner's own description, kept close to their words. It is the anchor
every later slot is checked against: if it mentions something no entry covers, that is a gap.
Do not replace it with a tidier summary — the throwaway details are exactly what later becomes
"you mentioned agencies, but no actor is recorded".

Application type decides which surface slots apply: screens for a UI, endpoints for an API,
commands for a CLI. Name it here; the surface files reference it.

MVP bounds are settled last, after the scenarios, and they are two explicit lists. "And so on"
is not a bound.

Done when: an implementer reading this file knows what to build, for whom, and what not to
build without asking.
-->

# Product

## How the owner describes it

<!-- The owner's own telling. Lightly cleaned, not rewritten. -->

## What it is for

<!-- One or two sentences. Every later decision is judged against this. -->

## What it deliberately does not do

<!-- One line each. This is what stops an autonomous run helpfully building the wrong thing. -->

## Application type

<!-- web app + API, monolith, mobile, CLI, library, API-only, data pipeline, landing.
     Say which surface slots apply and which are not_applicable. -->

## Environment and constraints

<!-- Where it runs, and the constraints that shape the build: offline, permissions, latency,
     volumes, platform rules. Only what is real for this product. -->

## MVP bounds

**In:** <!-- explicit list -->

**Out:** <!-- explicit list -->
