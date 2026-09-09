# Confessions Word Guide

A word-by-word interlinear reading edition of Augustine's *Confessiones*, in the original Latin. Every word shows its lemma, part of speech, gender, and full case/mood/tense/voice parse; hover for a short English gloss, click to open the full dictionary entry (via [Logeion](https://logeion.uchicago.edu/)) in a side panel without leaving the page. A public-domain English translation runs underneath each paragraph (toggleable) so you can follow along without knowing Latin.

All thirteen books are built.

## Viewing it

Open `index.html` in a browser, or (once published) visit the GitHub Pages URL for this repo.

## How it's built

- **Text**: public-domain Latin text from [The Latin Library](https://www.thelatinlibrary.com/august.html) (J. J. O'Donnell's edition), fetched into `raw/`.
- **Morphology**: [Collatinus](https://github.com/PonteIneptique/pycollatinus) (via `pycollatinus`) parses every word form offline — lemma, part of speech, case/number/gender or person/tense/mood/voice. Ambiguous forms are resolved with a frequency- and plausibility-based heuristic in `morph.py`; the word always links out to Logeion so you can check alternatives.
- **English glosses**: short hover definitions are cross-referenced from Whitaker's Words' dictionary (`senses.py`), plus a small hand-curated list for common function words (pronouns, conjunctions, etc.) it handles poorly.
- **English translation**: E. B. Pusey's 1838 translation (public domain), from [Project Gutenberg #3296](https://www.gutenberg.org/ebooks/3296), extracted paragraph-by-paragraph in `extract_translation.py` into `translation.json`. Pusey's paragraph breaks line up with the standard Book.Paragraph numbering almost everywhere; the handful of books where he merged or split a section differently are patched by hand in that script (see `_MERGE_AT`/`_SPLIT_AT`).
- **Rendering**: `build.py` tokenizes each paragraph and generates the static HTML pages in `books/`.

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
- English translation: E. B. Pusey, *The Confessions of S. Augustine* (1838), public domain, via [Project Gutenberg](https://www.gutenberg.org/ebooks/3296).
- Word lookups: [Logeion](https://logeion.uchicago.edu/), University of Chicago.
- Morphology: [Collatinus](https://github.com/biblissima/collatinus) / [pycollatinus](https://github.com/PonteIneptique/pycollatinus).
- English glosses: [Whitaker's Words](https://mk270.github.io/whitakers-words/) via the [Open Words](https://github.com/ArchimedesDigital/open_words) Python port.
