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

## Repository layout

```
src/
  python/         Python build pipeline and compiler framework
    compilers/    TEICompiler abstract base class and HTMLCompiler
    build_site.py
    main.py
  perseus6/       XML processing utilities; drama XSLT stub
  xslt/           XSLT stylesheets
    chunker_core.xsl     importable base — extend via xsl:import
    generate_chunks.xsl  batch chunk generator
data/             TEI source texts (git submodule: canonical-greekLit)
schemas/          TEI ODD schemas (perseus_base.odd, tei_bare.odd)
tests/            test suite and fixtures
.claude/          context documents for AI-assisted development
```

## Further reading

The project wiki is available at `wiki/` (git submodule).  It contains
standards, workflows, best practices, and design documents including the
chunking and CTS URN architecture.
