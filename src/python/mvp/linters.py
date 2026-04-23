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
        tree = etree.parse(file_path, parser=parser)
    return tree


class BaseTEILinter:
    NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    XML_BASE = f"{{{NS['xml']}}}base"

    def __init__(self, tree) -> None:
        # Use a parser that is very permissive
        self.tree = tree
        self.root = self.tree.getroot()
        self._base_urn = None
        self._targets = None
        self.fixed_count = 0


    @property
    def base_urn(self) -> str:
        if self._base_urn is None:
            edition_div = self.root.xpath("//tei:div[@type='edition']", namespaces=NS)
            if edition_div:
                self._base_urn = edition_div[0].get('n', '').rstrip(':')
            else:
                self._base_urn = "urn:cts:greekLit:unknown"

        return self._base_urn



    def serialize(self, output_path:Path) -> None:
        with output_path.open('wb') as f:
            self.tree.write(f, encoding='UTF-8', xml_declaration=True)



class HierarchicalLinter(BaseTEILinter):
    """Ideal for the Greek corpus, which is cleaner."""

    @property
    def targets(self):
        """Target everything with an @n attribute."""
        if self._targets is None:
            self._targets = self.root.xpath("//tei:div[@n] | //tei:l[@n] | //tei:milestone[@n]",
                                  namespaces=NS)
        return self._targets


    def node_urn(self, node):
        nodes = node.xpath("ancestor-or-self::*[@n and not(contains(@n, 'urn:cts:'))]",
                           namespaces=NS)
        n_values = [n.get('n') for n in nodes]
        if not n_values:
            return f"{self.base_urn}:"
        return f"{self.base_urn}:{'.'.join(n_values)}"

    def update_node(self, node):
        pass

    def process(self, fix=False) -> None:
        self.fixed_count = 0
        for el in self.targets:
            # Skip the top-level edition div for the recursive n-join
            if 'urn:cts:' in (el.get('n') or ''):
                if fix: el.set(XML_BASE, f"{el.get('n')}:")
                continue

            expected: str = self.node_urn(el)
            actual: str = el.get(XML_BASE)

            if actual != expected:
                if fix:
                    el.set(XML_BASE, expected)
                    self.fixed_count += 1

class RefsDeclLinterMine(BaseTEILinter):
    """for milestone-heavy or non-nested texts.

    Uses state-machine logic based on CRefPattern."""

    def __init__(self, tree):
        super().__init__(tree)
        self.state_tracker: dict = {}

    def _parse_refs_decl(self):
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
        # TODO implement
        pass


class RefsDeclLinter(BaseTEILinter):
    """
    A linter that uses the teiHeader's refsDecl to determine the URN.
    Perfect for milestone-heavy texts where hierarchies are flat or
    declared via cRefPatterns.
    """

    def __init__(self, tree) -> None:
        super().__init__(tree)
        # 1. Extract and SORT the levels by structural depth
        self.citation_levels = self._parse_refs_decl()
        # 2. Map unit names to their hierarchical position
        # (e.g., 'book' -> 0, 'line' -> 1)
        self.level_map = {name: i for i, name in enumerate(self.citation_levels)}

    def _parse_refs_decl(self):
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

        # We must walk the body to find state transitions (milestones/divs/lines)
        for el in self.root.xpath("//tei:body//*", namespaces=self.NS):
            # Resolve the 'unit' name. Handle the 'l' vs 'line' alias.
            tag_name = el.tag.split('}')[-1].lower()
            unit = (el.get('subtype') or el.get('unit') or tag_name).lower()

            # Alias common TEI tags to their standard citation units
            if unit == 'l' and 'line' in current_state:
                unit = 'line'

            n_val = el.get('n')

            # Update the state if this element represents a citation level
            if unit in current_state and n_val:
                current_state[unit] = n_val

                # Assemble URN: only include segments up to the current level
                active_values = []
                for level in self.citation_levels:
                    if current_state[level]:
                        active_values.append(current_state[level])
                    if level == unit:
                        break

                # Use self.base_urn (the property) to avoid 'None'
                expected = f"{self.base_urn}:{'.'.join(active_values)}"
                actual = el.get(self.XML_BASE)

                if actual != expected:
                    if fix:
                        el.set(self.XML_BASE, expected)
                        self.fixed_count += 1
                    else:
                        # Log to stderr to separate diagnostics from XML output
                        import sys
                        sys.stderr.write(f"MISMATCH [{unit} n={n_val}]: Expected {expected}, Got {actual}\n")
