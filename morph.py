"""
Latin morphological analysis for the Confessions word guide.

Wraps pycollatinus (a Python port of the Collatinus lexicon/analyzer) to
produce, for each attested word form, a short English parse label:
lemma, part of speech, gender (nouns/adjectives/pronouns), and full
case/number or person/tense/mood/voice for inflected forms.

Ambiguous forms (several possible lemmas/parses) are disambiguated by
picking the candidate whose lemma has the highest corpus frequency
(nbOcc) in the Collatinus lexicon -- the most probable reading absent
sentence context. The word itself still links out to Logeion so a
reader can check the alternatives and see the full paradigm.
"""
import functools
import re
from pathlib import Path

from pycollatinus import Lemmatiseur

_PYCOLLATINUS_DATA = Path(
    __import__("pycollatinus").__file__
).parent / "data" / "lemmes.la"

POS_EN = {
    "n": "noun",
    "a": "adj.",
    "ap": "adj./pron.",
    "v": "verb",
    "d": "adv.",
    "p": "pron.",
    "r": "prep.",
    "cd": "conj.",
    "cs": "conj.",
    "c": "conj.",
    "e": "interj.",
    "i": "interj.",
    "m": "num.",
    "nnum": "num.",
    "x": "",
}

CASE_EN = {
    "nominatif": "nom.",
    "vocatif": "voc.",
    "accusatif": "acc.",
    "génitif": "gen.",
    "datif": "dat.",
    "ablatif": "abl.",
    "locatif": "loc.",
}
GENDER_EN = {"masculin": "m.", "féminin": "f.", "neutre": "n."}
NUMBER_EN = {"singulier": "sg.", "pluriel": "pl."}
MOOD_EN = {
    "indicatif": "ind.",
    "subjonctif": "subj.",
    "impératif": "imperat.",
    "infinitif": "inf.",
    "participe": "part.",
    "gérondif": "gerund",
    "supin": "supine",
}
TENSE_EN = {
    "présent": "pres.",
    "imparfait": "impf.",
    "futur": "fut.",
    "futur antérieur": "fut. perf.",
    "parfait": "perf.",
    "PQP": "plup.",
}
VOICE_EN = {"actif": "act.", "passif": "pass."}
PERSON_EN = {"1ère": "1", "2ème": "2", "3ème": "3"}
DEGREE_EN = {"positif": "pos.", "comparatif": "comp.", "superlatif": "superl."}

_ALL_TOKENS = {
    **CASE_EN, **GENDER_EN, **NUMBER_EN, **MOOD_EN,
    **TENSE_EN, **VOICE_EN, **PERSON_EN, **DEGREE_EN,
}


def _translate_morph(morph: str) -> str:
    """Turn a Collatinus French morph phrase into a short English tag string."""
    if not morph or morph == "-":
        return ""
    parts = morph.replace("futur antérieur", "futurantérieur").split()
    out = []
    for tok in parts:
        if tok == "futurantérieur":
            out.append(TENSE_EN["futur antérieur"])
        else:
            out.append(_ALL_TOKENS.get(tok, tok))
    return " ".join(out)


@functools.lru_cache(maxsize=1)
def _load_lemmatiseur() -> Lemmatiseur:
    l = Lemmatiseur()
    try:
        l.load()
    except FileNotFoundError:
        l = Lemmatiseur(load=False)
        l.compile()
        l.load()
    return l


@functools.lru_cache(maxsize=1)
def _load_gender_map() -> dict:
    """lemma key (accent-stripped, homonym-suffix stripped) -> 'm'/'f'/'n'/'m/f' etc."""
    from pycollatinus.ch import atone

    gender_map = {}
    gender_re = re.compile(r"\b(m|f|n)\.(?:\s*/\s*(m|f|n)\.)?")
    for fname in ("lemmes.la", "lem_ext.la"):
        path = _PYCOLLATINUS_DATA.parent / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("!"):
                continue
            fields = line.split("|")
            if len(fields) < 5:
                continue
            head = fields[0].split("=")[0]
            key = atone(head).rstrip("0123456789").lower()
            note = fields[4]
            m = gender_re.search(note)
            if m:
                g = m.group(1)
                if m.group(2) and m.group(2) != g:
                    g = g + "/" + m.group(2)
                gender_map.setdefault(key, g)
    return gender_map


GENDER_LABEL = {"m": "m.", "f": "f.", "n": "n.", "m/f": "m./f.", "f/n": "f./n.", "m/n": "m./n."}


@functools.lru_cache(maxsize=1)
def _lemma_freq_cache() -> dict:
    return {}


# Grammatical categories that are rare in running text relative to how
# often their bare inflection pattern happens to overlap with a far more
# common word's ending (e.g. genitive singular of a rare future-active-
# participle reading vs. a common noun). Down-weight them so raw lemma
# frequency doesn't let an unlikely reading win a coincidental tie.
_RARE_MORPH_MARKERS = (
    "participe futur",
    "participe parfait passif",
    "gérondif",
    "supin",
    "locatif",
)


def _form_prior(morph: str) -> float:
    morph = morph or ""
    for marker in _RARE_MORPH_MARKERS:
        if marker in morph:
            return 0.005
    return 1.0


def _lemma_lookup(lemmatiseur: Lemmatiseur, lemma_key: str):
    """
    Collatinus's own candidate list sometimes returns a lemma spelled with
    "j"/"v" (e.g. "jam") when the lexicon actually stores it under "i"/"u"
    ("iam") or vice versa -- an internal inconsistency, not something we
    control. A direct dict lookup then raises KeyError even though the
    lemma genuinely exists, which silently zeroes its frequency and lets a
    coincidental rival win. Try the classical-spelling variants too.
    """
    for key in (lemma_key, lemma_key.replace("j", "i"), lemma_key.replace("v", "u")):
        try:
            return lemmatiseur.lemme(key)
        except KeyError:
            continue
    return None


def _lemma_nboc(lemmatiseur: Lemmatiseur, lemma_key: str) -> int:
    cache = _lemma_freq_cache()
    if lemma_key in cache:
        return cache[lemma_key]
    obj = _lemma_lookup(lemmatiseur, lemma_key)
    n = obj._nbOcc if obj is not None else 0
    cache[lemma_key] = n
    return n


# Collatinus's bundled frequency corpus badly undercounts the relative
# pronoun "qui/quae/quod" (one of the most common words in Latin, since
# relative clauses are everywhere) against rarer pronouns it happens to
# share forms with -- but only *pronoun* rivals ("quis", "quidam", ...);
# "quod" the causal conjunction is a separate, genuinely more frequent
# word and must keep winning its own ties on real frequency.
_QUI_RIVAL_PRONOUNS = {"quis", "quidam", "quiuis", "quisquam", "quisque"}


def _rank_score(lemmatiseur: Lemmatiseur, candidate: dict, sibling_lemmas: frozenset) -> float:
    score = _lemma_nboc(lemmatiseur, candidate["lemma"]) * _form_prior(candidate.get("morph", ""))
    if (
        candidate.get("pos") == "p"
        and candidate["lemma"] in _QUI_RIVAL_PRONOUNS
        and "qui" in sibling_lemmas
    ):
        score *= 0.005
    return score


# Some case/number pairs are genuinely indistinguishable from the bare word
# form alone (e.g. 3rd-declension i-stem adjectives: nom. sg. == gen. sg.
# for "laudabilis"). When two candidates of the *same* lemma tie on score,
# prefer the more "citation-form" reading as a sane default -- a reader
# clicking through to Logeion can see the rest.
_CASE_PRIORITY = {
    "nominatif": 6, "accusatif": 5, "génitif": 4,
    "ablatif": 3, "datif": 2, "vocatif": 1, "locatif": 0,
}
_MOOD_PRIORITY = {
    "infinitif": 4, "indicatif": 3, "subjonctif": 2, "impératif": 1, "participe": 0,
}


def _tiebreak_key(morph: str, pos: str) -> tuple:
    """
    Break same-lemma, same-frequency ties with a plausibility default: for
    verbs, prefer common moods/active voice; for nominal forms, prefer the
    singular and then the more "citation-form" case. These two dimensions
    don't mix (e.g. an infinitive has no number), so branch on POS rather
    than scoring every candidate on every axis.
    """
    morph = morph or ""

    if pos == "v":
        mood_rank = 0
        for word_fr, rank in _MOOD_PRIORITY.items():
            if word_fr in morph:
                mood_rank = rank
                break
        voice_rank = 1 if "actif" in morph else 0
        return (mood_rank, voice_rank)

    case_rank = 0
    for word_fr, rank in _CASE_PRIORITY.items():
        if morph.startswith(word_fr):
            case_rank = rank
            break
    number_rank = 1 if "singulier" in morph else 0
    return (number_rank, case_rank)


# People and places from Augustine's own life -- classical Latin lexicons
# (Collatinus included) have no entry for them at all, so Collatinus
# returns zero candidates. A small hand-built fallback for the ones that
# recur through the narrative, so at least these aren't left completely
# unlabeled. Case guessed from the ending; these are proper nouns, so it's
# a minor detail next to just identifying who/where it is.
_PROPER_NOUN_FALLBACK = {
    "alypius": ("alypius", "nom. sg."),
    "alypio": ("alypius", "dat./abl. sg."),
    "alypium": ("alypius", "acc. sg."),
    "monnica": ("monnica", "nom. sg."),
    "monnicae": ("monnica", "gen./dat. sg."),
    "ponticianus": ("ponticianus", "nom. sg."),
    "romanianus": ("romanianus", "nom. sg."),
    "simplicianus": ("simplicianus", "nom. sg."),
    "simpliciano": ("simplicianus", "dat./abl. sg."),
    "simplicianum": ("simplicianus", "acc. sg."),
    "vindicianus": ("vindicianus", "nom. sg."),
    "vindiciano": ("vindicianus", "dat./abl. sg."),
    "elpidius": ("elpidius", "nom. sg."),
    "elpidii": ("elpidius", "gen. sg."),
    "hierius": ("hierius", "nom. sg."),
    "hierium": ("hierius", "acc. sg."),
    "cassiciacum": ("cassiciacum", "nom./acc. sg."),
    "cassiciaco": ("cassiciacum", "abl. sg."),
    "hierusalem": ("hierusalem", "indecl."),
    "hippocraten": ("hippocrates", "acc. sg. (Greek)"),
    "helias": ("helias", "nom. sg."),
    "heliam": ("helias", "acc. sg."),
    "thagastensis": ("thagastensis", "nom./gen. sg."),
    "thagastensi": ("thagastensis", "abl. sg."),
    "daviticum": ("daviticus", "acc. sg."),
    "genesis": ("genesis", "nom. sg. (Greek)"),
    "geneseos": ("genesis", "gen. sg. (Greek)"),
    "martyum": ("martyr", "gen. pl. (syncopated for martyrum)"),
}
_COMMON_NOUN_FALLBACK = {"martyum"}


@functools.lru_cache(maxsize=None)
def analyze(word: str):
    """
    Return the best-guess morphological analysis of a Latin word form, or
    None if the analyzer has no entry for it.
    """
    l = _load_lemmatiseur()
    candidates = list(l.lemmatise(word.lower(), pos=True))
    if not candidates:
        fallback = _PROPER_NOUN_FALLBACK.get(word.lower())
        if fallback:
            lemma, case_tag = fallback
            kind = "noun" if word.lower() in _COMMON_NOUN_FALLBACK else "proper noun"
            return {
                "lemma": lemma,
                "pos": "noun",
                "pos_code": "n",
                "gender_code": "",
                "tag": f"{kind}, {case_tag}",
                "ambiguous": False,
            }
        return None

    # Prefer candidates that match the queried form exactly over ones
    # produced by Collatinus's fuzzy suffix-reduction fallback (which can
    # surface spurious unrelated readings, e.g. "domine" -> "domi").
    exact = [c for c in candidates if c.get("form", "").lower() == word.lower()]
    if exact:
        candidates = exact

    sibling_lemmas = frozenset(c["lemma"] for c in candidates)
    best = max(
        candidates,
        key=lambda c: (
            _rank_score(l, c, sibling_lemmas),
            _tiebreak_key(c.get("morph", ""), c.get("pos", "")),
        ),
    )

    # "j" never appears in a genuine Latin dictionary headword (it's just
    # an old typographical variant of consonantal "i"); Collatinus's own
    # candidate list is inconsistent about this, so normalize it away.
    lemma_display = best["lemma"].lower().replace("j", "i")
    pos_code = best.get("pos", "")
    pos_label = POS_EN.get(pos_code, pos_code)
    morph_label = _translate_morph(best.get("morph", ""))

    gender_map = _load_gender_map()
    from pycollatinus.ch import atone
    gender_code = gender_map.get(atone(lemma_display))
    gender_label = GENDER_LABEL.get(gender_code, "") if gender_code else ""

    # Nouns have one fixed gender not reflected in the per-form morph string
    # (unlike adjectives/pronouns, whose morph string already varies gender
    # by form) -- so only nouns need the gender spliced in separately.
    if pos_code == "n" and gender_label:
        tag = f"{pos_label} ({gender_label}) {morph_label}".strip()
    else:
        tag = f"{pos_label} {morph_label}".strip()

    return {
        "lemma": lemma_display,
        "pos": pos_label,
        "pos_code": pos_code,
        "gender_code": gender_code or "",
        "tag": tag,
        "ambiguous": len({c["lemma"] for c in candidates}) > 1,
    }


if __name__ == "__main__":
    import sys
    for w in sys.argv[1:] or ["es", "magnus", "domine", "et", "sapientiae", "ego", "qui"]:
        print(w, "->", analyze(w))
