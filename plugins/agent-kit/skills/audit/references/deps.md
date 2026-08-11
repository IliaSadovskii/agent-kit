# Lens: deps

Reference: the registries. Walks: the project's direct dependencies.

Use the ecosystem's own tooling rather than reasoning about versions — `composer outdated`,
`composer audit`, `npm outdated`, `npm audit`, `pip list --outdated`, whatever the stack has. Three
kinds of finding, in this order: a known vulnerability, a package past end of life, a major version
behind. Ignore patch drift; a project is not in trouble because something moved by 0.0.1.

**Relaying the tool's output is this lens's cheap path**, and it is what the owner could have run
themselves. So every finding carries the same kind of artefact the tests lens demands — a citation
that cannot be written without looking:

```
league/commonmark 2.4.1 → CVE-2025-… (XSS in inline HTML)
  used at        MarkdownRenderer.php:31, PostBody.php:18
  reachable      yes — post bodies are user text and pass through it
  upgrade to     2.6.0, no API change in the paths above

symfony/mailer 6.4 → end of life 2026-11
  used at        none — transitive through laravel/framework
  reachable      not directly; moves with the framework's own upgrade

filament/filament 3.2 → 4.0 available
  used at        src/Admin/** (14 panels)
  upgrade blocked by  4.0 requires Livewire 4; the project pins livewire/livewire ^3.5
```

Three fields, each of which forces a look: **where it is used** (call sites, or `none` for a
transitive dependency), **whether the vulnerable path is reachable here**, and **what the upgrade
costs or what blocks it**. A finding with no call sites and no reason is the tool's line copied
across.

Order by what the owner would act on first: a reachable vulnerability, then an unreachable one, then
end of life, then a major behind. Ignore patch drift entirely.

This lens walks packages rather than entries, so `walked` in its line of counters is every direct
dependency across every manifest — the ones that came out `covered` included. Patch drift is not a
verdict and not a row.

This lens needs no `docs/knowledge/` at all, so it is the one that works on a project the kit has
never described — and the only one that survives on a repository nobody has ever run `blueprint`
against.
