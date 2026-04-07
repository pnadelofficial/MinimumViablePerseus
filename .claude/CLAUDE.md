# Perseus6 — Claude Code context

## What this project is

Perseus6 is a compiler-based reading environment for the Perseus Digital
Library, replacing Perseus 4 (the Hopper). It takes TEI-encoded XML texts and
produces static HTML pages, catalogs, citation tables, vocabulary aids, and
passage alignments — all navigable by web browser without JavaScript or a
back-end database.

## Design philosophy

**Minimal computing.** Perseus6 is data-forward: it generates artifacts that
others can serve or build on, rather than running services itself. Prefer
simplicity. Avoid external dependencies. Do not introduce JavaScript
requirements into the HTML output.

## Languages and tooling

- **Python 3.14.3** — primary implementation language
- **XSLT 3.0 / Saxon** — TEI-to-HTML transformation pipeline
- See `.claude/guidelines/python.md` for Python conventions used in this repo

## Before starting any coding task

Read all files in `.claude/guidelines/`.

## Before working on XSLT or TEI processing

Read `.claude/CHUNKING_DESIGN.md`. It covers the milestone chunking algorithm,
the XSLT import architecture, CTS URN annotation strategy, and deferred work
(especially the Sophocles citation hierarchy, which awaits philologist input).

## Repository layout

```
src/            Python packages
xslt/           XSLT stylesheets
  tei-to-html-base.xsl   importable base — extend via xsl:import
  generate_chunks.xsl    batch chunk generator
tests/          test suite and fixtures
.claude/        context documents for AI-assisted development
```

## Further reading

The project wiki contains standards, workflows, and best practices for
contributors.
