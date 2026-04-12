# strategy.py
#
# ChunkingStrategy and StrategySelector.
#
# A ChunkingStrategy encapsulates the logic for determining how a TEI
# document should be divided into navigable chunks.  Compilers receive
# a strategy as a collaborator; they do not contain chunking logic.
#
# StrategySelector inspects a TEIDocument and returns the appropriate
# strategy.  It reads refsDecl as a hint but also inspects the actual
# document structure, since encoding inconsistencies in the Perseus
# corpus mean that refsDecl cannot always be trusted.

from __future__ import annotations

from abc import ABC, abstractmethod

from document import TEIDocument

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


class ChunkingStrategy(ABC):
    """Abstract base for document segmentation strategies."""

    @abstractmethod
    def describes(self, doc: TEIDocument) -> bool:
        """Return True if this strategy is applicable to doc."""
        ...

    @property
    @abstractmethod
    def xslt_stylesheet(self) -> str:
        """Filename of the XSLT stylesheet that implements this strategy."""
        ...

    @property
    @abstractmethod
    def chunk_unit(self) -> str:
        """The unit value passed to the XSLT stylesheet."""
        ...


class MilestoneStrategy(ChunkingStrategy):
    """Chunk at <milestone unit='{unit}'/> elements.

    Applies to texts that use TEI milestone elements to mark
    page or section boundaries that cut across the element hierarchy.
    This is the most common case in the Perseus corpus.
    """

    def __init__(self, unit: str = "card") -> None:
        self._unit = unit

    @property
    def chunk_unit(self) -> str:
        return self._unit

    @property
    def xslt_stylesheet(self) -> str:
        return "generate_chunks.xsl"

    def describes(self, doc: TEIDocument) -> bool:
        root = doc.tree.getroot()
        ms = root.find(f".//tei:text//tei:milestone[@unit='{self._unit}']", NS)
        return ms is not None


class DivisionStrategy(ChunkingStrategy):
    """Chunk at <div type='{div_type}'> elements.

    Applies to texts structured as nested divisions rather than
    milestone-delimited sections.  The Sophocles case (nested
    div[@type='textpart'] elements) is the primary known instance.
    """

    def __init__(self, div_type: str = "textpart") -> None:
        self._div_type = div_type

    @property
    def chunk_unit(self) -> str:
        return self._div_type

    @property
    def xslt_stylesheet(self) -> str:
        # TODO: implement division-based XSLT stylesheet
        raise NotImplementedError(
            "DivisionStrategy XSLT stylesheet not yet implemented"
        )

    def describes(self, doc: TEIDocument) -> bool:
        root = doc.tree.getroot()
        div = root.find(
            f".//tei:text//tei:div[@type='{self._div_type}']", NS
        )
        return div is not None


class StrategySelector:
    """Selects a ChunkingStrategy for a TEIDocument.

    Inspects the document structure to determine the appropriate
    strategy.  The order of preference reflects the current state
    of the corpus: milestone-based chunking is the common case.

    Per-document overrides are not yet implemented.  When they are,
    a configuration file mapping URNs to strategy names would be
    consulted first.
    """

    # Strategies tried in order; first match wins.
    _STRATEGIES: list[ChunkingStrategy] = [
        MilestoneStrategy(unit="card"),
        MilestoneStrategy(unit="section"),
        MilestoneStrategy(unit="line"),
        DivisionStrategy(div_type="textpart"),
        DivisionStrategy(div_type="book"),
    ]

    def select(self, doc: TEIDocument) -> ChunkingStrategy:
        """Return the first strategy that describes doc.

        Raises:
            ValueError: If no strategy matches.
        """
        for strategy in self._STRATEGIES:
            if strategy.describes(doc):
                return strategy
        raise ValueError(
            f"No chunking strategy found for {doc.path} "
            f"(URN: {doc.metadata.urn})"
        )
