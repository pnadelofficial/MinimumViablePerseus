# document.py
#
# TEIDocument: parses and holds a single TEI source file.
#
# Metadata extraction is eager: TEIMetadata is populated on
# construction.  If performance over the full corpus proves
# problematic, lazy extraction can be introduced later.

from __future__ import annotations

from pathlib import Path

from lxml import etree

from models import TEIMetadata

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


class TEIDocument:
    """A parsed TEI source document with extracted metadata.

    Args:
        path: Absolute or relative path to the TEI XML file.

    Raises:
        FileNotFoundError: If the path does not exist.
        etree.XMLSyntaxError: If the file is not well-formed XML.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"TEI document not found: {self._path}")
        self._tree: etree._ElementTree = etree.parse(self._path)
        self._metadata: TEIMetadata = self._extract_metadata()

    @classmethod
    def from_path(cls, path: Path | str) -> TEIDocument:
        return cls(Path(path))

    @property
    def path(self) -> Path:
        return self._path

    @property
    def tree(self) -> etree._ElementTree:
        return self._tree

    @property
    def metadata(self) -> TEIMetadata:
        return self._metadata

    # ------------------------------------------------------------------
    # Private

    def _extract_metadata(self) -> TEIMetadata:
        root = self._tree.getroot()

        urn = self._extract_urn(root)
        title = self._extract_title(root)
        author = self._extract_author(root)
        language = self._extract_language(root)
        text_type = self._extract_text_type(root)
        chunk_unit = self._extract_chunk_unit(root)

        return TEIMetadata(
            urn=urn,
            title=title,
            author=author,
            language=language,
            text_type=text_type,
            chunk_unit=chunk_unit,
            source_path=self._path,
        )

    def _extract_urn(self, root: etree._Element) -> str:
        # CTS URN lives on the edition div or, in some encodings, on
        # the outermost div[@type='edition'].  Fall back to the
        # refsDecl/@n which carries the base URN in CTS-aware files.
        edition = root.find(".//tei:div[@type='edition']", NS)
        if edition is not None:
            urn = edition.get("n", "")
            if urn:
                return urn

        refs_decl = root.find(".//tei:refsDecl[@n='CTS']", NS)
        if refs_decl is not None:
            urn = refs_decl.get("n", "")
            if urn:
                return urn

        return ""

    def _extract_title(self, root: etree._Element) -> str:
        title_el = root.find(".//tei:titleStmt/tei:title", NS)
        if title_el is not None and title_el.text:
            return title_el.text.strip()
        return ""

    def _extract_author(self, root: etree._Element) -> str:
        author_el = root.find(".//tei:titleStmt/tei:author", NS)
        if author_el is not None and author_el.text:
            return author_el.text.strip()
        return ""

    def _extract_language(self, root: etree._Element) -> str:
        # xml:lang on the text element is the most reliable signal.
        text_el = root.find("tei:text", NS)
        if text_el is not None:
            lang = text_el.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            if lang:
                return lang
        # Fall back to langUsage
        lang_el = root.find(".//tei:langUsage/tei:language", NS)
        if lang_el is not None:
            return lang_el.get("ident", "")
        return ""

    def _extract_text_type(self, root: etree._Element) -> str:
        # Heuristic: presence of <l> elements suggests verse;
        # presence of <sp> suggests drama; otherwise prose.
        # This is intentionally simple and can be refined.
        text_el = root.find("tei:text", NS)
        if text_el is None:
            return "prose"
        if text_el.find(".//tei:sp", NS) is not None:
            return "drama"
        if text_el.find(".//tei:l", NS) is not None:
            return "verse"
        return "prose"

    def _extract_chunk_unit(self, root: etree._Element) -> str:
        # Read the first milestone/@unit found in the text body.
        # If none, fall back to 'section' as a safe default.
        ms = root.find(".//tei:text//tei:milestone", NS)
        if ms is not None:
            return ms.get("unit", "section")
        return "section"
