# Lens: scenarios

Reference: `docs/knowledge/scenarios.md`. Walks: every scenario.

Tests prove the parts; scenarios prove the joins. A path where every action works and the step
between two of them does not is invisible to any test written at the level of one action, and it is
the defect a person notices first.

**Two passes, and the first needs no code.**

1. **Chain the steps against the entries.** Step N sets a status, step N+1 lists its preconditions —
   a mismatch is a finding without opening anything. The same for surfaces: if step N+1 is reached
   from a screen, some earlier step must lead to that screen. The entries already carry all of this.
2. **Trace the path through the code**, step by step: the implementation of each step exists, and
   the surface the next step needs is reachable from where the previous one leaves the actor.

Run the end-to-end tests first if the project has any, and report per scenario what they returned.
Where there are none, trace instead — an earlier draft of this lens reported "nothing to run" and
stopped, which on most projects means an empty audit and a defect left in place.

**The cheap path here is a verdict with no trace behind it** — "the path looks fine". So each
scenario is written as its steps, each step citing the code that carries it, and the break named at
the step where it happens:

```
Nino tells a story about a neighbour
  1. author.submit_post     SubmitPostAction.php:24 · route web.php:57 · from screen.new_post   ok
  2. author.edit_post_body  EditPostBodyAction.php:18                                           ok
  3. validator.check_post   ClaimPostForValidationAction.php:31                                 ok
  4. → published            PublishPostAction.php:40, sets post.published                       ok
  5. guest.browse_feed      Feed.php:66                                                         BREAKS
     the card links to the story only when the body is over 500 characters
     (post-card.blade.php:34), and this story is shorter
  verdict: breaks at step 5 — reachable in the entries, not reachable in the application
```

Each step carries **two citations, not one**: what implements it, and **what gets the actor to it
from the previous step** — the route, the link, the redirect, the button. The second is the one that
matters: an action can exist, be correct, be tested, and be unreachable from where the person
actually is, which is the whole class of defect this lens exists for.

**Citations come from the code, never from the entries.** An entry saying a step is reached from a
screen is the claim under test; quoting it back is the same substitution as crediting a test because
of its name. If the link is not in a template, a route or a controller, it is not there.

**Walk the whole scenario, past a break.** When a step breaks, assume it fixed and keep going: the
remaining steps may hold two more, and finding them a week later — one per fix — is the slow way to
learn what the owner wanted in one pass.

**Where end-to-end tests exist, name which test covers which scenario and check it walks the same
steps.** A green suite is not evidence that this path is the one covered; that is the test's own
claim about itself again.

**Every scenario needs one, and a scenario with none is a finding of its own** — separate from
whether it walks, and reported per scenario as `no end-to-end test`. Tracing proves the path exists
in the code today; it says nothing about tomorrow, and this lens runs when somebody remembers to
run it. A scenario is exactly what a test cannot be talked out of: it goes through the queue, the
worker, the schedule and the browser at once, which is where a green suite over green units breaks.

Where a step cannot honestly live in a test — a paid call to a real third party, something only a
person can judge — the test covers the rest and the exception goes to `docs/technical_debt.md`,
naming the step and why. What must not happen is a scenario quietly counted as proven because its
trace came out clean.

Three verdicts, and no fourth may be invented: a scenario whose every step is cited and reachable
`walks`; one with a break is `breaks at step N` (all of them, listed); one with a step whose
implementation you could not find is `unfollowable` — which is not `walks`. The end-to-end test is
recorded beside the verdict, as a citation or as `no end-to-end test`: a scenario can walk today and
have nothing standing guard over it tomorrow, and those are two different facts about it.

**Every scenario and every step appears in the map.** The file's own numbering says how many steps a
scenario has, so a shorter trace is a defect in the report, countable without reading it.

**It does not write the end-to-end tests it wants.** Tracing answers what is broken now; the tests
answer whether it breaks again, and building them means fixtures, seeding and often a harness the
project does not have — an owner's decision and a `ship` run, not a side effect of an audit. So the
work list opens with the harness when there is none, marked as the owner's decision, and carries one
item per scenario after it. Whoever writes those tests then knows which ones should fail first.
