#!/usr/bin/env python3
"""
Builds word-linked HTML pages of Augustine's Confessions (Latin, public domain
text from The Latin Library / J.J. O'Donnell's edition) from raw/confN.html.

Every word token is wrapped in a link to Logeion (logeion.uchicago.edu), a
live Latin dictionary/morphology tool that shows the lemma (root), full
declension/conjugation paradigm, and grammatical parse (part of speech,
gender, declension, case, mood, etc.) for the clicked word form.
"""
import html
import json
import re
import sys
from pathlib import Path

import morph
import senses

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
OUT = ROOT / "books"
OUT.mkdir(exist_ok=True)

TRANSLATION_PATH = ROOT / "translation.json"
TRANSLATIONS = (
    json.loads(TRANSLATION_PATH.read_text(encoding="utf-8")) if TRANSLATION_PATH.exists() else {}
)

SECTION_RE = re.compile(r"^\d+\.\d+\.\d+$")
WORD_RE = re.compile(r"[A-Za-zÆæŒœ]+(?:'[A-Za-zÆæŒœ]+)?")
CHUNK_RE = re.compile(r"\S+")

BOOK_TITLES = {
    1: "Liber Primus", 2: "Liber Secundus", 3: "Liber Tertius",
    4: "Liber Quartus", 5: "Liber Quintus", 6: "Liber Sextus",
    7: "Liber Septimus", 8: "Liber Octavus", 9: "Liber Nonus",
    10: "Liber Decimus", 11: "Liber Undecimus", 12: "Liber Duodecimus",
    13: "Liber Tertius Decimus",
}

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


def extract_paragraphs(raw_html: str):
    """Return list of (section_id or None, paragraph_text) from Latin Library markup."""
    # Content lives in <p>...</p> blocks between <p class=border></P> markers.
    # We only want the plain <p> blocks (no class) after the pagehead.
    blocks = re.findall(r"<p(?:\s+class=([\"']?)([\w]+)\1)?>(.*?)</p>", raw_html, re.S | re.I)
    paragraphs = []
    pending_section = None
    for _, cls, body in blocks:
        cls = (cls or "").lower()
        if cls == "citation":
            break  # footer / attribution block marks the end of the text
        if cls in ("pagehead", "border"):
            continue
        text = html.unescape(body)
        text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)  # line breaks (e.g. inside quoted verse) -> space
        text = re.sub(r"<[^>]+>", "", text)  # strip remaining stray tags
        text = re.sub(r"&#\d+;", "", text)   # drop obfuscated mailto entities etc.
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        # A block that starts with a section marker (optionally followed by
        # an editorial "commentary on ..." note, which we discard) sets the
        # pending section id for the next real paragraph of Latin text.
        # Latin prose paragraphs never start with a digit, so this is safe.
        marker_match = re.match(r"^(\d+\.\d+\.\d+)\s*(.*)$", text, re.S)
        if marker_match:
            pending_section = marker_match.group(1)
            text = marker_match.group(2).strip()
            if not text or re.match(r"^commentary\b", text, re.I):
                # Either just the bare marker, or an editorial English
                # "commentary on X.Y.Z" note -- not Latin text either way.
                continue
            # This block had the marker AND the paragraph text run together
            # in the same <p> (usually they're in separate <p> tags) --
            # fall through and use the remainder as this section's text.
        if pending_section is None and paragraphs:
            # This <p> block is a continuation of the previous section (the
            # source sometimes splits one section across multiple <p> tags,
            # e.g. around embedded quoted verse) -- merge rather than start
            # a bogus unlabeled section.
            prev_sid, prev_text = paragraphs[-1]
            paragraphs[-1] = (prev_sid, f"{prev_text} {text}")
            continue
        paragraphs.append((pending_section, text))
        pending_section = None
    return paragraphs


def tokenize_to_html(paragraph_text: str) -> str:
    """
    Render each whitespace-delimited chunk of the paragraph as an interlinear
    block: the word (linked to Logeion, with any attached punctuation) on
    top, and a small auto-generated parse label (lemma + part of speech,
    gender, case/number or person/tense/mood/voice) underneath -- the way
    an interlinear study Bible glosses each word. Chunks with no Latin word
    in them (e.g. a bare em dash) are passed through as plain text.
    """
    out = []
    pos = 0
    for m in CHUNK_RE.finditer(paragraph_text):
        start, end = m.span()
        if start > pos:
            out.append(html.escape(paragraph_text[pos:start]))
        chunk = m.group(0)

        word_match = WORD_RE.search(chunk)
        if not word_match:
            out.append(html.escape(chunk))
            pos = end
            continue

        prefix = html.escape(chunk[: word_match.start()])
        suffix = html.escape(chunk[word_match.end() :])
        word = word_match.group(0)
        lookup = re.sub(r"'.*$", "", word).lower()
        safe_word = html.escape(word)
        href = f"https://logeion.uchicago.edu/{lookup}"

        analysis = morph.analyze(word)
        gloss_html = ""
        extra_attrs = ""
        if analysis:
            tag_text = analysis["tag"]
            gloss_text = html.escape(f"{analysis['lemma']} · {tag_text}")
            gloss_html = f'<span class="gloss">{gloss_text}</span>'

            english = senses.gloss(word, analysis["lemma"], analysis["pos_code"], analysis["gender_code"])
            extra_attrs = (
                f' data-lemma="{html.escape(analysis["lemma"])}"'
                f' data-tag="{html.escape(tag_text)}"'
                f' data-gloss="{html.escape(english)}"'
            )

        out.append(
            f'<span class="w-wrap">'
            f'<span class="wtop">{prefix}'
            f'<a class="w" href="{href}" rel="noopener" '
            f'data-word="{safe_word}"{extra_attrs}>{safe_word}</a>{suffix}</span>'
            f'{gloss_html}'
            f'</span>'
        )
        pos = end
    if pos < len(paragraph_text):
        out.append(html.escape(paragraph_text[pos:]))
    return "".join(out)


PAGE_TEMPLATE = """<!doctype html>
<html lang="la">
<head>
<meta charset="utf-8">
<title>Confessiones {roman} — Confessions Word Guide</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header class="topbar">
  <a class="home" href="../index.html">&larr; Index</a>
  <h1>AVGVSTINI CONFESSIONVM {title_upper}</h1>
  <nav class="booknav">
    <button id="translation-toggle" class="toggle-btn" aria-pressed="true">Hide translation</button>
    {prev_link}{next_link}
  </nav>
</header>
<main>
{sections}
</main>
<footer>
  <p>Latin text: The Latin Library / J. J. O'Donnell edition (public domain). English translation: Albert C. Outler's 1955 translation (released to the public domain by the translator), via <a href="https://en.wikisource.org/wiki/The_Confessions_of_Saint_Augustine_(Outler)" target="_blank" rel="noopener">Wikisource</a>. Word lookups: <a href="https://logeion.uchicago.edu/" target="_blank" rel="noopener">Logeion</a> (University of Chicago), aggregating Lewis &amp; Short and Perseus morphological data. Click any word to open its full dictionary entry, declension/conjugation, and grammatical parse in the side panel.</p>
</footer>

{shared_widgets}

<script src="../app.js"></script>
</body>
</html>
"""

SHARED_WIDGETS = """
<div id="word-tooltip" class="word-tooltip" hidden></div>

<div id="panel-overlay" class="panel-overlay" hidden></div>
<aside id="word-panel" class="word-panel" hidden>
  <div class="panel-header">
    <span id="panel-title"></span>
    <a id="panel-newtab" class="panel-newtab" href="#" target="_blank" rel="noopener" title="Open in a new tab">open in new tab &#8599;</a>
    <button id="panel-close" class="panel-close" aria-label="Close">&times;</button>
  </div>
  <iframe id="panel-frame" class="panel-frame" title="Logeion dictionary lookup"></iframe>
</aside>

<button id="cheatsheet-btn" class="fab" title="Morphology abbreviations">?</button>
<aside id="cheatsheet-panel" class="cheatsheet" hidden>
  <div class="panel-header">
    <span>Morphology abbreviations</span>
    <button id="cheatsheet-close" class="panel-close" aria-label="Close">&times;</button>
  </div>
  <div class="cheatsheet-body">
    <section>
      <h3>Part of speech</h3>
      <dl>
        <div><dt>noun</dt><dd>noun</dd></div>
        <div><dt>adj.</dt><dd>adjective</dd></div>
        <div><dt>adj./pron.</dt><dd>adjective used as a pronoun (e.g. <em>is, hic, ipse</em>)</dd></div>
        <div><dt>verb</dt><dd>verb</dd></div>
        <div><dt>pron.</dt><dd>pronoun</dd></div>
        <div><dt>adv.</dt><dd>adverb</dd></div>
        <div><dt>prep.</dt><dd>preposition</dd></div>
        <div><dt>conj.</dt><dd>conjunction</dd></div>
        <div><dt>interj.</dt><dd>interjection</dd></div>
        <div><dt>num.</dt><dd>numeral</dd></div>
      </dl>
    </section>
    <section>
      <h3>Case</h3>
      <dl>
        <div><dt>nom.</dt><dd>nominative &mdash; subject</dd></div>
        <div><dt>voc.</dt><dd>vocative &mdash; direct address</dd></div>
        <div><dt>acc.</dt><dd>accusative &mdash; direct object</dd></div>
        <div><dt>gen.</dt><dd>genitive &mdash; possession, "of ..."</dd></div>
        <div><dt>dat.</dt><dd>dative &mdash; indirect object, "to/for ..."</dd></div>
        <div><dt>abl.</dt><dd>ablative &mdash; "by/with/from ..."</dd></div>
        <div><dt>loc.</dt><dd>locative &mdash; place where</dd></div>
      </dl>
    </section>
    <section>
      <h3>Number &amp; gender</h3>
      <dl>
        <div><dt>sg.</dt><dd>singular</dd></div>
        <div><dt>pl.</dt><dd>plural</dd></div>
        <div><dt>m.</dt><dd>masculine</dd></div>
        <div><dt>f.</dt><dd>feminine</dd></div>
        <div><dt>n.</dt><dd>neuter</dd></div>
      </dl>
    </section>
    <section>
      <h3>Mood</h3>
      <dl>
        <div><dt>ind.</dt><dd>indicative &mdash; statement of fact</dd></div>
        <div><dt>subj.</dt><dd>subjunctive &mdash; wish, possibility, purpose, etc.</dd></div>
        <div><dt>imperat.</dt><dd>imperative &mdash; command</dd></div>
        <div><dt>inf.</dt><dd>infinitive &mdash; "to ..."</dd></div>
        <div><dt>part.</dt><dd>participle &mdash; verbal adjective</dd></div>
        <div><dt>gerund</dt><dd>gerund &mdash; verbal noun</dd></div>
        <div><dt>supine</dt><dd>supine &mdash; verbal noun of purpose</dd></div>
      </dl>
    </section>
    <section>
      <h3>Tense</h3>
      <dl>
        <div><dt>pres.</dt><dd>present</dd></div>
        <div><dt>impf.</dt><dd>imperfect</dd></div>
        <div><dt>fut.</dt><dd>future</dd></div>
        <div><dt>perf.</dt><dd>perfect</dd></div>
        <div><dt>plup.</dt><dd>pluperfect</dd></div>
        <div><dt>fut. perf.</dt><dd>future perfect</dd></div>
      </dl>
    </section>
    <section>
      <h3>Voice &amp; person</h3>
      <dl>
        <div><dt>act.</dt><dd>active</dd></div>
        <div><dt>pass.</dt><dd>passive</dd></div>
        <div><dt>1, 2, 3</dt><dd>first, second, third person</dd></div>
      </dl>
    </section>
  </div>
</aside>
"""

SECTION_TEMPLATE = """<section class="chapter" id="{sid}">
  <span class="secnum">{display}</span>
  <p class="latin">{body}</p>
  <p class="translation">{translation}</p>
</section>
"""


def display_label(sid: str) -> str:
    """
    The source's citation is Book.Chapter.Paragraph (e.g. "1.5.6" = Book 1,
    chapter 5, paragraph 6). Most reading editions and translations cite by
    Book.Paragraph only -- the paragraph number already runs continuously
    and uniquely through the whole book, so the chapter digit is dropped
    here to match what a reader following along in a translation expects
    (e.g. Book 1's 31 paragraphs shown as "1.1" through "1.31").
    """
    parts = sid.split(".")
    if len(parts) == 3:
        return f"{parts[0]}.{parts[2]}"
    return sid


def build_book(n: int):
    raw_path = RAW / f"conf{n}.html"
    if not raw_path.exists():
        print(f"skip book {n}: no raw file", file=sys.stderr)
        return
    raw_html = raw_path.read_text(encoding="utf-8", errors="replace")
    paragraphs = extract_paragraphs(raw_html)

    english = TRANSLATIONS.get(str(n), [])
    if english and len(english) != len(paragraphs):
        print(
            f"warning: book {n} has {len(paragraphs)} Latin paragraphs but "
            f"{len(english)} English ones -- translation alignment will be off",
            file=sys.stderr,
        )

    sections_html = []
    for i, (sid, text) in enumerate(paragraphs):
        body = tokenize_to_html(text)
        sid_label = sid or ""
        translation = html.escape(english[i]) if i < len(english) else ""
        sections_html.append(
            SECTION_TEMPLATE.format(
                sid=sid_label, display=display_label(sid_label), body=body, translation=translation
            )
        )

    prev_link = f'<a href="conf{n-1}.html">&laquo; {ROMAN[n-1]}</a>' if n > 1 else ""
    next_link = f'<a href="conf{n+1}.html">{ROMAN[n+1]} &raquo;</a>' if n < 13 else ""

    page = PAGE_TEMPLATE.format(
        roman=ROMAN[n],
        title_upper=BOOK_TITLES[n].upper(),
        sections="\n".join(sections_html),
        prev_link=prev_link,
        next_link=next_link,
        shared_widgets=SHARED_WIDGETS,
    )
    out_path = OUT / f"conf{n}.html"
    out_path.write_text(page, encoding="utf-8")
    print(f"wrote {out_path} ({len(paragraphs)} sections)")


if __name__ == "__main__":
    books = [int(a) for a in sys.argv[1:]] or [1]
    for b in books:
        build_book(b)
