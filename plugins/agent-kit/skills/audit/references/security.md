# Lens: security

Reference: two of them, and only one is generic. Walks: the actions that touch anything dangerous.

**Choosing the list is the first finding.** Go through every entry and mark it in or out, with the
reason in three words — untrusted input, permissions, money, files or processes, an outbound call, a
migration. Write the whole table, including the ones you excluded. A lens that quietly narrows its
own scope produces a clean report about five actions and says nothing about the thirty it never
looked at, and nobody can tell which happened.

`walked` in this file's counters is **every entry you marked**, in or out — the whole table, not the
subset you took. What you excluded is the half of this lens's completeness that nothing else can
see.

**Half of this lens is about rules no scanner can know.** Every entry's *must never* lines and its
actor's — "a developer never sees another developer's offers", "the author is not shown the report
count" — are this product's own authorization rules. **Every one of them appears in the report**,
with a citation or `none`; leaving out the ones you could not place is how a report ends up dense
and silent about the gap.

For each, **two citations, not one: where the check is written, and where it is invoked on the path
the actor takes.** A policy method can be correct and never called, a middleware can be defined and
missing from the route group — the same defect the scenarios lens exists for, in permissions. One
citation proves the rule was thought about; two prove it runs.

And a name is not a check. `PostPolicy::report` existing, or `auth` appearing in a route file, is the
code's claim about itself — the same substitution as crediting a test for its name. Read the body.

**The other half is the generic classes, and the tool exists.** Run `/security-review` over the
files the risky actions live in — you can invoke it, unlike the review commands only a person can
start — rather than reasoning about injection and deserialization from scratch. Point it at those
files, not at the repository.

Also check what the repository itself gives away: credentials in tracked files, a committed `.env`,
keys in fixtures or seeds. That is the one part of production readiness a repository can actually
show.

**Every finding carries where and whether**, the same artefact the deps lens produces:

```
author.view_my_posts — must never: the moderation trail must not reach the author
  enforced at   MyPosts.php:71 (select list), MyPostsPolicy.php:18
  holds for     attempt_no, reason codes, human flag
  does not for  body_snapshot, raw_response — both selected, both rendered at my-posts.blade.php:88
  reachable     yes, any author on their own rejected story
```

**The scanner returning nothing is not a verdict.** It knows the classes in its own catalogue and
nothing about this product's rules; say what it covered and keep the two halves visibly separate in
the report.

Walk every risky action, past the first finding: stopping early leaves the rest to be found one per
fix. And do not attempt an exploit — the citation is the evidence, and a lens that changes state to
prove a point has stopped being a lens.
