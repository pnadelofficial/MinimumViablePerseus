import sys
import argparse
from lxml import etree

# TEI Namespace
NS = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}

class TEILinter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = etree.parse(file_path)
        self.root = self.tree.getroot()

    def get_urn_parts(self, element):
        """Recursively build the URN based on @n attributes of ancestors."""
        parts = []
        # Find all ancestor divs and the current element if it's a div
        nodes = element.xpath('ancestor-or-self::tei:div[@n]', namespaces=NS)

        for node in nodes:
            n_val = node.get('n')
            # If @n is a full URN, it's our starting point
            if n_val.startswith('urn:cts:'):
                parts = [n_val.rstrip(':')]
            else:
                parts.append(n_val)

        if not parts:
            return None

        # The work URN is index 0, the rest are joined by dots
        if len(parts) == 1:
            return parts[0] + ":"
        return f"{parts[0]}:{'.'.join(parts[1:])}"

    def lint(self, fix=False):
        # We look for all divs that are part of the citation hierarchy
        citable_divs = self.root.xpath('//tei:div[@n]', namespaces=NS)
        changes_made = 0

        for div in citable_divs:
            current_base = div.get(f'{{{NS["xml"]}}}base')
            expected_base = self.get_urn_parts(div)

            if not expected_base:
                continue

            # Check for redundancy or errors
            if current_base != expected_base:
                status = "[FIXED]" if fix else "[ERROR]"
                print(f"{status} Node {div.get('n')}:")
                print(f"  Current:  {current_base}")
                print(f"  Expected: {expected_base}")

                if fix:
                    div.set(f'{{{NS["xml"]}}}base', expected_base)
                    changes_made += 1
            else:
                # Optional: Flag if the base is valid but technically redundant
                # because the parent already established the prefix.
                pass

        if fix and changes_made > 0:
            self.tree.write(self.file_path, encoding='UTF-8', xml_declaration=True)
            print(f"\nSuccessfully updated {changes_made} attributes in {self.file_path}")
        elif not fix:
            print("\nLinting complete. Run with --fix to apply changes.")

def main():
    parser = argparse.ArgumentParser(description="Lint and Repair TEI @xml:base for CTS URNs")
    parser.add_argument("file", help="Path to the TEI XML file")
    parser.add_argument("--fix", action="store_true", help="Apply repairs to the file")
    args = parser.parse_args()

    linter = TEILinter(args.file)
    linter.lint(fix=args.fix)

if __name__ == "__main__":
    main()
