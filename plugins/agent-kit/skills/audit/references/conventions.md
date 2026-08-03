# Lens: conventions

Reference: `docs/knowledge/stack.md`. Walks: every rule written there.

The other five lenses check what the product does. This one checks **how it is built, against the
project's own words about how it should be** — the stances per area, the library map, the testing
rules, the list of what this project does not do.

**The rules are the list, so write them out and walk them one at a time.** A rule with nothing
violating it gets a row saying where you looked; a rule you could not check gets `unjudged` and the
reason. Reading the file and reporting three violations tells the owner nothing about the other
fifteen rules.

Four kinds of finding, and the first is the most valuable:

- **Hand-rolled where the library map names a package.** The project already depends on something
  that covers this, and someone wrote it again. Cite both — the code and the map line it ignores.
- **A stance broken.** The area's stance says one thing, the code does another. Cite the stance and
  the place.
- **Something on the "we do not do this" list, done.**
- **How a test is built** — brittle, slow, duplicated, asserting the implementation instead of the
  behavior, sitting at a lower seam than the project's rules ask for. The tests lens answers whether
  a test proves the entry; this one answers whether it was worth writing that way. Neither invents a
  rule the project never wrote down.

**A rule the project did not write is not a finding.** Your opinion about layering, naming or file
size is not this reference, and smuggling it in as a violation is how a lens becomes an argument.
Where the code is plainly worse than the rules require but no rule covers it, that is one line in
"also noticed" and a candidate for `blueprint` to record — not a violation of something unwritten.

**Say how thin the reference is.** This lens is worth exactly what `stack.md` is worth: on a project
whose stances were derived and confirmed, it finds real divergence; on one with three vague lines it
finds little, and that is a fact about `stack.md` rather than about the code. State which of the two
you were working with, in the file, before the findings.
