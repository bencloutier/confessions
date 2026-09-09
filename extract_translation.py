#!/usr/bin/env python3
"""
Extract E. B. Pusey's 1838 English translation of the Confessions (public
domain, via Project Gutenberg #3296) into one paragraph list per book,
aligned with the standard Book.Paragraph numbering used for the Latin text.

Pusey's translation preserves the traditional paragraph/section divisions
as actual paragraph breaks, so -- for most books -- paragraph N of the
English text corresponds directly to Latin section N. A few books are off
by one due to a paragraph Pusey merged or split differently; those are
patched by hand below after inspection.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "raw_en" / "pusey.html"
OUT = ROOT / "translation.json"

EXPECTED_COUNTS = [31, 18, 21, 31, 25, 26, 27, 30, 37, 70, 41, 43, 53]


def clean_paragraph(p: str) -> str:
    p = re.sub(r"<br\s*/?>", " ", p, flags=re.I)
    p = re.sub(r"<[^>]+>", "", p)
    p = html.unescape(p)
    p = re.sub(r"\s+", " ", p).strip()
    return p


def extract_book(raw: str, n: int) -> list:
    anchor = f"link2H_4_{n:04d}"
    next_anchor = f"link2H_4_{n+1:04d}"
    start = raw.index(f'{anchor}" id="{anchor}')
    end = raw.index(f'{next_anchor}" id="{next_anchor}') if n < 13 else len(raw)
    body = raw[start:end]
    paras = re.findall(r"<p>(.*?)</p>", body, re.S)
    cleaned = [clean_paragraph(p) for p in paras]
    return [p for p in cleaned if len(p) > 40]


# Pusey's paragraph breaks otherwise line up exactly with the standard
# Book.Paragraph numbering, except for a few spots where his translation
# merges or splits a section differently. Found by aligning relative
# paragraph lengths against the Latin (see git history) and confirmed by
# reading the surrounding sentences. Applied after cleaning, before the
# length-40 filter, using 0-based paragraph indices.
_MERGE_AT = {
    6: 25,  # Pusey runs 6.26 and 6.27's material together as one paragraph
}
_SPLIT_AT = {
    # (paragraph index, character offset into that paragraph's text)
    8: (10, "ner, and feared as much to be freed of all incumbrances, as we should fear to be encumbered with it. "),
    12: (17, '"What will ye say then, O ye gainsayers? '),
    13: (21, "For Thou by an eternal counsel dost in their proper seasons bestow heavenly blessings upon the earth. "),
}


def apply_fixups(n: int, paras: list) -> list:
    if n in _MERGE_AT:
        i = _MERGE_AT[n]
        paras = paras[:i] + [paras[i] + " " + paras[i + 1]] + paras[i + 2 :]
    if n in _SPLIT_AT:
        i, prefix = _SPLIT_AT[n]
        para = paras[i]
        assert para.startswith(prefix.strip()[:30]) or prefix.strip()[:30] in para, (
            f"book {n}: expected split prefix not found in paragraph {i}"
        )
        pos = len(prefix)
        left, right = para[:pos].strip(), para[pos:].strip()
        paras = paras[:i] + [left, right] + paras[i + 1 :]
    return paras


def main():
    raw = SRC.read_text(encoding="utf-8")
    books = {}
    for n in range(1, 14):
        paras = extract_book(raw, n)
        paras = apply_fixups(n, paras)
        expected = EXPECTED_COUNTS[n - 1]
        flag = "OK" if len(paras) == expected else f"MISMATCH (got {len(paras)}, want {expected})"
        print(f"book {n:2}: {len(paras):3} paragraphs  {flag}")
        books[str(n)] = paras
    OUT.write_text(json.dumps(books, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
