# Confessions Word Guide

A word-by-word interlinear reading edition of Augustine's *Confessiones*, in the original Latin. Every word shows its lemma, part of speech, gender, and full case/mood/tense/voice parse; hover for a short English gloss, click to open the full dictionary entry (via [Logeion](https://logeion.uchicago.edu/)) in a side panel without leaving the page. A public-domain English translation runs underneath each paragraph (toggleable) so you can follow along without knowing Latin.

All thirteen books are built. Everything is static, pre-rendered HTML/CSS/JS -- no build step, no framework, no server -- which is deliberate: all the content (Latin text, morphology, translation) is computed once at build time, and the interactive parts (hover tooltip, dictionary panel, cheat sheet, chapter navigation) are a few hundred lines of plain JS with no real client-side state to justify something like Svelte or React.

## Viewing it

Open `index.html` in a browser, or (once published) visit the GitHub Pages URL for this repo.

## Page structure

Each book has a table-of-contents page (`books/confN.html`) with a summary and a list of chapters, and one page per chapter (`books/confN/C.html`) with that chapter's interlinear Latin, morphology, and English translation -- rather than one huge page per book (Book X alone has 70 paragraphs across 43 chapters). Chapters are the traditional Book.Chapter divisions from the critical edition, so "Caput 5" means the same thing here as in any print edition or translation.

## How it's built

- **Text**: public-domain Latin text from [The Latin Library](https://www.thelatinlibrary.com/august.html) (J. J. O'Donnell's edition), fetched into `raw/`.
- **Morphology**: [Collatinus](https://github.com/PonteIneptique/pycollatinus) (via `pycollatinus`) parses every word form offline — lemma, part of speech, case/number/gender or person/tense/mood/voice. Ambiguous forms are resolved with a frequency- and plausibility-based heuristic in `morph.py`; the word always links out to Logeion so you can check alternatives.
- **English glosses**: short hover definitions are cross-referenced from Whitaker's Words' dictionary (`senses.py`), plus a small hand-curated list for common function words (pronouns, conjunctions, etc.) it handles poorly.
- **English translation**: Albert C. Outler's 1955 translation, released to the public domain by the translator, from [Wikisource](https://en.wikisource.org/wiki/The_Confessions_of_Saint_Augustine_(Outler)) (`raw_en/outler/`), extracted paragraph-by-paragraph in `extract_translation.py` into `translation.json` and `book_summaries.json`. Outler's text is itself numbered "1. ... 2. ... 3. ..." using the same standard Book.Paragraph scheme as the Latin, so no heuristic alignment is needed -- paragraph N in the source *is* Latin section N (an earlier version of this used Pusey's 1838 translation via Project Gutenberg, whose paragraph breaks required guesswork to line up; Outler's explicit numbering, and noticeably more modern English, is why it replaced Pusey).
- **Rendering**: `build.py` groups each book's paragraphs by chapter (from the Book.Chapter.Paragraph id) and generates one TOC page plus one page per chapter in `books/confN/`.

## Regenerating / adding a book

```bash
pip install "git+https://github.com/ArchimedesDigital/open_words.git" pycollatinus
```

`pycollatinus` on PyPI is not Python 3.10+ compatible out of the box; if `import pycollatinus` fails with a `Callable` import error, edit `pycollatinus/util.py` in your site-packages to import `Callable` from `collections.abc` instead of `collections`, then compile its lexicon once:

```bash
python3 -c "from pycollatinus import Lemmatiseur; l = Lemmatiseur(load=False); l.compile()"
```

Then, to add another book:

```bash
curl -s "https://www.thelatinlibrary.com/augustine/conf3.shtml" -o raw/conf3.html
python3 build.py 3
```

and add its `<li>` entry in `index.html`.

## Attribution

- Latin text: The Latin Library / J. J. O'Donnell's electronic edition (public domain).
- English translation: Albert C. Outler, *The Confessions of Saint Augustine* (1955), released to the public domain by the translator, via [Wikisource](https://en.wikisource.org/wiki/The_Confessions_of_Saint_Augustine_(Outler)).
- Word lookups: [Logeion](https://logeion.uchicago.edu/), University of Chicago.
- Morphology: [Collatinus](https://github.com/biblissima/collatinus) / [pycollatinus](https://github.com/PonteIneptique/pycollatinus).
- English glosses: [Whitaker's Words](https://mk270.github.io/whitakers-words/) via the [Open Words](https://github.com/ArchimedesDigital/open_words) Python port.
