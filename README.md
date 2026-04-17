# Perseus6

Perseus 6 will be a reading environment that replaces Perseus 4 (the
Hopper). Our first project is implementing Minimum Viable Perseus (MVP),
a website that reproduces the Hopper's critical functionality.

## Background

The Perseus Digital Library is a large collection of texts encoded in
TEI XML. These encoded texts are Open Source and available on
[GitHub](https://github.com/PerseusDL). Perseus has always provided
tools for discovering resources and reading them in a richly
hypertextual environment. Perseus6 is an implementation of those tools.

## Installation

### Prerequisites

- **Python 3.12+**
- **Java 11+** (required by Saxon for XSLT 3.0 transformations)
- **[PDM](https://pdm-project.org/)** — Python dependency manager

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/PerseusDLCode/mvp.git
   cd mvp
   ```

2. Install Python dependencies (including Saxon):

   ```bash
   pdm install
   ```

3. Clone the corpus data (optional — required for building the site):

   ```bash
   git clone https://github.com/PerseusDL/canonical-latinLit.git data/canonical-latinLit
   git clone https://github.com/PerseusDL/canonical-greekLit.git  data/canonical-greekLit
   ```

### Running the test suite

```bash
pdm run test
```

Slow integration tests (require Saxon) are excluded by default. To run them:

```bash
pdm run test -m slow
```

## Building the site

Compile one or more corpora into a static site:

```bash
# Single corpus
pdm run python src/tools/run_build.py data/canonical-latinLit/data /tmp/out

# Both corpora in one pass → unified catalog
pdm run python src/tools/run_build.py \
    data/canonical-latinLit/data \
    data/canonical-greekLit/data \
    /tmp/out
```

Rebuild the catalog from existing compiled output (no recompilation):

```bash
pdm run python src/tools/run_build.py --catalog-only /tmp/out
```

Serve the result locally:

```bash
cd /tmp/out && python -m http.server 8000
# open http://localhost:8000
```

## Documentation

See the wiki associated with this repository for standards, workflows,
and best practices used in this project. Also see documentation in the
docs/ directory of this repository.
