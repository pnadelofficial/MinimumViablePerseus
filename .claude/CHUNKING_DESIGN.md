# TEI Milestone Chunking — Design Document

This document captures the design decisions made while developing the
milestone-based chunking tools for TEI-encoded classical texts.  It is
intended as context for a fresh session in any repository that has adopted
these tools.  The full development history (including XQuery explorations
that preceded the Python and XSLT implementations) lives in the scratchpad
repo `https://github.com/PerseusDLCode/tei-tagger`.

---

## The problem: overlapping hierarchies

TEI milestone elements such as

```xml
<milestone unit="card" n="57"/>
```

represent physical boundaries — index cards, manuscript pages, editorial
sections — that cut across the XML element hierarchy.  A dramatic speech
(`<sp>`) may straddle a card boundary, with the milestone appearing inside it:

```xml
<sp who="#thyestis">
  <l n="54">some text</l>
  <l n="55">more text</l>
  <l n="56">last line before boundary</l>
</sp>
<milestone unit="card" n="57"/>
<sp who="#chorus">
  <l n="57">first line of next card</l>
  ...
```

No XPath axis can select "all content between two milestones" in a single
step, because milestones are siblings of the elements they divide, not
wrappers around them.

---

## The algorithm (language-independent)

Three steps, identical in the Python and XSLT implementations:

### Step 1 — Find top-level elements between the milestones

Select all elements `>> ms1` and `<< ms2` (document-order comparison),
then filter to those with **no ancestor also in that set**.  This prevents
returning `<note>` inside a `<p>` when `<p>` itself is already in the result.

```xpath
let $hits := //element()[. >> $ms1][. << $ms2]
let $top  := $hits[not(ancestor::* intersect $hits)]
```

### Step 2 — Truncate straddling elements

Any element in `$top` that **contains `ms2` as a descendant** straddles the
boundary.  Copy it, but discard everything at or after `ms2`.

- **Python** (`copy_before(element, stop)`): recursive deep-copy; breaks out
  of the child loop as soon as it encounters `stop` or a subtree containing it.
- **XSLT** (`local:before-stop(node, stop)`): a boolean function checked
  inline in every template — no pre-copy step needed (single-pass).

`local:before-stop` definition:

```xslt
<xsl:function name="local:before-stop" as="xs:boolean">
  <xsl:param name="node" as="node()"/>
  <xsl:param name="stop" as="node()?"/>
  <!-- empty $stop means last chunk — no boundary to enforce -->
  <xsl:sequence select="
    empty($stop)
    or (not($node is $stop) and not($node &gt;&gt; $stop))
  "/>
</xsl:function>
```

### Step 3 — Convert TEI → HTML

Map element names, add CTS annotations, suppress `<pb>` and `<milestone>`.

**Note on Python tail rescue:** lxml models text following a child element as
a `.tail` property on that element.  Suppressing `<pb>` with `return None` in
`to_html()` would silently drop any text in `pb.tail`.  The Python code
explicitly rescues it.  This problem does not arise in XSLT because XPath
models that same text as an independent text-node sibling, handled naturally
by the `text()` template.

---

## XSLT architecture

Two files, designed for `xsl:import`-based extensibility.

### `tei-to-html-base.xsl` — importable base

Contains all element templates in **`chunk` mode** plus three helper
functions.  All templates receive `$stop` and `$base-urn` as **tunnel
parameters**.

| Symbol | Purpose |
|--------|---------|
| `local:before-stop($node, $stop)` | Document-order gate (see above) |
| `local:extract-base-urn($root)` | Reads `div[@type='edition']/@n` |
| `local:chunk-cts-range($top, $stop, $base-urn)` | Computes range URN for a chunk |

Element → HTML mapping in the base:

| TEI | HTML |
|-----|------|
| `tei:sp` | `<div class="speech" data-who="...">` |
| `tei:speaker` | `<b class="speaker">` |
| `tei:l` | `<p class="line" data-n="..." data-cts-urn="..." id="l{n}">` |
| `tei:p` | `<p>` |
| `tei:div` | `<div>` |
| `tei:emph` | `<em>` |
| `tei:note` | `<span class="note">` |
| `tei:gap` | `<span class="gap">†</span>` |
| `tei:pb`, `tei:milestone` | *(suppressed)* |

**To extend for a TEI customization:** `<xsl:import href="tei-to-html-base.xsl"/>`
and add or override templates.  Import precedence means your overrides
automatically win over the base.

### `generate_chunks.xsl` — batch generator

Imports the base.  Parameters:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `$chunk-unit` | `'card'` | `milestone/@unit` value to chunk on |
| `$output-dir` | `'.'` | Directory for output files |

Output files are named `{chunk-unit}_{@n}.html`.  An `index.json` manifest
is also written.

**Key XSLT 3 constructs used:**

`xsl:iterate` replaces the XSLT 2 pattern of recursive named templates for
stateful loops.  Accumulator params carry state across iterations:

```xslt
<xsl:iterate select="$milestones">
  <xsl:param name="index-entries" as="map(*)*" select="()"/>

  <!-- on-completion fires ONCE after the last item, with final param values -->
  <!-- It MUST appear first in the iterate body (after xsl:param)           -->
  <xsl:on-completion>
    <xsl:result-document href="{$output-dir}/index.json" method="json" indent="yes">
      <xsl:sequence select="map{ 'chunks': array{ $index-entries }, ... }"/>
    </xsl:result-document>
  </xsl:on-completion>

  <!-- iteration body -->
  <xsl:result-document href="{$output-dir}/{$chunk-unit}_{@n}.html" ...>
    ...
  </xsl:result-document>

  <!-- next-iteration MUST be the last instruction in the body -->
  <xsl:next-iteration>
    <xsl:with-param name="index-entries"
      select="($index-entries, map{ 'n': string(@n), ... })"/>
  </xsl:next-iteration>

</xsl:iterate>
```

`method="json"` on `xsl:result-document` serializes XDM maps and arrays
directly to JSON — no manual string-building needed.

**Saxon command-line usage:**

```bash
# Seneca, chunked by card
saxon -s:phi1017.phi007.perseus-lat2.xml \
      -xsl:generate_chunks.xsl           \
      chunk-unit=card                    \
      output-dir=/tmp/seneca

# larger.xml test document, chunked by section
saxon -s:larger.xml              \
      -xsl:generate_chunks.xsl  \
      chunk-unit=section         \
      output-dir=/tmp/larger
```

---

## CTS URN annotation

### Structure of a CTS URN

```
urn:cts:latinLit:phi1017.phi007.perseus-lat2:57
          │       │         │         │       └── passage citation node (l/@n)
          │       │         │         └────────── version identifier
          │       │         └──────────────────── work identifier
          │       └────────────────────────────── textgroup (author)
          └────────────────────────────────────── CTS namespace
```

The base URN (everything before the colon-separated passage) lives on
`div[@type='edition']/@n` in the TEI file.  The citation scheme is declared
in `encodingDesc/refsDecl/cRefPattern`.  Both the Seneca and Sophocles files
declare single-level (flat line) citation: `l[@n='$1']`.

### In the generated HTML

Each `<p class="line">` receives:

```html
<p class="line"
   data-n="57"
   id="l57"
   data-cts-urn="urn:cts:latinLit:phi1017.phi007.perseus-lat2:57">
  O regnorum magnis fallax
</p>
```

- `id="l{n}"` — fragment-safe anchor for deep links (`card_57.html#l57`)
- `data-cts-urn` — full machine-readable URN for resolvers / JavaScript
- Raw URN not used as `id` because colons in fragment identifiers require
  percent-encoding, making links unreadable

Each chunk page also carries:

```html
<meta name="dc.identifier" content="urn:cts:latinLit:phi1017.phi007.perseus-lat2:57-107">
```

### `index.json` manifest

```json
{
  "base_urn": "urn:cts:latinLit:phi1017.phi007.perseus-lat2",
  "title": "Agamemnon",
  "chunks": [
    { "n": "1",  "file": "card_1.html",  "urn": "...:1-56"   },
    { "n": "57", "file": "card_57.html", "urn": "...:57-107" },
    ...
  ]
}
```

This is the minimum data a CTS resolver needs to map `urn:cts:...:83`
→ `card_57.html#l83`.

---

## XML escaping gotcha

The XPath `<<` operator (document-order "comes before") **must** be escaped as
`&lt;&lt;` when used inside XSLT attribute values (`select=`, `test=`, etc.),
because `<` is illegal in XML attribute content.  `>>` is technically
permitted unescaped but `&gt;&gt;` is safer.  Both are transparent to the
XPath processor after XML parsing.  Failure to escape `<<` produces a Saxon
compile error that points at `>>` — a confusing diagnostic.

---

## Deferred work

### Sophocles hierarchical citation *(most urgent)*

`tlg0011.tlg001.perseus-grc2.xml` (Sophocles *Trachiniae*) has nested
`div[@type='textpart']` elements (episode → strophe / antistrophe → line).
The current `refsDecl` declares only flat line-number citation, erasing that
structure.  Proper multi-level URNs (e.g. `strophe.1.3`) require:

1. Confirming the correct scholarly citation conventions with classical
   philologists
2. Updating `refsDecl` to declare a hierarchical citation scheme
3. Adding a `tei:div[@type='textpart']` template to `tei-to-html-base.xsl`
4. Extending `local:chunk-cts-range()` to handle multi-level passage references

### CTS resolver

`index.json` contains the data.  A small service that maps a passage URN to
the correct chunk file and `#l{n}` anchor has not been built.

### ODD-to-stylesheet generation *(longer term)*

TEI ODD files define element sets and citation schemes for specific
customizations.  The `xsl:import` architecture was chosen partly to support
generating customization-specific stylesheets derived from an ODD.  The
design for this has not yet been worked out.

### Tests

No automated tests exist for the XSLT.  The Python module has a test
directory but no substantive test cases.

---

## Source history

| Repo | Role |
|------|------|
| `https://github.com/PerseusDLCode/tei-tagger` | Scratchpad — full development history including XQuery explorations |

Key commits in `tei-tagger`:

| Commit | What |
|--------|------|
| `78cdd80` | Card generation working against real Perseus texts |
| `20af699` | CTS URN support added to Python generator |
| `5ef6a40` | XSLT batch generator (`generate_chunks.xsl` + `tei-to-html-base.xsl`) |
