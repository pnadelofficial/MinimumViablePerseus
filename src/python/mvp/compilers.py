# mvp/compilers.py
#
# PageCompiler and CatalogCompiler.
#
# Compilers follow the command pattern: compile() returns None on
# success and raises CompilationError on failure.  All output is
# written to paths obtained from SiteMap.  Compilers are agents that
# produce artifacts; they are not functions that return values.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saxonche import PySaxonProcessor

from mvp.document import TEIDocument
from mvp.models import TEIMetadata
from mvp.strategy import ChunkingStrategy


@dataclass
class CompilationError(Exception):
    """Raised when a compiler fails to produce its artifact.

    Carries enough context for the BuildPipeline to log clearly
    and decide whether to continue or abort.
    """
    document: TEIDocument
    message: str
    cause: Exception | None = None

    def __str__(self) -> str:
        base = f"Compilation failed for {self.document.path}: {self.message}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


class PageCompiler:
    """Compiles a TEIDocument into a sequence of HTML chunk pages.

    Delegates document segmentation to a ChunkingStrategy and HTML
    generation to an XSLT 3.0 stylesheet via Saxon.

    Args:
        strategy:   ChunkingStrategy determining how the document is
                    divided into chunks.
        xslt_root:  Directory containing XSLT stylesheets.

    Usage::

        compiler = PageCompiler(strategy, xslt_root=Path("src/xslt"))
        compiler.compile(doc, output_path=site_map.chunk_dir(doc.metadata.urn))
    """

    def __init__(self, strategy: ChunkingStrategy,
                 xslt_root: Path) -> None:
        self._strategy = strategy
        self._xslt_root = Path(xslt_root)

    def compile(self, doc: TEIDocument, output_path: Path) -> None:
        """Compile doc into HTML chunk pages written to output_path.

        Args:
            doc:         The TEI source document to compile.
            output_path: Directory into which chunk HTML files and
                         index.json are written.  Created if absent.

        Raises:
            CompilationError: If the XSLT transformation fails for
                              any reason.
        """
        output_path.mkdir(parents=True, exist_ok=True)
        stylesheet = self._xslt_root / self._strategy.xslt_stylesheet

        try:
            with PySaxonProcessor(license=False) as proc:
                xslt = proc.new_xslt30_processor()
                transformer = xslt.compile_stylesheet(
                    stylesheet_file=str(stylesheet)
                )
                transformer.set_parameter(
                    "chunk-unit",
                    proc.make_string_value(self._strategy.chunk_unit)
                )
                transformer.set_parameter(
                    "output-dir",
                    proc.make_string_value(str(output_path))
                )
                transformer.transform_to_file(
                    source_file=str(doc.path),
                    output_file=str(output_path / "index.json")
                )
        except Exception as exc:
            raise CompilationError(
                document=doc,
                message="XSLT transformation failed",
                cause=exc,
            ) from exc


class CatalogCompiler:
    """Compiles a collection of TEIMetadata records into catalog HTML pages.

    Produces one catalog page per language grouping.  The catalog page
    lists all documents in that language with links to their first
    chunk pages.

    Args:
        template_path: Path to the HTML/Jinja2 catalog template.
                       (Templating engine TBD; placeholder for now.)

    Note: The catalog template and rendering engine are not yet
    specified.  This class is a stub that will be filled in once
    the template design is settled.
    """

    def __init__(self, template_path: Path) -> None:
        self._template_path = template_path

    def compile(self, entries: list[TEIMetadata],
                output_path: Path) -> None:
        """Compile catalog pages from entries, written to output_path.

        Args:
            entries:     Metadata records for all documents in the corpus.
            output_path: Directory into which catalog HTML files are written.

        Raises:
            CompilationError: If catalog page generation fails.
            NotImplementedError: Until the template engine is selected.
        """
        raise NotImplementedError(
            "CatalogCompiler is not yet implemented. "
            "Template engine selection is pending."
        )
