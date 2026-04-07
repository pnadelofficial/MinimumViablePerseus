from pathlib import Path
from lxml import etree
from abc import ABC, abstractmethod

# Uses the "Registry" Pattern to support a compiler-based approach to
# generating artifacts for Perseus 6. For example:
#
#  processor = TEIProcessor(TEIDocument("document.xml"))
#  processor.register_compiler("html", HTMLCompiler)
#  processor.run("html")

class TEIDocument:
    def __init__(self, xml_path: Path | str) -> None:
        pass

class TEICompiler(ABC):
    def __init__(self) -> None:
        pass


    @abstractmethod
    def compile(self, source_doc:TEIDocument, output_path:Path):
        """Must be implemented by subclasses"""
        pass


class HTMLCompiler(TEICompiler):
    def compile(self, source_doc:TEIDocument, output_path:Path):
        print(f"compiling {source_doc} to {output_path}")


class TEIProcessor:
    """The main coordinator."""
    def __init__(self, tei_doc: TEIDocument):
        self.tei_doc: TEIDocument = tei_doc
        self._registry: dict[str, TEICompiler] = {}

    def register_compiler(self, name:str, compiler_cls:TEICompiler):
        self._registry[name] = compiler_cls

    def run(self, target:str, output_path:Path):
        compiler: TEICompiler | None = self._registry.get(target)
        if compiler is not None:
            return compiler.compile(self.tei_doc, output_path = output_path)
        else:
            raise KeyError(f"compiler target {target} not registered.")
