#!/usr/bin/env python3
"""Perseus6 static site builder.

Usage:
    python src/tools/run_build.py <corpus_root> <output_root> [--xslt-root DIR]

Example:
    python src/tools/run_build.py data/canonical-latinLit/data /tmp/perseus6-out

Serve the result:
    cd /tmp/perseus6-out && python -m http.server 8000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running directly without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from mvp.corpus import Corpus
from mvp.pipeline import BuildPipeline
from mvp.site_map import SiteMap

_DEFAULT_XSLT_ROOT = Path(__file__).parent.parent / "xslt"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perseus6 static site builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "corpus_root",
        type=Path,
        help="Root directory of the TEI corpus to compile",
    )
    parser.add_argument(
        "output_root",
        type=Path,
        help="Root directory for compiled HTML output",
    )
    parser.add_argument(
        "--xslt-root",
        type=Path,
        default=_DEFAULT_XSLT_ROOT,
        help=f"Directory containing XSLT stylesheets (default: {_DEFAULT_XSLT_ROOT})",
    )
    args = parser.parse_args()

    # The canonical-*Lit repositories store their TEI files under a
    # data/ subdirectory (e.g. data/canonical-latinLit/data/).  If the
    # supplied corpus_root contains a data/ subdirectory, use it instead.
    corpus_path = args.corpus_root
    data_subdir = corpus_path / "data"
    if data_subdir.is_dir():
        corpus_path = data_subdir

    print(f"Corpus:  {corpus_path}")
    print(f"Output:  {args.output_root}")
    print(f"XSLT:    {args.xslt_root}")
    print()

    pipeline = BuildPipeline(
        corpus=Corpus(corpus_path),
        site_map=SiteMap(args.output_root),
        xslt_root=args.xslt_root,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
