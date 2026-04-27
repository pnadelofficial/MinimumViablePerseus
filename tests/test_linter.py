from pathlib import Path
import pytest

from mvp.linters import TEILinter

DATA_DIR: Path = Path(__file__).parent / "data"

@pytest.fixture
def test_doc():
    return DATA_DIR / "tlg0001.tlg001.perseus-grc2.xml"

def test_linter_init(test_doc):
    linter: TEILinter = TEILinter(test_doc)
    assert linter.tree is not None
    assert linter.root is not None
    assert linter.base_urn is "urn:cts:greekLit:tlg0001.tlg001.perseus-grc2"
