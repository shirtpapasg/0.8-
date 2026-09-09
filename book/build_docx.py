#!/usr/bin/env python3
"""Build a Kindle-ready .docx from the manuscript Markdown, using the
formatting conventions of the earlier books in the series.

Usage: build_docx.py MANUSCRIPT.md TEMPLATE.docx OUTPUT.docx
The template supplies styles/settings; only word/document.xml is replaced.
"""
import re, sys, zipfile, shutil
from xml.sax.saxutils import escape

def runs(text):
    """Convert inline **bold** and *italic* markdown into w:r runs."""
    out = []
    pos = 0
    pat = re.compile(r'\*\*(.+?)\*\*|\*(.+?)\*')
    for m in pat.finditer(text):
        if m.start() > pos:
            out.append(run(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(run(m.group(1), bold=True))
        else:
            out.append(run(m.group(2), italic=True))
        pos = m.end()
    if pos < len(text):
        out.append(run(text[pos:]))
    return ''.join(out)

def run(text, bold=False, italic=False):
    rpr = ''
    if bold or italic:
        rpr = '<w:rPr>' + ('<w:b/>' if bold else '') + ('<w:i/>' if italic else '') + '</w:rPr>'
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

BODY_PPR = '<w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr>'
QUOTE_PPR = '<w:pPr><w:ind w:left="720" w:right="720"/><w:spacing w:before="120" w:after="120"/></w:pPr>'

def para(ppr, inner):
    return f'<w:p>{ppr}{inner}</w:p>\n'

def build(md_text):
    lines = md_text.split('\n')
    paras = []
    seen_title = False
    in_body = False          # becomes True at the first "# Part" / "# Chapter"
    quote_buf = []
    body_buf = []             # consecutive non-blank lines form one paragraph

    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            paras.append(para(QUOTE_PPR, runs(' '.join(quote_buf))))
            quote_buf = []

    def flush_body():
        nonlocal body_buf
        if body_buf:
            paras.append(para(BODY_PPR, runs(' '.join(body_buf))))
            body_buf = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith('> '):
            flush_body()
            quote_buf.append(line[2:].strip())
            continue
        if line.strip() == '>':
            continue
        flush_quote()
        if not line.strip():
            flush_body()
            continue
        if line.strip() == '---':
            flush_body()
            continue
        if line.startswith('#'):
            flush_body()
        if line.startswith('# '):
            title = line[2:].strip()
            if not seen_title:
                seen_title = True
                paras.append(para('<w:pPr><w:pStyle w:val="Heading1"/><w:jc w:val="center"/></w:pPr>', runs(title)))
                continue
            if re.match(r'(Part |Chapter )', title):
                in_body = True
            paras.append(para('<w:pPr><w:pStyle w:val="Heading2"/></w:pPr>',
                              '<w:r><w:br w:type="page"/></w:r>' + runs(title)))
            continue
        if line.startswith('## '):
            title = line[3:].strip()
            if not in_body:
                paras.append(para('<w:pPr><w:pStyle w:val="Heading2"/></w:pPr>',
                                  '<w:r><w:br w:type="page"/></w:r>' + runs(title)))
            else:
                paras.append(para('<w:pPr><w:pStyle w:val="Heading3"/></w:pPr>', runs(title)))
            continue
        if line.startswith('#'):
            raise SystemExit(f'Unexpected heading depth: {line}')
        body_buf.append(line.strip())
    flush_quote()
    flush_body()
    return ''.join(paras)

SECT = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/><w:cols w:space="720"/></w:sectPr>')

def main(md_path, template, output):
    md_text = open(md_path, encoding='utf-8').read()
    body = build(md_text)
    with zipfile.ZipFile(template) as zin:
        doc = zin.read('word/document.xml').decode('utf-8')
        head = doc[:doc.index('<w:body>') + len('<w:body>')]
        new_doc = head + '\n' + body + SECT + '</w:body></w:document>'
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == 'word/document.xml':
                    data = new_doc.encode('utf-8')
                zout.writestr(item, data)
    print('wrote', output, 'paragraphs:', body.count('<w:p>'))

if __name__ == '__main__':
    main(*sys.argv[1:4])
