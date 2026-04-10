<?xml version="1.0"?>
<xsl:stylesheet
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xslFormatting="urn:xslFormatting"
    version="1.0">
    <xsl:output method="html"/>
    <xsl:template match="/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt">
        <h1><xsl:value-of select="/tei:title/text()" /></h1>
        <h2><xsl:value-of select="/tei:author/text()" /></h2>
        <p>Edited by <xsl:value-of select="/tei:editor/text()" /></p>
        <p>Sponsored by <xsl:value-of select="/tei:editor/text()" /></p>

    </xsl:template>
</xsl:stylesheet>