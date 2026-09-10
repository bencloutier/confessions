#!/usr/bin/env python3
"""
Extract Albert C. Outler's 1955 English translation of the Confessions
(publicly released by the translator; hosted on Wikisource) into one
paragraph list per book, aligned with the standard Book.Paragraph
numbering used for the Latin text.

Unlike most other public-domain translations, Outler's text is itself
explicitly numbered paragraph-by-paragraph ("1. ... 2. ... 3. ...") using
the same standard numbering as the Latin critical edition, so no
heuristic alignment is needed -- paragraph N in the source *is* Latin
section N.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "raw_en" / "outler"
OUT = ROOT / "translation.json"
SUMMARY_OUT = ROOT / "book_summaries.json"

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]

EXPECTED_COUNTS = [31, 18, 21, 31, 25, 26, 27, 30, 37, 70, 41, 43, 53]

PARA_START_RE = re.compile(r"(?m)^(\d+)\. ")


def clean_text(t: str) -> str:
    # Footnotes.
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", "", t)
    # Wikitext italics/bold markup.
    t = re.sub(r"'''''(.*?)'''''", r"\1", t)
    t = re.sub(r"'''(.*?)'''", r"\1", t)
    t = re.sub(r"''(.*?)''", r"\1", t)
    # [[link|text]] or [[text]] -> text
    t = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    # Any remaining stray wiki/html tags.
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\{\{[^}]*\}\}", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_book(n: int) -> list:
    roman = ROMAN[n]
    path = SRC_DIR / f"book_{roman}.wikitext"
    raw = path.read_text(encoding="utf-8")

    # Drop everything before the first numbered paragraph (header/intro
    # summary) and any chapter-heading lines ("== Chapter I ==").
    raw = re.sub(r"(?m)^== .*? ==\s*$", "", raw)

    parts = PARA_START_RE.split(raw)
    # parts = [prefix, num, text, num, text, ...]
    paras = []
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        text = clean_text(parts[i + 1])
        paras.append((num, text))

    # Sanity: numbers should be exactly 1..len(paras) in order.
    nums = [n for n, _ in paras]
    expected_nums = list(range(1, len(paras) + 1))
    if nums != expected_nums:
        raise ValueError(f"book {n}: paragraph numbers out of sequence: {nums[:10]}...")

    return [text for _, text in paras]


FIRST_CHAPTER_RE = re.compile(r"(?m)^== Chapter .+ ==\s*$")


def extract_summary(n: int) -> str:
    """The short italicized description Outler put at the head of each book."""
    roman = ROMAN[n]
    raw = (SRC_DIR / f"book_{roman}.wikitext").read_text(encoding="utf-8")
    m = FIRST_CHAPTER_RE.search(raw)
    intro = raw[: m.start()] if m else raw
    intro = re.sub(r"\{\{header.*?\}\}", "", intro, flags=re.S)
    intro = re.sub(r"\[\[Image:[^\]]*\]\]", "", intro)
    return clean_text(intro)


def main():
    books = {}
    summaries = {}
    for n in range(1, 14):
        paras = extract_book(n)
        expected = EXPECTED_COUNTS[n - 1]
        flag = "OK" if len(paras) == expected else f"MISMATCH (got {len(paras)}, want {expected})"
        print(f"book {n:2}: {len(paras):3} paragraphs  {flag}")
        books[str(n)] = paras
        summaries[str(n)] = extract_summary(n)
    OUT.write_text(json.dumps(books, ensure_ascii=False, indent=1), encoding="utf-8")
    SUMMARY_OUT.write_text(json.dumps(summaries, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
