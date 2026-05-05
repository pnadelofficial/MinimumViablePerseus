<?xml version="1.0" encoding="UTF-8"?>
<!--
  generate_chunks.xsl
  Batch generator: produces one HTML file per milestone chunk, a toc.html,
  and index.json.

  Parameters:
    chunk-unit  (xs:string)  milestone/@unit value to chunk on  [default: 'card']
    output-dir  (xs:string)  directory to write output files to [default: '.']
    catalog-url (xs:string)  relative URL for the Catalog nav link

  Output files are named  {chunk-unit}_{position}.html  (e.g. card_57.html).

  Usage with Saxon on the command line:
    saxon -s:phi1017.phi007.perseus-lat2.xml \
          -xsl:generate_chunks.xsl           \
          chunk-unit=card                    \
          output-dir=/tmp/seneca

    saxon -s:larger.xml      \
          -xsl:generate_chunks.xsl \
          chunk-unit=section  \
          output-dir=/tmp/larger
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

  <xsl:param name="chunk-unit"  as="xs:string" select="'card'"/>
  <xsl:param name="output-dir"  as="xs:string" select="'.'"/>
  <xsl:param name="catalog-url" as="xs:string" select="'/index.html'"/>
  <!-- When non-empty, each word in the output is linked to the morphological
       server at this base URL (e.g. http://localhost:5000). -->
  <xsl:param name="morph-url"   as="xs:string" select="''"/>


  <!-- ============================================================
       Main template
       ============================================================ -->

  <xsl:template match="/">
    <xsl:variable name="base-urn"   select="local:extract-base-urn(.)"/>
    <xsl:variable name="work-title" select="string((//tei:titleStmt/tei:title)[1])"/>
    <xsl:variable name="doc-lang"   select="string((//tei:text/@xml:lang)[1])"/>
    <xsl:variable name="milestones" select="//tei:milestone[@unit = $chunk-unit]"/>
    <xsl:variable name="home-url"
      select="replace($catalog-url, 'catalog/[^/]+\.html$', 'index.html')"/>

    <xsl:if test="empty($milestones)">
      <xsl:message terminate="yes">
        No milestone elements found with unit="<xsl:value-of select="$chunk-unit"/>".
        Check the chunk-unit parameter.
      </xsl:message>
    </xsl:if>

    <!--
      xsl:iterate lets us accumulate index metadata across chunks and
      write index.json and toc.html in xsl:on-completion once all chunks are done.
    -->
    <xsl:iterate select="$milestones">
      <xsl:param name="index-entries" as="map(*)*" select="()"/>

      <!-- xsl:on-completion must appear before any content instructions -->
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

        <!-- TOC page -->
        <xsl:result-document
          href        ="{$output-dir}/toc.html"
          method      ="html"
          html-version="5"
          indent      ="yes">
          <html>
            <xsl:if test="$doc-lang != ''">
              <xsl:attribute name="lang" select="$doc-lang"/>
            </xsl:if>
            <head>
              <meta charset="utf-8"/>
              <meta name="viewport" content="width=device-width, initial-scale=1"/>
              <title><xsl:value-of select="$work-title"/> — Contents | Perseus</title>
              <style><xsl:value-of select="$page-css"/></style>
            </head>
            <body>
              <header class="site-header">
                <a href="{$home-url}">Perseus Digital Library</a>
              </header>
              <nav class="chunk-nav">
                <span><a href="{$catalog-url}">&#x2190; Catalog</a></span>
              </nav>
              <main>
                <h1><xsl:value-of select="$work-title"/></h1>
                <ol class="toc">
                  <xsl:for-each select="$index-entries">
                    <li>
                      <a href="{.('file')}">
                        <xsl:value-of select=".('n')"/>
                      </a>
                    </li>
                  </xsl:for-each>
                </ol>
              </main>
              <footer class="site-footer">Perseus Digital Library</footer>
            </body>
          </html>
        </xsl:result-document>
      </xsl:on-completion>

      <xsl:variable name="ms"      select="."/>
      <xsl:variable name="ms-next"
        select="following::tei:milestone[@unit = $chunk-unit][1]"/>
      <xsl:variable name="ms-prev"
        select="preceding::tei:milestone[@unit = $chunk-unit][1]"/>

      <!-- Elements strictly between this milestone and the next.
           For the final chunk there is no next milestone, so we take
           all elements after this one. -->
      <xsl:variable name="hits" as="element()*" select="
        if (empty($ms-next))
        then  //element()[. &gt;&gt; $ms]
        else  //element()[. &gt;&gt; $ms][. &lt;&lt; $ms-next]
      "/>
      <!-- Top-level subset: elements with no ancestor also in $hits.
           When $hits is empty the milestones are inline (inside paragraphs
           rather than between block elements).  Fall back to the body's
           direct children and rely on the $start tunnel parameter in
           chunker_core to suppress content that precedes $ms. -->
      <xsl:variable name="top" as="element()*" select="
        if (exists($hits))
        then $hits[not(ancestor::* intersect $hits)]
        else (//tei:body, //tei:text)[1]/child::*
      "/>

      <xsl:variable name="cts-range"
        select="local:chunk-cts-range($top, $ms-next, $base-urn)"/>

      <!-- Use position() for filenames so they are globally unique even
           when @n values restart across structural divisions (e.g. card 1
           in Book 1 and card 1 in Book 2 of the Iliad).  The semantic @n
           value is preserved in the HTML title and the index.json manifest. -->
      <xsl:variable name="pos"       select="position()"/>
      <xsl:variable name="pos-prev"  select="$pos - 1"/>
      <xsl:variable name="pos-next"  select="if ($ms-next) then $pos + 1 else ()"/>
      <xsl:variable name="file-name"
        select="concat($chunk-unit, '_', $pos, '.html')"/>
      <xsl:variable name="prev-file"
        select="if ($ms-prev) then concat($chunk-unit, '_', $pos-prev, '.html') else ()"/>
      <xsl:variable name="next-file"
        select="if ($ms-next) then concat($chunk-unit, '_', $pos-next, '.html') else ()"/>

      <!-- ── Write the chunk HTML file ── -->
      <xsl:result-document
        href      ="{$output-dir}/{$file-name}"
        method    ="html"
        html-version="5"
        indent    ="yes">
        <html>
          <xsl:if test="$doc-lang != ''">
            <xsl:attribute name="lang" select="$doc-lang"/>
          </xsl:if>
          <head>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1"/>
            <title>
              <xsl:value-of select="$work-title"/>
              <xsl:text> &#x2014; </xsl:text>
              <xsl:value-of select="$chunk-unit"/>
              <xsl:text> </xsl:text>
              <xsl:value-of select="@n"/>
              <xsl:text> | Perseus</xsl:text>
            </title>
            <xsl:if test="exists($cts-range)">
              <meta name="dc.identifier" content="{$cts-range}"/>
            </xsl:if>
            <style><xsl:value-of select="$page-css"/></style>
          </head>
          <body>
            <header class="site-header">
              <a href="{$home-url}">Perseus Digital Library</a>
            </header>
            <nav class="chunk-nav">
              <span>
                <a href="{$catalog-url}">&#x2190; Catalog</a>
                <xsl:text> · </xsl:text>
                <a href="toc.html">Contents</a>
              </span>
              <span>
                <xsl:if test="exists($prev-file)">
                  <a href="{$prev-file}">&#x2190; prev</a>
                </xsl:if>
                <xsl:if test="exists($next-file)">
                  <a href="{$next-file}">next &#x2192;</a>
                </xsl:if>
              </span>
            </nav>
            <main>
              <h1>
                <xsl:value-of select="
                  if (exists($cts-range)) then $cts-range
                  else concat($work-title, ' — ', $chunk-unit, ' ', @n)
                "/>
              </h1>
              <!-- Single-pass transform: templates check $start/$stop themselves -->
              <xsl:apply-templates select="$top" mode="chunk">
                <xsl:with-param name="start"     select="$ms"        tunnel="yes"/>
                <xsl:with-param name="stop"      select="$ms-next"   tunnel="yes"/>
                <xsl:with-param name="base-urn"  select="$base-urn"  tunnel="yes"/>
                <xsl:with-param name="morph-url" select="$morph-url" tunnel="yes"/>
              </xsl:apply-templates>
            </main>
            <footer class="site-footer">Perseus Digital Library</footer>
          </body>
        </html>
      </xsl:result-document>

      <!-- xsl:next-iteration must be the last instruction in the body -->
      <xsl:next-iteration>
        <xsl:with-param name="index-entries" select="(
          $index-entries,
          map {
            'n'   : string(@n),
            'file': $file-name,
            'urn' : ($cts-range, '')[1]
          }
        )"/>
      </xsl:next-iteration>

    </xsl:iterate>
  </xsl:template>

</xsl:stylesheet>
