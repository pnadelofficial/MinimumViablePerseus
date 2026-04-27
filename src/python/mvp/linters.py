# mvp/linters.py
#
#
import sys
from pathlib import Path
from lxml import etree

def parsed_xml(file_path: Path):
    # Use a parser that is very permissive
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    with file_path.open('rb') as f:
        tree = etree.parse(f, parser=parser)
    return tree


class BaseTEILinter:
    NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    XML_BASE = f"{{{NS['xml']}}}base"

    def __init__(self, tree) -> None:
        self.tree = tree
        self.root = self.tree.getroot()
        self._base_urn = None
        self._targets = None
        self.fixed_count = 0


    @property
    def base_urn(self) -> str:
        """Lazily extracts the work-level URN from the edition div."""
        if self._base_urn is None:
            # Look for the edition div which typically holds the URN in @n
            edition_div = self.root.xpath("//tei:div[@type='edition']", namespaces=NS)
            if edition_div:
                self._base_urn = edition_div[0].get('n', '').rstrip(':')
            else:
                self._base_urn = "urn:cts:greekLit:unknown"

        return self._base_urn


    def serialize(self, output_path:Path) -> None:
        """Writes the current tree to a file."""
        with output_path.open('wb') as f:
            self.tree.write(f, encoding='UTF-8', xml_declaration=True)



class HierarchicalLinter(BaseTEILinter):
    """Ideal for the Greek corpus using ancestor-based resolution."""

    @property
    def targets(self):
        """Target everything with an @n attribute."""
        if self._targets is None:
            self._targets = self.root.xpath("//tei:div[@n] | //tei:l[@n] | //tei:milestone[@n]",
                                  namespaces=self.NS)
        return self._targets


    def node_urn(self, node):
        nodes = node.xpath("ancestor-or-self::*[@n and not(contains(@n, 'urn:cts:'))]",
                           namespaces=self.NS)

        n_values = [n.get('n') for n in nodes]

        if not n_values:
            return f"{self.base_urn}:"
        return f"{self.base_urn}:{'.'.join(n_values)}"

    def update_node(self, node):
        pass

    def process(self, fix=False) -> None:
        for el in self.targets:
            # Skip the top-level edition div for the recursive n-join
            if 'urn:cts:' in (el.get('n') or ''):
                if fix: el.set(XML_BASE, f"{el.get('n')}:")
                continue

            expected: str = self.node_urn(el)
            actual: str = el.get(XML_BASE)

            if actual != expected and fix:
                el.set(XML_BASE, expected)
                self.fixed_count += 1



class RefsDeclLinter(BaseTEILinter):
    """
    A linter that uses the teiHeader's refsDecl to determine the URN.
    Perfect for milestone-heavy texts where hierarchies are flat or
    declared via cRefPatterns.

    Uses a state machine to track citations across milestones and divs.
    """

    def __init__(self, tree) -> None:
        super().__init__(tree)
        # 1. Extract and SORT the levels by structural depth
        self.citation_levels = self._parse_refs_decl()

        # Common TEI tag to Unit mapping
        self.tag_map = {'l': 'line', 'p': 'paragraph', 'div': 'textpart'}

        # 2. Map unit names to their hierarchical position
        # (e.g., 'book' -> 0, 'line' -> 1)

        # TODO is level_map still used?
        self.level_map = {name: i for i, name in enumerate(self.citation_levels)}

    def _parse_refs_decl(self):
        """Sorts units by hierarchical depth (capture group count)."""
        patterns = self.root.xpath("//tei:refsDecl[@n='CTS']/tei:cRefPattern", namespaces=NS)
        if not patterns:
            states = self.root.xpath("//tei:refState/@unit", namespaces=NS)
            return list(dict.fromkeys(p.lower() for p in states))

        levels = []
        for p in patterns:
            name = p.get('n').lower()
            depth = p.get('matchPattern').count('(')
            levels.append((name, depth))

        # Sort so 'book' (1 group) comes before 'line' (2 groups)
        levels.sort(key=lambda x: x[1])
        return [name for name, depth in levels]


    def _parse_refs_decl_old(self):
        """
        Parses patterns and sorts them by capture group count.
        Example: matchPattern '(\\w+).(\\w+)' (2 groups) follows '(\\w+)' (1 group).
        """
        patterns = self.root.xpath("//tei:refsDecl[@n='CTS']/tei:cRefPattern", namespaces=self.NS)

        if not patterns:
            # Fallback to refState if no CTS patterns are found
            states = self.root.xpath("//tei:refState/@unit", namespaces=self.NS)
            return list(dict.fromkeys(p.lower() for p in states))

        # Build list of (name, depth)
        levels_with_depth = []
        for p in patterns:
            name = p.get('n').lower()
            match = p.get('matchPattern')
            # The depth of a URN segment is the number of capture groups
            depth = match.count('(')
            levels_with_depth.append((name, depth))

        # Sort by depth ASCENDING: [('book', 1), ('line', 2)]
        levels_with_depth.sort(key=lambda x: x[1])
        return [name for name, depth in levels_with_depth]

    def process(self, fix=False) -> None:
        # Initialize state machine: { 'book': None, 'line': None }
        current_state = {level: None for level in self.citation_levels}
        self.fixed_count = 0

        for el in self.root.xpath("//tei:body//*", namespaces=NS):
            n_val = el.get('n')
            if not n_val: continue

            # Detect unit: check subtype/unit attrs, then tag name, then aliases
            tag = el.tag.split('}')[-1].lower()
            attr_unit = (el.get('subtype') or el.get('unit') or "").lower()

            # Find which level this element belongs to
            matched_level = None
            for level in self.citation_levels:
                if level == attr_unit or level == tag or level == self.tag_map.get(tag):
                    matched_level = level
                    break

            if matched_level:
                current_state[matched_level] = n_val
                # Reset all child levels (e.g., new book resets current line)
                reset = False
                for level in self.citation_levels:
                    if reset: current_state[level] = None
                    if level == matched_level: reset = True

                # Assemble URN
                active_values = []
                for level in self.citation_levels:
                    if current_state[level]:
                        active_values.append(current_state[level])
                    if level == matched_level: break

                expected = f"{self.base_urn}:{'.'.join(active_values)}"
                actual = el.get(XML_BASE)

                if actual != expected:
                    if fix:
                        el.set(XML_BASE, expected)
                        self.fixed_count += 1
                    else:
                        sys.stderr.write(f"MISMATCH: Expected {expected}, Got {actual}\n")
