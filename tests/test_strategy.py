# tests/test_strategy.py
#
# Tests for ChunkingStrategy subclasses and StrategySelector.
#
# Three layers:
#   1. Unit tests for describes() against synthetic XML fixtures
#   2. Unit tests for StrategySelector.select() — strategy selection logic
#   3. Integration tests against known corpus files in tests/data/
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


def make_tei_with_hint(body: str, hint_unit: str) -> str:
    """Return a minimal TEI document with a <refState n='chunk'> hint."""
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
            <encodingDesc>
              <refsDecl>
                <refState unit="work"/>
                <refState unit="{hint_unit}" n="chunk"/>
              </refsDecl>
            </encodingDesc>
          </teiHeader>
          <text xml:lang="lat">
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


def write_doc_with_hint(tmp_path: Path, body: str,
                        hint_unit: str) -> TEIDocument:
    """Write a TEI document with a refState chunk hint."""
    p = tmp_path / "test_hint.xml"
    p.write_text(make_tei_with_hint(body, hint_unit), encoding="utf-8")
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

CHAPTER_DIVS_ONLY = """\
    <div type="edition" n="urn:cts:latinLit:phi2331.phi013.test">
      <div type="textpart" subtype="chapter" n="1">
        <p><milestone unit="section" n="1"/>first section of chapter one.</p>
      </div>
      <div type="textpart" subtype="chapter" n="2">
        <p><milestone unit="section" n="1"/>first section of chapter two.</p>
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

    def test_chunk_unit_reflects_div_type_when_no_subtype(self):
        assert DivisionStrategy(div_type="textpart").chunk_unit == "textpart"
        assert DivisionStrategy(div_type="book").chunk_unit == "book"

    def test_chunk_unit_reflects_subtype_when_given(self):
        assert DivisionStrategy(div_type="textpart",
                                subtype="chapter").chunk_unit == "chapter"
        assert DivisionStrategy(div_type="textpart",
                                subtype="scene").chunk_unit == "scene"

    def test_subtype_filter_matches_chapter_divs(self, tmp_path):
        doc = write_doc(tmp_path, CHAPTER_DIVS_ONLY)
        assert DivisionStrategy(div_type="textpart",
                                subtype="chapter").describes(doc)

    def test_subtype_filter_does_not_match_wrong_subtype(self, tmp_path):
        doc = write_doc(tmp_path, CHAPTER_DIVS_ONLY)
        assert not DivisionStrategy(div_type="textpart",
                                    subtype="scene").describes(doc)

    def test_xslt_stylesheet_returns_generate_div_chunks(self):
        assert DivisionStrategy(div_type="textpart").xslt_stylesheet == \
            "generate_div_chunks.xsl"


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

    def test_selects_division_strategy_for_textpart_only_document(
            self, tmp_path, selector):
        doc = write_doc(tmp_path, TEXTPART_DIVS_ONLY)
        strategy = selector.select(doc)
        assert isinstance(strategy, DivisionStrategy)
        assert strategy.chunk_unit == "textpart"

    def test_selects_division_strategy_for_book_div_only_document(
            self, tmp_path, selector):
        doc = write_doc(tmp_path, BOOK_DIVS_ONLY)
        strategy = selector.select(doc)
        assert isinstance(strategy, DivisionStrategy)
        assert strategy.chunk_unit == "book"

    def test_hint_overrides_section_milestone(self, tmp_path, selector):
        """A chapter hint causes DivisionStrategy to win over section milestones."""
        doc = write_doc_with_hint(tmp_path, CHAPTER_DIVS_ONLY, hint_unit="chapter")
        strategy = selector.select(doc)
        assert isinstance(strategy, DivisionStrategy)
        assert strategy.chunk_unit == "chapter"

    def test_hint_card_selects_card_milestone(self, tmp_path, selector):
        """A card hint selects MilestoneStrategy(card) when card milestones exist."""
        doc = write_doc_with_hint(tmp_path, CARD_MILESTONES, hint_unit="card")
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "card"

    def test_no_hint_falls_back_to_ordered_list(self, tmp_path, selector):
        """Without a hint, section milestones win over chapter divs."""
        doc = write_doc(tmp_path, CHAPTER_DIVS_ONLY)
        strategy = selector.select(doc)
        assert isinstance(strategy, MilestoneStrategy)
        assert strategy.chunk_unit == "section"

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

    def test_galen_gets_division_strategy(self, selector):
        """tlg0057.tlg069 -- Greek prose, Galenus verbatim revised encoding.

        This file has div[@type='textpart'] structure (9 sections).  The
        milestone units present -- ed1page and ed2page -- are bibliographic
        apparatus, not chunking boundaries.  DivisionStrategy(textpart) is
        the correct selection now that generate_div_chunks.xsl is implemented.
        """
        doc = TEIDocument.from_path(
            DATA_DIR / "tlg0057.tlg069.1st1K-grc1.xml"
        )
        strategy = selector.select(doc)
        assert isinstance(strategy, DivisionStrategy)
        assert strategy.chunk_unit == "textpart"

    def test_caracallus_gets_chapter_division_strategy(self, selector):
        """phi2331.phi013 -- SHA Antoninus Caracallus.

        Has <refState unit='chapter' n='chunk'> in the header and
        div[@type='textpart'][@subtype='chapter'] in the body.  The hint
        should steer selection to DivisionStrategy(textpart, subtype=chapter).
        """
        doc = TEIDocument.from_path(
            DATA_DIR / "phi2331.phi013.perseus-lat2.xml"
        )
        strategy = selector.select(doc)
        assert isinstance(strategy, DivisionStrategy)
        assert strategy.chunk_unit == "chapter"

    def test_caracallus_chunk_hint(self, selector):
        doc = TEIDocument.from_path(
            DATA_DIR / "phi2331.phi013.perseus-lat2.xml"
        )
        assert doc.chunk_hint() == "chapter"

    def test_seneca_has_no_chunk_hint(self, selector):
        doc = TEIDocument.from_path(
            DATA_DIR / "phi1017.phi007.perseus-lat2.xml"
        )
        assert doc.chunk_hint() is None
