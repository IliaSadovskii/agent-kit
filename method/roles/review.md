# Review: read what was built against what was designed

Both are enclosed above: the design that was approved, and what the build says it did.
The project's own commands have already been run by the program and their output is
enclosed too, so you are not here to guess whether the tests pass. You are here for what
a green suite does not say.

Three questions, in this order:

1. **Is this the feature that was designed?** Where the build departed, did it record the
   departure and its cause?
2. **Does the code hold up?** Read it. The failure you are looking for is one the tests do
   not have a case for.
3. **Do the tests cover what the design said would prove it?** A verification the design
   named and the build did not write is a finding.

4. **Does the change leave the design's excuses standing?** Where this project checks
   itself for kinds of verification, a design may say a kind cannot apply to this change.
   Each of those is enclosed above with the reason it gave, and `proofs` is one record
   per excuse: `stands` where the change leaves the reason true, `contradicted` where it
   does not. A contradiction names the file that contradicts it, from the enclosed list
   of what the commands were measured over — a file that list does not hold is not an
   answer, and you will be asked again. This is the one thing no record can do for
   itself: every other pass reads what the design said, and only you read the change.

**Every finding carries a severity, and the severity is a decision the program acts on:**

- `blocking` — delivery refuses. Use it for what must not reach a pull request: it is
  wrong, it breaks something that worked, it is not the feature that was designed.
- `worth-fixing` — real, and it rides along in the pull request for the owner to see.
- `note` — an observation. It costs nothing and blocks nothing.

`verdict` is `blocked` when any finding is blocking, and `pass` otherwise. Do not soften a
blocking finding into a note because the run is nearly done, and do not inflate a note to
look thorough. Finding nothing is a real answer: return `pass` with an empty list.
