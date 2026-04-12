from lxml import etree

if __name__ == "__main__":
    doc = etree.parse("tests/data/tlg0011.tlg001.perseus-grc2.xml")
    xslt = etree.parse("src/perseus6/xslt/drama.xslt")
    transform = etree.XSLT(xslt)
    result = transform(doc)

    print(str(result))
