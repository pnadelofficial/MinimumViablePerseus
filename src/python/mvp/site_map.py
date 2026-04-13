# mvp/site_map.py
#
# SiteMap: owns the output path and URL scheme for all compiled artifacts.
#
# No other object constructs output paths.  Everything goes through
# SiteMap so the URL scheme can be changed in one place.

from __future__ import annotations

from pathlib import Path


class SiteMap:
    """Output path and URL scheme for all Perseus6 compiled artifacts.

    All path construction is centralised here.  Pipeline stages obtain
    output paths from SiteMap rather than constructing them directly.

    The URL scheme is:
        /{language}/{textgroup}/{work}/{version}/    — chunk pages
        /catalog/{language}.html                    — catalog pages
        /{language}/{textgroup}/{work}/{version}/index.json  — manifests

    URN components are mapped as follows:
        urn:cts:{namespace}:{textgroup}.{work}.{version}:{passage}
        → {namespace}/{textgroup}/{work}/{version}/

    Args:
        output_root: Root directory for all compiled output.
    """

    def __init__(self, output_root: Path | str) -> None:
        self._root = Path(output_root)

    @property
    def root(self) -> Path:
        return self._root

    def chunk_dir(self, urn: str) -> Path:
        """Return the output directory for chunk pages of a document.

        Creates parent directories as needed.
        """
        path = self._root / self._urn_to_path(urn)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def chunk_path(self, urn: str, chunk_id: str) -> Path:
        """Return the output path for a single chunk HTML file."""
        return self.chunk_dir(urn) / f"chunk_{chunk_id}.html"

    def manifest_path(self, urn: str) -> Path:
        """Return the output path for a document's index.json manifest."""
        return self.chunk_dir(urn) / "index.json"

    def catalog_path(self, language: str) -> Path:
        """Return the output path for a language catalog page."""
        catalog_dir = self._root / "catalog"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        return catalog_dir / f"{language}.html"

    # ------------------------------------------------------------------
    # Private

    def _urn_to_path(self, urn: str) -> Path:
        """Convert a CTS URN to a relative filesystem path.

        urn:cts:greekLit:tlg0011.tlg001.perseus-grc2
        → greekLit/tlg0011/tlg001/perseus-grc2

        Returns a single-segment path for URNs that don't conform to
        the expected structure.
        """
        # Strip 'urn:cts:' prefix and passage citation if present
        bare = urn.removeprefix("urn:cts:")
        bare = bare.split(":")[0]           # drop passage component

        parts = bare.split(".")
        if len(parts) >= 3:
            namespace_and_rest = bare.split(":", 1)
            if len(namespace_and_rest) == 2:
                namespace = namespace_and_rest[0]
                work_parts = namespace_and_rest[1].split(".")
                return Path(namespace, *work_parts)

        # Fallback: use the bare URN as a single directory name
        return Path(bare.replace(":", "_").replace(".", "_"))
