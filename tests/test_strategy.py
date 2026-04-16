# tests/test_strategy.py
#
# Tests for ChunkingStrategy subclasses and StrategySelector.
#
# Three layers:
#   1. Unit tests for describes() against synthetic XML fixtures
#   2. Unit tests for StrategySelector.select() — strategy selection logic
#   3. Integration tests against known corpus files in tests/data/
#
# NOTE on DivisionStrategy.xslt_stylesheet: that property is not yet
# implemented (raises NotImplementedError).  Tests here cover describes()
# only; xslt_stylesheet will be tested once the XSLT is written.
#
# NOTE on StrategySelector._STRATEGIES: the current implementation uses
# a class-level list of pre-constructed instances.  Tests use the public
# select() interface throughout; they do not depend on the internal
# representation.

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from mvp.document import TEIDocument
from mvp.strategy import (
    ChunkingStrategy,
    DivisionStrategy,
    MilestoneStrategy,
    StrategySelector,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"


def make_tei(body: str) -> str:
    """Return a minimal TEI document string with the given body content."""
    return textwrap.dedent(f"""\
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc>
              <titleStmt>
                <title>Test</title><author>Test</author>
              </titleStmt>
              <publicationStmt><p>Test</p></publicationStmt>
              <sourceDesc><p>Test</p></sourceDesc>
            </fileDesc>
          </teiHeader>
          <text xml:lang="grc">
            <body>
              {body}
            </body>
          </text>
        </TEI>
    """)


def write_doc(tmp_path: Path, body: str) -> TEIDocument:
    """Write a minimal TEI document with body and return a TEIDocument."""
    p = tmp_path / "test.xml"
    p.write_text(make_tei(body), encoding="utf-8")
    return TEIDocument.from_path(p)


# ---------------------------------------------------------------------------
# Body fragments for strategy detection
# ---------------------------------------------------------------------------

CARD_MILESTONES = """\
    <milestone unit="card" n="1"/>
    <p>text</p>
    <milestone unit="card" n="2"/>
"""

SECTION_MILESTONES = """\
    <milestone unit="section" n="1"/>
    <p>text</p>
    <milestone unit="section" n="2"/>
"""

LINE_MILESTONES = """\
    <milestone unit="line" n="1"/>
    <p>text</p>
    <milestone unit="line" n="2"/>
"""

# Division-based structure with no milestones — the pure Sophocles case
# (the real corpus file has both; this synthetic fixture isolates
# DivisionStrategy.describes() from MilestoneStrategy interference)
TEXTPART_DIVS_ONLY = """\
    <div type="edition" n="urn:cts:greekLit:tlg0011.tlg001.test">
      <div type="textpart" subtype="episode">
        <l n="1">line one</l>
        <l n="2">line two</l>
      </div>
      <div type="textpart" subtype="episode">
        <l n="3">line three</l>
      </div>
    </div>
"""

BOOK_DIVS_ONLY = """\
    <div type="edition" n="urn:cts:greekLit:tlg9999.tlg001.test">
      <div type="book">
        <p>book one</p>
      </div>
      <div type="book">
        <p>book two</p>
      </div>
    </div>
"""

FEATURELESS = "<p>plain prose, no milestones or structural divs</p>"


# ---------------------------------------------------------------------------
# Layer 1: Unit tests for describes() against synthetic fixtures
# ---------------------------------------------------------------------------

class TestMilestoneStrategyDescribes:

    def test_card_describes_card_doc(self, tmp_path):
        doc = write_doc(tmp_path, CARD_MILESTONES)
        assert MilestoneStrategy(unit="card").describes(doc)

    def test_card_does_not_describe_section_doc(self, tmp_path):
        doc = write_doc(tmp_path, SECTION_MILESTONES)
        assert not MilestoneStrategy(unit="card").describes(doc)

    def test_section_describes_section_doc(self, tmp_path):
        doc = write_doc(tmp_path, SECTION_MILESTONES)
        assert MilestoneStrategy(unit="section").describes(doc)

    def test_section_does_not_describe_card_doc(self, tmp_path):
        doc = write_doc(tmp_path, CARD_MILESTONES)
        assert not MilestoneStrategy(unit="section").describes(doc)

    def test_line_describes_line_doc(self, tmp_path):
        doc = write_doc(tmp_path, LINE_MILESTONES)
        assert MilestoneStrategy(unit="line").describes(doc)

    def test_milestone_strategy_does_not_describe_featureless(self, tmp_path):
        doc = write_doc(tmp_path, FEATURELESS)
        assert not MilestoneStrategy(unit="card").describes(doc)
        assert not MilestoneStrategy(unit="section").describes(doc)
        assert not MilestoneStrategy(unit="line").describes(doc)

    def test_chunk_unit_reflects_constructor_argument(self):
        assert MilestoneStrategy(unit="card").chunk_unit == "card"
        assert MilestoneStrategy(unit="section").chunk_unit == "section"
        assert MilestoneStrategy(unit="line").chunk_unit == "line"


class TestDivisionStrategyDescribes:

    def test_textpart_describes_textpart_doc(self, tmp_path):
        doc = write_doc(tmp_path, TEXTPART_DIVS_ONLY)
        assert DivisionStrategy(div_type="textpart").describes(doc)

    def test_book_describes_book_doc(self, tmp_path):
        doc = write_doc(tmp_path, BOOK_DIVS_ONLY)
        assert DivisionStrategy(div_type="book").describes(doc)

    def test_textpart_does_not_describe_book_doc(self, tmp_path):
        doc = write_doc(tmp_path, BOOK_DIVS_ONLY)
        assert not DivisionStrategy(div_type="textpart").describes(doc)

    def test_division_strategy_does_not_describe_featureless(self, tmp_path):
        doc = write_doc(tmp_path, FEATURELESS)
        assert not DivisionStrategy(div_type="textpart").describes(doc)

    def test_chunk_unit_reflects_constructor_argument(self):
        assert DivisionStrategy(div_type="textpart").chunk_unit == "textpart"
        assert DivisionStrategy(div_type="book").chunk_unit == "book"

    def test_xslt_stylesheet_raises_not_implemented(self, tmp_path):
        """DivisionStrategy.xslt_stylesheet is not yet implemented.

        This test documents that fact and will fail (intentionally) once
        the XSLT is written -- at which point it should be replaced with
        a positive assertion.
        """
        with pytest.raises(NotImplementedError):
            _ = DivisionStrategy(div_type="textpart").xslt_stylesheet


class TestChunkingStrategyIsAbstract:

    def test_cannot_instantiate_base_class(self):
        with pytest.raises(TypeError):
            ChunkingStrategy()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Layer 2: StrategySelector.select()
# ---------------------------------------------------------------------------

class TestStrategySelectorSelect:

    @pytest.fixture
    def selector(self):
        return StrategySelector()

    def test_selects_card_milestone_strategy(self, tmp_path, selector):
        doc = write_doc(tmp_path, CARD_MILESTONES)
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "card"

    def test_selects_section_milestone_strategy(self, tmp_path, selector):
        doc = write_doc(tmp_path, SECTION_MILESTONES)
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "section"

    def test_selects_line_milestone_strategy(self, tmp_path, selector):
        doc = write_doc(tmp_path, LINE_MILESTONES)
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "line"

    def test_raises_for_textpart_only_document(self, tmp_path, selector):
        """Division-only documents raise ValueError until DivisionStrategy XSLT
        is implemented.  StrategySelector detects the match but skips it because
        DivisionStrategy.xslt_stylesheet raises NotImplementedError; no other
        strategy matches, so select() raises ValueError and the document is
        SKIPPED (not failed) by BuildPipeline.

        When generate_chunks_div.xsl is implemented, update this test to assert
        that select() returns DivisionStrategy(textpart).
        """
        doc = write_doc(tmp_path, TEXTPART_DIVS_ONLY)
        with pytest.raises(ValueError, match="No chunking strategy"):
            selector.select(doc)

    def test_raises_for_book_div_only_document(self, tmp_path, selector):
        """Same as above for div[@type='book']-only documents."""
        doc = write_doc(tmp_path, BOOK_DIVS_ONLY)
        with pytest.raises(ValueError, match="No chunking strategy"):
            selector.select(doc)

    def test_raises_for_featureless_document(self, tmp_path, selector):
        doc = write_doc(tmp_path, FEATURELESS)
        with pytest.raises(ValueError, match="No chunking strategy"):
            selector.select(doc)

    def test_card_takes_precedence_over_section(self, tmp_path, selector):
        """A document with both card and section milestones gets card.

        This tests the ordering guarantee of _STRATEGIES: card is tried
        before section.
        """
        body = CARD_MILESTONES + "\n" + SECTION_MILESTONES
        doc = write_doc(tmp_path, body)
        strategy = selector.select(doc)
        assert strategy.chunk_unit == "card"

    def test_milestone_takes_precedence_over_division(self, tmp_path, selector):
        """A document with both card milestones and textpart divs gets card.

        This is the real Sophocles case: the corpus file has both, and
        milestone-based chunking is the correct (and current) selection.
        See wiki/Chunking-Design.org for the deferred work on proper
        hierarchical citation for this file.
        """
        body = CARD_MILESTONES + "\n" + TEXTPART_DIVS_ONLY
        doc = write_doc(tmp_path, body)
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "card"

    def test_returns_chunking_strategy_instance(self, tmp_path, selector):
        doc = write_doc(tmp_path, CARD_MILESTONES)
        strategy = selector.select(doc)
        assert isinstance(strategy, ChunkingStrategy)


# ---------------------------------------------------------------------------
# Layer 3: Integration tests against known corpus files
# ---------------------------------------------------------------------------

class TestStrategySelectorOnCorpusFixtures:
    """Strategy selection against the real TEI fixtures in tests/data/.

    These assertions reflect the *current* behavior of the selector
    against the actual corpus files, including known encoding quirks.
    """

    @pytest.fixture(scope="class")
    def selector(self):
        return StrategySelector()

    def test_seneca_agamemnon_gets_card(self, selector):
        """phi1017.phi007 -- Latin drama, card milestones."""
        doc = TEIDocument.from_path(
            DATA_DIR / "phi1017.phi007.perseus-lat2.xml"
        )
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "card"

    def test_sophocles_trachiniae_gets_card(self, selector):
        """tlg0011.tlg001 -- Greek drama.

        The file contains both card milestones and div[@type='textpart'].
        The selector currently returns MilestoneStrategy(card) because
        milestone detection precedes division detection in _STRATEGIES.

        This behaviour is intentional for the present milestone: the
        deferred Sophocles hierarchical citation work (see Chunking-Design.org)
        will require revisiting strategy selection for this file.
        """
        doc = TEIDocument.from_path(
            DATA_DIR / "tlg0011.tlg001.perseus-grc2.xml"
        )
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "card"

    def test_galen_skipped_until_division_xslt_implemented(self, selector):
        """tlg0057.tlg069 -- Greek prose, Galenus verbatim revised encoding.

        This file originates from the 1st1K project and was subsequently
        revised by the Galenus verbatim project, which added div[@type='textpart']
        structure (9 sections).  The milestone units present -- ed1page and
        ed2page -- are purely bibliographic apparatus tracking page breaks in
        two reference editions (Kuehn and likely Basel/Chartier).  They are
        not structural chunking boundaries.

        DivisionStrategy(textpart) describes this document, but its XSLT
        stylesheet is not yet implemented.  StrategySelector therefore raises
        ValueError and BuildPipeline SKIPs the file.

        When generate_chunks_div.xsl is implemented, update this test to assert
        that select() returns DivisionStrategy(textpart).
        """
        doc = TEIDocument.from_path(
            DATA_DIR / "tlg0057.tlg069.1st1K-grc1.xml"
        )
        with pytest.raises(ValueError, match="No chunking strategy"):
            selector.select(doc)
