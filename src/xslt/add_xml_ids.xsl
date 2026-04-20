<?xml version="1.0" encoding="UTF-8"?>
<!--
  add_xml_ids.xsl
  Preparation pass: stamp stable @xml:id attributes onto citable TEI elements.

  Input:  A TEI document (any structural convention).
  Output: The same document with @xml:id added to every citable element that
          lacked one.  All other content is copied unchanged (identity transform).

  Citable elements are those whose unit names appear in the CTS refsDecl:
    //tei:refsDecl[@n='CTS']/tei:cRefPattern/@n

  ID format: {prefix}-{ancestor-n-1}-...-{own-n}
    prefix = @subtype (for textpart divs), @unit (for milestones), or local-name()
    ancestor @n values are collected from structural divs above, excluding the
    top-level edition div (whose @n is a CTS URN, not a citation component).

  Example: tei:l[@n="5"] inside div[@subtype="poem"][@n="1"] → xml:id="l-1-5"
  Example: div[@subtype="chapter"][@n="2"] → xml:id="chapter-2"
  Example: milestone[@unit="section"][@n="3"] inside chapter 2 → xml:id="section-2-3"

  This stylesheet is stage 1 of the Perseus6 annotation pipeline.  Its output
  feeds tokenize.xsl, which requires stable @xml:id anchors on citable elements.
-->
<xsl:stylesheet
  xmlns:xsl  ="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei  ="http://www.tei-c.org/ns/1.0"
  xmlns:xs   ="http://www.w3.org/2001/XMLSchema"
  xmlns:local="http://local.functions"
  version="3.0"
  exclude-result-prefixes="tei xs local">

  <xsl:output method="xml" indent="no" encoding="UTF-8"/>

  <!-- ============================================================
       Citable unit names derived from CTS refsDecl.
       E.g. ("chapter") or ("poem", "line").
       ============================================================ -->

  <!-- Lowercase all unit names so matching is case-insensitive.
       Some corpora use "Chapter"/"Book"; others use "chapter"/"book". -->
  <xsl:variable name="units" as="xs:string*"
    select="//tei:refsDecl[@n='CTS']/tei:cRefPattern/@n/lower-case(.)"/>

  <!-- ============================================================
       local:make-id: build a stable xml:id from citation coordinates.

       prefix    = @subtype | @unit | local-name(.)
       ancestors = @n values from structural ancestor divs (excl. edition div)
       joined by hyphens; non-[A-Za-z0-9_-] chars replaced with underscore.
       ============================================================ -->

  <xsl:function name="local:make-id" as="xs:string">
    <xsl:param name="el" as="element()"/>
    <xsl:variable name="prefix" as="xs:string"
      select="if ($el/@subtype) then lower-case(string($el/@subtype))
              else if ($el/@unit) then lower-case(string($el/@unit))
              else local-name($el)"/>
    <xsl:variable name="ancestor-ns" as="xs:string*"
      select="$el/ancestor::tei:div[not(starts-with(@n, 'urn:'))]/@n/string()"/>
    <xsl:variable name="raw"
      select="string-join(($prefix, $ancestor-ns, string($el/@n)), '-')"/>
    <!-- Sanitize: replace any char that is not alphanumeric, hyphen, or underscore -->
    <xsl:value-of select="replace($raw, '[^A-Za-z0-9_-]', '_')"/>
  </xsl:function>

  <!-- ============================================================
       Identity transform — copy everything as-is by default.
       ============================================================ -->

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- ============================================================
       Citable verse lines: tei:l[@n] without @xml:id.
       Active when "line" is a declared citation unit.
       ============================================================ -->

  <xsl:template match="tei:l[@n][not(@xml:id)]['line' = $units]" priority="10">
    <xsl:variable name="id" select="local:make-id(.)"/>
    <xsl:call-template name="copy-with-id">
      <xsl:with-param name="id" select="$id"/>
    </xsl:call-template>
  </xsl:template>

  <!-- ============================================================
       All structural divs with @n and without @xml:id, except the top-level
       edition div (whose @n is a CTS URN).  Stamping every div — not just
       CTS-cited units — ensures that introductions, prologues, and other
       non-CTS-cited sections still provide stable anchors for their content.
       ============================================================ -->

  <xsl:template
    match="tei:div[@n][not(@xml:id)][not(starts-with(@n, 'urn:'))]"
    priority="10">
    <xsl:variable name="id" select="local:make-id(.)"/>
    <xsl:call-template name="copy-with-id">
      <xsl:with-param name="id" select="$id"/>
    </xsl:call-template>
  </xsl:template>

  <!-- ============================================================
       Citable milestones: those whose @unit appears in the CTS units list.
       ============================================================ -->

  <xsl:template match="tei:milestone[@n][not(@xml:id)][lower-case(@unit) = $units]" priority="10">
    <xsl:variable name="id" select="local:make-id(.)"/>
    <xsl:call-template name="copy-with-id">
      <xsl:with-param name="id" select="$id"/>
    </xsl:call-template>
  </xsl:template>

  <!-- ============================================================
       Named template: emit the current element with @xml:id prepended,
       then copy all existing attributes and process children.
       Warns if the generated id would duplicate one already in the document.
       ============================================================ -->

  <xsl:template name="copy-with-id">
    <xsl:param name="id" as="xs:string"/>
    <xsl:if test="count(//*[@xml:id = $id]) gt 0">
      <xsl:message>WARNING: duplicate xml:id '<xsl:value-of select="$id"/>'
        on <xsl:value-of select="local-name()"/> @n=<xsl:value-of select="@n"/></xsl:message>
    </xsl:if>
    <xsl:copy>
      <xsl:attribute name="xml:id" select="$id"/>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
