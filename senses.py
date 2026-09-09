"""
Short English glosses for the hover tooltip, cross-referenced from
Whitaker's Words' dictionary (open_words port) against the lemma that
morph.py (Collatinus) determined -- Collatinus itself carries no English
definitions, only morphology, so this fills that one gap without a
network call. Whitaker's own grammar engine is unreliable (see morph.py's
docstring history) but its dictionary glosses are fine; we only ever use
its "senses" text, never its parsing.
"""
import functools
import re

from open_words.dict_line import WordsDict
from open_words.uniques import Uniques

_POS_BUCKET = {
    "n": "N", "a": "ADJ", "ap": "ADJ", "v": "V", "d": "ADV",
    "p": "PRON", "r": "PREP", "cd": "CONJ", "cs": "CONJ", "c": "CONJ",
    "e": "INTERJ", "i": "INTERJ", "m": "NUM",
}

_GENDER_RE = re.compile(r"\b([MFNC])\b")


def _norm(s: str) -> str:
    """
    Collatinus and Whitaker's Words don't agree on classical vs. modern
    orthography -- Collatinus's lemma citation forms mix "u" and "v"
    inconsistently (e.g. "dominus" but "uolo" for volo), while Whitaker's
    dictionary stems use "v"/"j" consistently. Normalize both sides to u/i
    before comparing so a lemma like "uideo" still matches Whitaker's
    "vide" stem.
    """
    return s.lower().replace("v", "u").replace("j", "i")

# Whitaker's dictionary stem-matching is unreliable for short, closed-class
# words (pronouns, conjunctions, common prepositions/adverbs) -- either the
# minimum stem length excludes them, or the stem collides with an unrelated
# entry (e.g. "qui" matching an adverbial "how?" homonym instead of the
# relative pronoun). These are a small, fixed set worth hand-curating once,
# since they're also some of the highest-frequency words in any Latin text.
_LEMMA_GLOSS_OVERRIDE = {
    "qui": "who, which, that",
    "quis": "who?, which?, what?",
    "quidam": "a certain one/thing, someone, something",
    "quisquam": "anyone, anything (at all)",
    "quisque": "each, each one, every",
    "quiuis": "anyone/anything you like",
    "quod": "because, in that, the fact that",
    "tu": "you (sg.)",
    "ego": "I",
    "nos": "we, us",
    "uos": "you (pl.)",
    "vos": "you (pl.)",
    "se": "himself, herself, itself, themselves",
    "suus": "his/her/its/their own",
    "hic": "this",
    "ille": "that",
    "is": "he, she, it; that",
    "ipse": "himself, herself, itself (emphatic)",
    "idem": "the same",
    "et": "and",
    "sed": "but",
    "aut": "or",
    "uel": "or (else)",
    "vel": "or (else)",
    "atque": "and (also), and moreover",
    "ac": "and",
    "nec": "and not, nor",
    "neque": "and not, nor",
    "non": "not",
    "ne": "not; lest, that ... not",
    "si": "if",
    "nisi": "if not, unless, except",
    "ut": "that, so that, as, when",
    "cum": "when, since, although; with",
    "enim": "for, indeed",
    "autem": "but, however, moreover",
    "tamen": "nevertheless, still, yet",
    "etiam": "also, even, still",
    "iam": "now, already, soon",
    "quoniam": "since, because",
    "quia": "because",
    "an": "or, whether",
    "in": "in, on, into, against",
    "ad": "to, toward, at, near",
    "ex": "out of, from",
    "de": "down from, concerning, about",
    "per": "through, by means of",
    "pro": "for, on behalf of, in front of",
    "sine": "without",
    "sum": "to be, exist",
    "possum": "to be able, can",
    "uolo": "to want, wish, be willing",
    "volo": "to want, wish, be willing",
    "eo": "to go",
    "queo": "to be able",
    "nescio": "to not know",
    "laudo": "to praise",
    "iam": "now, already, soon",
    "spes": "hope",
    "inquam": "I say, said I (used mid-quotation)",
    "tecum": "with you (sg.)",
    "mecum": "with me",
    "homerus": "Homer (the Greek poet)",
    "imus": "lowest, deepest",
    "imum": "lowest, deepest",
    "vepres": "thorn-bush, bramble",
}


@functools.lru_cache(maxsize=1)
def _unique_form_map() -> dict:
    """Exact surface-form -> first sense, for irregular forms (sum, es, est, ...)."""
    m = {}
    for u in Uniques:
        orth = u.get("orth", "").lower()
        senses = u.get("senses") or []
        if orth and senses and orth not in m:
            m[orth] = senses[0].strip(" ;")
    return m


@functools.lru_cache(maxsize=1)
def _stem_index() -> dict:
    """normalized stem -> list of dict_line entries sharing that stem."""
    idx = {}
    for e in WordsDict:
        stem = _norm(e.get("orth") or "")
        if not stem:
            continue
        idx.setdefault(stem, []).append(e)
    return idx


def _pick_entry(entries: list, pos_bucket: str, gender_letter: str, require_pos: bool = False):
    # Prefer entries matching our POS bucket. For very short stems (1-2
    # letters), a random cross-POS collision is likely, so require an
    # actual POS match rather than falling back to "whatever's there".
    pos_matches = [e for e in entries if e.get("pos") == pos_bucket]
    if not pos_matches and not require_pos:
        pos_matches = entries
    if not pos_matches:
        return None

    if gender_letter:
        gender_matches = []
        for e in pos_matches:
            m = _GENDER_RE.search(e.get("form", ""))
            if m and m.group(1) == gender_letter:
                gender_matches.append(e)
        if gender_matches:
            pos_matches = gender_matches

    return pos_matches[0] if pos_matches else None


@functools.lru_cache(maxsize=4096)
def gloss(word: str, lemma: str, pos_code: str, gender_code: str = "") -> str:
    """
    Best-effort short English gloss for a word, given the lemma and POS
    Collatinus already determined. Returns "" if nothing plausible found.
    """
    word_l = word.lower()
    lemma_l = lemma.lower()

    override = _LEMMA_GLOSS_OVERRIDE.get(lemma_l)
    if override:
        return override

    unique_hit = _unique_form_map().get(word_l)
    if unique_hit:
        return unique_hit

    pos_bucket = _POS_BUCKET.get(pos_code, "")
    gender_letter = gender_code[0].upper() if gender_code else ""

    stem_index = _stem_index()
    lemma_norm = _norm(lemma_l)
    for length in range(len(lemma_norm), 0, -1):
        stem = lemma_norm[:length]
        entries = stem_index.get(stem)
        if not entries:
            continue
        entry = _pick_entry(entries, pos_bucket, gender_letter, require_pos=length <= 2)
        if entry and entry.get("senses"):
            return entry["senses"][0].strip(" ;|")
    return ""


if __name__ == "__main__":
    import sys
    import morph

    for w in sys.argv[1:] or ["dominus", "es", "magnus", "virtus", "laudo", "creatura"]:
        a = morph.analyze(w)
        if not a:
            print(w, "-> no morph analysis")
            continue
        g = gloss(w, a["lemma"], a["pos_code"], a["gender_code"])
        print(w, "->", a["lemma"], "|", a["tag"], "|", g)
