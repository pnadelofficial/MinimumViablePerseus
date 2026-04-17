<?xml version="1.0" encoding="UTF-8"?>
<!--
  generate_div_chunks.xsl
  Division-based batch generator: produces one HTML file per structural div
  (e.g. chapter, scene, poem) plus index.json.

  Parameters:
    chunk-unit  (xs:string)  @subtype value of the target divs  [default: 'chapter']
    output-dir  (xs:string)  directory to write output files to  [default: '.']
    catalog-url (xs:string)  relative URL for the Catalog nav link

  The stylesheet selects top-level divs whose @subtype matches chunk-unit
  (i.e. divs that are not nested inside another matching div).  It renders
  the full content of each div using chunker_core.xsl without start/stop
  milestone filtering, since the div boundary IS the chunk boundary.

  Output files are named  {chunk-unit}_{position}.html  (e.g. chapter_1.html).
-->
<xsl:stylesheet
  xmlns:xsl  ="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei  ="http://www.tei-c.org/ns/1.0"
  xmlns:xs   ="http://www.w3.org/2001/XMLSchema"
  xmlns:local="http://local.functions"
  version="3.0"
  exclude-result-prefixes="tei xs local">

  <xsl:import href="chunker_core.xsl"/>

  <xsl:output method="html" html-version="5" indent="yes"/>

  <!-- ============================================================
       Parameters
       ============================================================ -->

  <xsl:param name="chunk-unit"  as="xs:string" select="'chapter'"/>
  <xsl:param name="output-dir"  as="xs:string" select="'.'"/>
  <xsl:param name="catalog-url" as="xs:string" select="'/index.html'"/>


  <!-- ============================================================
       Main template
       ============================================================ -->

  <xsl:template match="/">
    <xsl:variable name="base-urn"   select="local:extract-base-urn(.)"/>
    <xsl:variable name="work-title" select="string((//tei:titleStmt/tei:title)[1])"/>

    <!-- Top-level divs matching chunk-unit.
         Try @subtype first (e.g. subtype="chapter"); fall back to @type
         (e.g. type="textpart" or type="book") for encodings that do not
         use @subtype.  "Top-level" means not nested inside another matching div. -->
    <xsl:variable name="by-subtype" as="element()*" select="
      //tei:div[@subtype = $chunk-unit]
               [not(ancestor::tei:div[@subtype = $chunk-unit])]
    "/>
    <xsl:variable name="chunks" as="element()*" select="
      if (exists($by-subtype)) then $by-subtype
      else //tei:div[@type = $chunk-unit]
                    [not(ancestor::tei:div[@type = $chunk-unit])]
    "/>

    <xsl:if test="empty($chunks)">
      <xsl:message terminate="yes">
        No div elements found with subtype="<xsl:value-of select="$chunk-unit"/>"
        or type="<xsl:value-of select="$chunk-unit"/>".
        Check the chunk-unit parameter.
      </xsl:message>
    </xsl:if>

    <xsl:iterate select="$chunks">
      <xsl:param name="index-entries" as="map(*)*" select="()"/>

      <xsl:on-completion>
        <xsl:result-document
          href  ="{$output-dir}/index.json"
          method="json"
          indent="yes">
          <xsl:sequence select="map {
            'base_urn': ($base-urn, '')[1],
            'title'   : $work-title,
            'chunks'  : array { $index-entries }
          }"/>
        </xsl:result-document>
      </xsl:on-completion>

      <xsl:variable name="div"      select="."/>
      <xsl:variable name="pos"      select="position()"/>
      <xsl:variable name="pos-prev" select="$pos - 1"/>
      <xsl:variable name="pos-next" select="if (position() lt last()) then $pos + 1 else ()"/>

      <xsl:variable name="file-name"
        select="concat($chunk-unit, '_', $pos, '.html')"/>
      <xsl:variable name="prev-file"
        select="if ($pos gt 1) then concat($chunk-unit, '_', $pos-prev, '.html') else ()"/>
      <xsl:variable name="next-file"
        select="if (exists($pos-next)) then concat($chunk-unit, '_', $pos-next, '.html') else ()"/>

      <xsl:variable name="chunk-label"
        select="concat($work-title, ' — ', $chunk-unit, ' ', @n)"/>

      <!-- ── Write the chunk HTML file ── -->
      <xsl:result-document
        href        ="{$output-dir}/{$file-name}"
        method      ="html"
        html-version="5"
        indent      ="yes">
        <html>
          <head>
            <meta charset="utf-8"/>
            <title><xsl:value-of select="$chunk-label"/></title>
            <style>
body         { font-family: serif; max-width: 48em; margin: 2em auto }
nav          { margin-bottom: 1em; font-size: .9em }
nav a        { margin-right: 1em }
h1           { font-size: 1em; color: #555; margin-bottom: .25em }
.speech      { margin: 1em 0 }
.speaker     { font-weight: bold; display: block; margin-bottom: .25em }
.line        { margin: .1em 0; padding-left: 2em }
.gap         { color: #888; font-style: italic }
.note        { border-bottom: 1px dotted #888 }
            </style>
          </head>
          <body>
            <nav>
              <a href="{$catalog-url}">&#x2190; Catalog</a>
              <xsl:if test="exists($prev-file)">
                <a href="{$prev-file}">&#x2190; prev</a>
              </xsl:if>
              <xsl:if test="exists($next-file)">
                <a href="{$next-file}">next &#x2192;</a>
              </xsl:if>
            </nav>
            <h1><xsl:value-of select="$chunk-label"/></h1>
            <!-- Render the full div content; no start/stop filtering needed -->
            <xsl:apply-templates select="$div/node()" mode="chunk">
              <xsl:with-param name="base-urn" select="$base-urn" tunnel="yes"/>
            </xsl:apply-templates>
          </body>
        </html>
      </xsl:result-document>

      <xsl:next-iteration>
        <xsl:with-param name="index-entries" select="(
          $index-entries,
          map {
            'n'   : string(@n),
            'file': $file-name,
            'urn' : ''
          }
        )"/>
      </xsl:next-iteration>

    </xsl:iterate>
  </xsl:template>

</xsl:stylesheet>
