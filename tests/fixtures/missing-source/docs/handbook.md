# Project handbook

The document the fixture contracts bind to. Its headings are what the section resolver walks.

## Boundaries

What must never enter this project.

### Third-party imports

The build installs nothing, so an import outside the standard library is a boundary violation.

## Verification

`true` is the whole suite here. A fixture must never name this repository's real one: that command
runs these tests, and the build would recurse.
