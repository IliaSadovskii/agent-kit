# Dependencies: what this project declares, against what it imports

Two lists are enclosed above and they were measured by the program, not by you: every
dependency the manifest declares, and every top-level module this project imports that is
neither the standard library's nor its own. You are standing in an unpacked copy of one
commit. **You write no file, you open no branch, you change nothing.** There is no
repository around you, so there is nothing to change even by accident.

Your work is the join between those two lists — and only that. A distribution is rarely
imported under its own name: `PyYAML` arrives as `yaml`, `python-dateutil` as `dateutil`,
`beautifulsoup4` as `bs4`. No arithmetic can know that, and that is why somebody is being
asked at all. Everything either side of the join is counted by the program.

Do this, in this order:

1. **Give every declared dependency a row.** All of them, including the ones that are
   plainly in use. A row that is missing is refused by name, and the cheap way to look
   thorough is to answer for the interesting third.

2. **Name the modules each one puts on the import path** — `imports`. Not a guess at what
   it does: the module names an `import` line would use. Read the enclosed list of measured
   modules, and read the code where it helps. This is the field your verdict is checked
   against.

3. **Give each row one of three verdicts.**
   - `imported` — at least one of the modules you named is in the measured list. Nothing
     more is needed: the arithmetic is the whole answer.
   - `used-without-importing` — nothing imports it and this project still needs it: a
     pytest plugin, a linter, a formatter, a build backend, a command somebody runs. **Say
     why in a line.** The program cannot check this one, so it is printed in the report as
     a claim standing on your word, and a lens that called every hard row a plugin will
     read as exactly that.
   - `unused` — nothing in this project needs it. **Say why in a line**: what you looked at
     and what it would mean to take it out.

4. **Answer for every measured module no row claims.** A module in the enclosed list that
   appears in nobody's `imports` goes in `undeclared`, with a line saying what it is. That
   is a package this project uses and does not declare: it works on the machine it was
   written on and breaks on a clean install.

**Do not invent.** A row may only name a dependency the enclosed manifest declares or a
module the enclosed list holds. There is nothing to find beyond those two lists, and a
finding pointing outside them is refused before anybody reads it.

**Nothing found is an answer.** A project where every dependency is imported and every
import is declared has every row `imported` and an empty `undeclared`, and that is the
whole of a correct answer. Manufacturing a finding out of a project that has none is worse
than the audit not having been run — it is the one failure this lens is measured against.

**Be careful in one direction.** A dependency that looks unused because its only importer
is a test, a script or an example is not unused. Look before you say it: you are in the
whole commit, not in the part of it somebody thought was the code.
