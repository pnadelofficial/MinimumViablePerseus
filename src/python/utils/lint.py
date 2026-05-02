import sys
import argparse
from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}

class TEIFilter:
    def __init__(self, input_stream):
        # Use a parser that preserves comments and processing instructions
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        self.tree = etree.parse(input_stream, parser)
        self.root = self.tree.getroot()

    def get_expected_urn(self, element):
        """Calculates the CTS URN based on the structural hierarchy."""
        parts = []
        # Find all ancestor divs with @n
        nodes = element.xpath('ancestor-or-self::tei:div[@n]', namespaces=NS)

        for node in nodes:
            n_val = node.get('n')
            if n_val.startswith('urn:cts:'):
                parts = [n_val.rstrip(':')]
            else:
                parts.append(n_val)

        if not parts: return None
        return f"{parts[0]}:{'.'.join(parts[1:])}" if len(parts) > 1 else f"{parts[0]}:"

    def process(self, fix=False):
        # Identify citable parts
        citable_divs = self.root.xpath('//tei:div[@n]', namespaces=NS)

        for div in citable_divs:
            expected = self.get_expected_urn(div)
            if not expected: continue

            if fix:
                # Force the attribute to the correct value
                div.set(f'{{{NS["xml"]}}}base', expected)
            else:
                # Just linting: check and report to stderr to keep stdout clean
                current = div.get(f'{{{NS["xml"]}}}base')
                if current != expected:
                    sys.stderr.write(f"MISMATCH: @n={div.get('n')} | Got: {current} | Expected: {expected}\n")

        # Write the resulting XML to stdout
        sys.stdout.buffer.write(etree.tostring(self.tree, encoding='UTF-8',
                                              xml_declaration=True, pretty_print=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A pipeline-friendly TEI URN filter.")
    parser.add_argument("file", nargs="?", type=argparse.FileType('rb'), default=sys.stdin.buffer)
    parser.add_argument("--fix", action="store_true", help="Repair @xml:base attributes in the output stream")
    args = parser.parse_args()

    # Process the stream
    tei_filter = TEIFilter(args.file)
    tei_filter.process(fix=args.fix)
