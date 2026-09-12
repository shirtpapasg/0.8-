# Teaching the Right Question

Third book in the series that began with *Asking the Right Question* and continued with *Asking the Right Prompt*.

Files:

- `Teaching_the_Right_Question__Manuscript.md` - the manuscript in Markdown, using the same conventions as the earlier books (chapter headings, italic taglines, epigraphs, `>` blockquote prompts, `🔍 Takeaway` lines, `🌱` Reflective Pause and One Small Habit sections, Author's Note, References, and a fifty-prompt appendix).
- `Teaching_the_Right_Question__Manuscript.docx` - the Kindle-ready Word file, built from the Markdown with exactly the styles and page breaks of the earlier books (Heading 1 title, Heading 2 chapter openings on new pages, Heading 3 sections, indented prompt blocks).
- `build_docx.py` - rebuilds the `.docx` from the Markdown. It takes an earlier book's `.docx` as a style template and replaces only the document body, so the output matches the series formatting paragraph for paragraph.
- `STYLE_GUIDE.md` - the series bible and style rules used to draft the chapters. Reuse it for the next book.

To rebuild the Word file after editing the Markdown:

```
python3 build_docx.py Teaching_the_Right_Question__Manuscript.md <template.docx> Teaching_the_Right_Question__Manuscript.docx
```

where `<template.docx>` is any earlier manuscript in the series (for example the *Asking the Right Prompt* Kindle file).
