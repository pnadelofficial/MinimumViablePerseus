# tests/test_compilers.py
#
# Tests for CompilationError, PageCompiler, and CatalogCompiler.
#
# Testing strategy:
#   - CompilationError: plain dataclass/exception behaviour, no mocking needed.
#   - PageCompiler: unit tests mock saxonche entirely.  We test that the
#     Python logic (directory creation, parameter passing, error wrapping)
#     is correct without invoking Saxon.  An integration test against real
#     Saxon + XSLT belongs here too but is deferred until the XSLT suite
#     is written; see the TODO at the bottom of this file.
#   - CatalogCompiler: stubbed; xfail documents the NotImplementedError.
#
# NOTE on PageCompiler design: PageCompiler constructs its PySaxonProcessor
# internally via a context manager.  We patch 'mvp.compilers.PySaxonProcessor'
# to intercept it.  If the import path changes, the patch target must change
# too.

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mvp.compilers import CatalogCompiler, CompilationError, PageCompiler
from mvp.models import TEIMetadata
from mvp.strategy import MilestoneStrategy

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
SENECA_PATH = DATA_DIR / "phi1017.phi007.perseus-lat2.xml"


@pytest.fixture
def seneca_doc():
    from mvp.document import TEIDocument
    return TEIDocument.from_path(SENECA_PATH)


@pytest.fixture
def card_strategy():
    return MilestoneStrategy(unit="card")


@pytest.fixture
def mock_saxon():
    """Patch PySaxonProcessor with a MagicMock and yield the mock class.

    The mock is configured so that the context-manager protocol works:
        with PySaxonProcessor(license=False) as proc: ...
    yields a mock proc object whose method calls are also mocks.
    """
    with patch("mvp.compilers.PySaxonProcessor") as mock_cls:
        mock_proc = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_proc)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_cls, mock_proc


# ---------------------------------------------------------------------------
# CompilationError
# ---------------------------------------------------------------------------

class TestCompilationError:

    def test_is_exception(self, seneca_doc):
        err = CompilationError(document=seneca_doc, message="something went wrong")
        assert isinstance(err, Exception)

    def test_str_without_cause(self, seneca_doc):
        err = CompilationError(document=seneca_doc, message="something went wrong")
        s = str(err)
        assert "something went wrong" in s
        assert str(seneca_doc.path) in s

    def test_str_with_cause(self, seneca_doc):
        cause = ValueError("underlying problem")
        err = CompilationError(
            document=seneca_doc,
            message="something went wrong",
            cause=cause,
        )
        s = str(err)
        assert "something went wrong" in s
        assert "underlying problem" in s

    def test_cause_defaults_to_none(self, seneca_doc):
        err = CompilationError(document=seneca_doc, message="oops")
        assert err.cause is None

    def test_can_be_raised_and_caught(self, seneca_doc):
        with pytest.raises(CompilationError) as exc_info:
            raise CompilationError(document=seneca_doc, message="test raise")
        assert exc_info.value.message == "test raise"


# ---------------------------------------------------------------------------
# PageCompiler
# ---------------------------------------------------------------------------

class TestPageCompilerConstruction:

    def test_accepts_strategy_and_xslt_root(self, tmp_path, card_strategy):
        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)
        assert compiler is not None

    def test_xslt_root_coerced_to_path(self, tmp_path, card_strategy):
        compiler = PageCompiler(strategy=card_strategy, xslt_root=str(tmp_path))
        # No public accessor, but construction must not raise
        assert compiler is not None


class TestPageCompilerCompile:

    def test_creates_output_directory(self, tmp_path, seneca_doc,
                                      card_strategy, mock_saxon):
        output_path = tmp_path / "output" / "deep" / "path"
        assert not output_path.exists()

        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)
        compiler.compile(seneca_doc, output_path)

        assert output_path.is_dir()

    def test_invokes_saxon_with_correct_stylesheet(self, tmp_path, seneca_doc,
                                                   card_strategy, mock_saxon):
        mock_cls, mock_proc = mock_saxon
        xslt_root = tmp_path / "xslt"
        xslt_root.mkdir()

        compiler = PageCompiler(strategy=card_strategy, xslt_root=xslt_root)
        compiler.compile(seneca_doc, tmp_path / "out")

        mock_proc.new_xslt30_processor().compile_stylesheet.assert_called_once_with(
            stylesheet_file=str(xslt_root / card_strategy.xslt_stylesheet)
        )

    def test_sets_chunk_unit_parameter(self, tmp_path, seneca_doc,
                                       card_strategy, mock_saxon):
        mock_cls, mock_proc = mock_saxon
        transformer = mock_proc.new_xslt30_processor().compile_stylesheet()

        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)
        compiler.compile(seneca_doc, tmp_path / "out")

        calls = [str(c) for c in transformer.set_parameter.call_args_list]
        assert any("chunk-unit" in c for c in calls)

    def test_sets_output_dir_parameter(self, tmp_path, seneca_doc,
                                       card_strategy, mock_saxon):
        mock_cls, mock_proc = mock_saxon
        transformer = mock_proc.new_xslt30_processor().compile_stylesheet()
        output_path = tmp_path / "out"

        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)
        compiler.compile(seneca_doc, output_path)

        calls = [str(c) for c in transformer.set_parameter.call_args_list]
        assert any("output-dir" in c for c in calls)

    def test_returns_none_on_success(self, tmp_path, seneca_doc,
                                     card_strategy, mock_saxon):
        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)
        result = compiler.compile(seneca_doc, tmp_path / "out")
        assert result is None

    def test_wraps_saxon_exception_as_compilation_error(self, tmp_path,
                                                         seneca_doc,
                                                         card_strategy,
                                                         mock_saxon):
        mock_cls, mock_proc = mock_saxon
        mock_proc.new_xslt30_processor().compile_stylesheet(
        ).transform_to_file.side_effect = RuntimeError("Saxon exploded")

        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)

        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(seneca_doc, tmp_path / "out")

        assert exc_info.value.document is seneca_doc
        assert isinstance(exc_info.value.cause, RuntimeError)

    def test_compilation_error_message_mentions_xslt(self, tmp_path,
                                                      seneca_doc,
                                                      card_strategy,
                                                      mock_saxon):
        mock_cls, mock_proc = mock_saxon
        mock_proc.new_xslt30_processor().compile_stylesheet(
        ).transform_to_file.side_effect = RuntimeError("oops")

        compiler = PageCompiler(strategy=card_strategy, xslt_root=tmp_path)

        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(seneca_doc, tmp_path / "out")

        assert "XSLT" in exc_info.value.message


# ---------------------------------------------------------------------------
# CatalogCompiler
# ---------------------------------------------------------------------------

class TestCatalogCompiler:

    @pytest.mark.xfail(
        reason="CatalogCompiler.compile() is not yet implemented; "
               "template engine selection is pending.",
        raises=NotImplementedError,
        strict=True,
    )
    def test_compile_raises_not_implemented(self, tmp_path):
        """CatalogCompiler.compile() is a stub.

        This test documents that fact.  strict=True ensures the suite
        fails loudly if compile() is implemented without this test being
        updated to assert correct behaviour.
        """
        compiler = CatalogCompiler(template_path=tmp_path / "template.html")
        compiler.compile(entries=[], output_path=tmp_path / "catalog")

    def test_construction_does_not_raise(self, tmp_path):
        """CatalogCompiler can be constructed even though compile() is stubbed."""
        compiler = CatalogCompiler(template_path=tmp_path / "template.html")
        assert compiler is not None


# ---------------------------------------------------------------------------
# TODO: PageCompiler integration tests
#
# An integration test suite should be added here once the XSLT stylesheets
# are stable.  Each test should:
#   1. Run PageCompiler.compile() against a real corpus fixture using the
#      real Saxon processor and the real XSLT.
#   2. Assert that the expected HTML chunk files and index.json were created.
#   3. Spot-check the content of at least one chunk file.
#
# These tests will be slow and should be marked @pytest.mark.slow so they
# can be excluded from the fast unit-test run:
#
#   @pytest.mark.slow
#   def test_seneca_produces_expected_chunks(tmp_path):
#       ...
#
# Add 'slow' to the markers list in pyproject.toml when implementing.
# ---------------------------------------------------------------------------
