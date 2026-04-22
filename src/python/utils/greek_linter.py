import sys
import argparse
from lxml import etree

NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

class GreekTEILinter:
    def __init__(self, input_path):
        # Use a parser that is very permissive
        parser = etree.XMLParser(recover=True, remove_blank_text=False)
        self.tree = etree.parse(input_path, parser)
        self.root = self.tree.getroot()

        # Get Work URN
        edition_div = self.root.xpath("//tei:div[@type='edition']", namespaces=NS)
        if edition_div:
            self.base_urn = edition_div[0].get('n', '').rstrip(':')
        else:
            self.base_urn = "urn:cts:greekLit:unknown"

    def get_urn_for_node(self, node):
        # Collect @n from ancestors (excluding the URN-level div itself)
        # We look for tei:div or tei:l that have @n and aren't the work URN
        nodes = node.xpath("ancestor-or-self::*[@n and not(contains(@n, 'urn:cts:'))]", namespaces=NS)
        n_values = [n.get('n') for n in nodes]

        if not n_values:
            return f"{self.base_urn}:"
        return f"{self.base_urn}:{'.'.join(n_values)}"

    def process(self, output_path, fix=False):
        # Target everything with an @n attribute
        targets = self.root.xpath("//tei:div[@n] | //tei:l[@n] | //tei:milestone[@n]", namespaces=NS)
        XML_BASE = f"{{{NS['xml']}}}base"

        fixed_count = 0
        for el in targets:
            # Skip the top-level edition div for the recursive n-join
            if 'urn:cts:' in (el.get('n') or ''):
                # But ensure the top-level has the trailing colon base
                if fix: el.set(XML_BASE, f"{el.get('n')}:")
                continue

            expected = self.get_urn_for_node(el)
            actual = el.get(XML_BASE)

            if actual != expected:
                if fix:
                    el.set(XML_BASE, expected)
                    fixed_count += 1

        # Use a physical file write instead of stdout buffer to ensure flushing
        with open(output_path, 'wb') as f:
            self.tree.write(f, encoding='UTF-8', xml_declaration=True)

        sys.stderr.write(f"Done. Targets checked: {len(targets)}. Attributes fixed: {fixed_count}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    linter = GreekTEILinter(args.input)
    linter.process(args.output, fix=args.fix)
