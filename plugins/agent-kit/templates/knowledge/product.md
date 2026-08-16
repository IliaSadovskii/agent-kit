<!--
Product — what this is and what it is deliberately not.

The first section is the owner's own description, kept close to their words. It is the anchor
every later slot is checked against: if it mentions something no entry covers, that is a gap.
Do not replace it with a tidier summary — the throwaway details are exactly what later becomes
"you mentioned agencies, but no actor is recorded".

The parts are what the interview is shaped by, and they are recorded because a part nobody wrote
down is invisible to the next session and to `epic`. Five to ten is what a product usually comes to,
not a limit: a narrow tool has one or two, a large one has more.

Each part carries a mark, and the mark stays English like `key:` and `state:` do: `walked: <date>`
when the owner told you this part, `derived` when it was read out of code and documents and never
confirmed. The check counts them, `blueprint` offers the walk for the derived ones, and `epic`
reports the split at its gate — which is the difference between a description somebody agreed to
and one nobody has read.

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

## Parts

<!-- One line each: the name, what it covers in a few words, and the mark — `walked: <date>` when
     the owner told you this part, `derived` when it was read out of the code and never confirmed.
     The names are in the project's language; the mark is not, because the check counts it.

     - вход и аккаунт — регистрация, вход, выход — `walked: 2026-08-09`
     - задание — чат урока целиком — `walked: 2026-08-09`
     - карта тем — прогресс по узлам — `derived`
-->

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

<!-- agent-kit:mvp-bounds -->
## MVP bounds

**In:** <!-- explicit list -->

**Out:** <!-- explicit list -->
