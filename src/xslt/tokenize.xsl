<?xml version="1.0" encoding="UTF-8"?>
<!--
  tokenize.xsl
  Stage 2 of the Perseus6 annotation pipeline: extract orthographic tokens
  from a TEI document that has been processed by add_xml_ids.xsl.

  Input:  A TEI document whose citable elements carry stable @xml:id attributes
          (produced by add_xml_ids.xsl).
  Output: A <tokens> document: one <token> per orthographic word, carrying:
            @surface   — form with leading/trailing punctuation stripped
            @raw       — original whitespace-delimited string
            @anchor    — xml:id of the containing element
            @in        — local-name of the containing element
            @position  — position of this token within its containing text node

  Design notes:
  - Apparatus elements are excluded (see $exclude-elements).
  - Punctuation is stripped from leading and trailing positions only; internal
    punctuation (hyphens, apostrophes mid-word) is preserved.
  - @anchor resolves to a real @xml:id; this stylesheet requires the preparation
    pass.  If an element still lacks @xml:id, a warning is emitted.

  XPath 3.0 regex notes (relevant to strip-punct):
  Inside a character class [...]:
    \]    escape the closing bracket
    \\    escape a literal backslash
    -     place at start or end to mean literal hyphen
    ^     special only as first character (negation)
  XML escaping (&lt; for <, &gt; for >, &quot; for ") is resolved by the XML
  parser before XPath sees the string, so the regex receives the intended chars.
  Apostrophe is handled in separate replace() calls using double-quoted strings
  to avoid the XPath single-quote delimiter conflict.
-->
<xsl:stylesheet
  xmlns:xsl  ="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei  ="http://www.tei-c.org/ns/1.0"
  xmlns:xs   ="http://www.w3.org/2001/XMLSchema"
  xmlns:local="http://local.functions"
  version="3.0"
  exclude-result-prefixes="tei xs local">

  <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

  <!-- Elements whose text content should be suppressed entirely.
       Add or remove names as corpus analysis dictates.             -->
  <xsl:param name="exclude-elements" as="xs:string*"
             select="('note', 'del', 'rdg', 'supplied', 'gap', 'unclear',
                      'figDesc', 'label', 'speaker', 'stage')"/>

  <!-- ============================================================
       strip-punct: remove leading and trailing punctuation from a token.

       Steps 1-2: main punctuation class (single-quoted attribute value).
       Steps 3-4: apostrophe/single-quote (double-quoted attribute value).

       Main punctuation class characters:
         .,;:!?    — common ASCII punctuation
         ·         — middle dot / Greek interpunct (U+00B7)
         —–        — em-dash (U+2014), en-dash (U+2013)
         (){}      — parentheses and braces
         \[\]      — square brackets (\] escapes the closing bracket)
         &lt;&gt;  — less-than / greater-than
         ⟨⟩        — mathematical angle brackets (U+27E8/U+27E9), EpiDoc texts
         &quot;    — double quotation mark
       ============================================================ -->

  <xsl:function name="local:strip-punct" as="xs:string">
    <xsl:param name="s" as="xs:string"/>
    <xsl:variable name="s1"
      select="replace($s,
                '^[.,;:!?·—–(){}\[\]&lt;&gt;⟨⟩&quot;]+', '')"/>
    <xsl:variable name="s2"
      select="replace($s1,
                '[.,;:!?·—–(){}\[\]&lt;&gt;⟨⟩&quot;]+$', '')"/>
    <xsl:variable name="s3" select="replace($s2, &quot;^'+&quot;, '')"/>
    <xsl:variable name="s4" select="replace($s3, &quot;'+$&quot;,  '')"/>
    <xsl:sequence select="$s4"/>
  </xsl:function>

  <!-- ============================================================
       Root: emit <tokens> wrapper with document metadata.
       ============================================================ -->

  <xsl:template match="/">
    <xsl:variable name="urn"
                  select="(//@n[starts-with(., 'urn:cts')])[1]"/>
    <xsl:variable name="lang"
                  select="(//@xml:lang)[1]"/>
    <tokens>
      <xsl:if test="$urn">
        <xsl:attribute name="urn" select="$urn"/>
      </xsl:if>
      <xsl:if test="$lang">
        <xsl:attribute name="xml:lang" select="$lang"/>
      </xsl:if>
      <xsl:apply-templates select="//tei:body"/>
    </tokens>
  </xsl:template>

  <!-- ============================================================
       Suppress excluded elements and their descendants entirely.
       ============================================================ -->

  <xsl:template match="tei:*[local-name() = $exclude-elements]"
                priority="10"/>

  <!-- ============================================================
       For every other element, recurse into children.
       ============================================================ -->

  <xsl:template match="tei:*">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- ============================================================
       Text nodes: tokenize and emit <token> elements.
       Requires the parent element to have @xml:id (from add_xml_ids.xsl).
       ============================================================ -->

  <xsl:template match="text()">
    <!--
      Walk up to the nearest citable ancestor — the innermost ancestor::tei:*
      that carries @xml:id (stamped by add_xml_ids.xsl).  The ancestor axis
      returns nodes in reverse document order (innermost first), so [1] is
      the closest.  Falling back to the immediate parent preserves @in for
      diagnostics even when no citable ancestor exists.
    -->
    <xsl:variable name="anchor"
      select="if (ancestor::tei:*[@xml:id])
              then (ancestor::tei:*[@xml:id])[1]
              else parent::tei:*"/>
    <xsl:variable name="anchor-id"   select="string($anchor/@xml:id)"/>
    <xsl:variable name="anchor-name" select="local-name($anchor)"/>

    <xsl:if test="$anchor-id = ''">
      <xsl:message>WARNING: no citable ancestor found for text in
        &lt;<xsl:value-of select="local-name(parent::tei:*)"/>&gt; —
        run add_xml_ids.xsl first.</xsl:message>
    </xsl:if>

    <xsl:variable name="raw-tokens" as="xs:string*"
                  select="tokenize(normalize-space(.), '\s+')
                          [normalize-space(.) != '']"/>

    <xsl:for-each select="$raw-tokens">
      <xsl:variable name="raw"     select="."/>
      <xsl:variable name="surface" select="local:strip-punct($raw)"/>
      <xsl:if test="normalize-space($surface) != ''">
        <token>
          <xsl:attribute name="surface"  select="$surface"/>
          <xsl:attribute name="raw"      select="$raw"/>
          <xsl:attribute name="anchor"   select="$anchor-id"/>
          <xsl:attribute name="in"       select="$anchor-name"/>
          <xsl:attribute name="position" select="position()"/>
        </token>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>
