"""
Regex / word-list baseline extractor for QUANTITY, UNIT, INGREDIENT, PREP.

This is the "no machine learning" comparison point. It uses hand-written
rules that encode the typical word order of an ingredient line:

    QUANTITY -> UNIT -> (PREP) -> INGREDIENT -> (PREP)
    e.g.  "2 tbsp finely chopped coriander"

The QUANTITY/UNIT rules are also reused by prelabel.py for pre-annotation.

Usage:
    python src/baseline.py                      # tag a few sample lines
    python src/baseline.py "2 tbsp ghee"        # tag one line
    python src/baseline.py --eval               # score on data/spacy/test.spacy
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- QUANTITY ----------
# A number can be: 2 | 1.5 | 1/2 | ½ | 2 1/2 | 1½  (the unicode fractions are common on recipe sites)
FRACTION = r"[½¼¾⅓⅔⅛]"
NUMBER = rf"(?:\d+(?:\.\d+)?(?:\s+\d+/\d+|\s*{FRACTION}|/\d+)?|{FRACTION})"
# Ranges: "1-2", "2 - 3", "2 to 3"
NUMERIC_QTY = rf"{NUMBER}(?:\s*(?:-|–|to)\s*{NUMBER})?"
# Word quantities - the pragmatic, conventional ones ("to taste", "as needed")
WORD_QTY = (
    r"a\s+pinch|pinch|a\s+few|few|a\s+handful|handful|half|quarter|"
    r"to\s+taste|as\s+required|as\s+needed|as\s+per\s+taste"
)
QTY_RE = re.compile(rf"(?<![\w/]){NUMERIC_QTY}(?![\w/])|\b(?:{WORD_QTY})\b", re.IGNORECASE)

# ---------- UNIT ----------
# Measurement units: always a UNIT when they directly follow a quantity.
MEASURE_UNITS = (
    r"tbsps?\.?|tablespoons?|tsps?\.?|teaspoons?|cups?|"
    r"kgs?|kilograms?|gms?|grams?|g|mls?|millilitres?|milliliters?|litres?|liters?|l|"
    r"inch(?:es)?|pinch(?:es)?"
)
# Count units: "5 cloves garlic" -> UNIT, but "4 cloves" (the spice, laung) -> INGREDIENT.
# So these are only a UNIT when another word follows them.
COUNT_UNITS = r"cloves?|leaves|sprigs?|pods?|sticks?|strands?|pieces?|pcs|cubes?|bunch(?:es)?|nos?\.?"
UNIT_AFTER_QTY_RE = re.compile(
    rf"\s*(?:({MEASURE_UNITS})(?![\w])|({COUNT_UNITS})(?=\s+[A-Za-z]))",
    re.IGNORECASE,
)

# ---------- PREP ----------
PREP_WORDS = (
    r"chopped|sliced|diced|grated|minced|crushed|mashed|boiled|peeled|slit|halved|"
    r"cubed|shredded|julienned|soaked|roasted|toasted|fried|deseeded|cored|pureed|"
    r"beaten|whisked|melted|washed|drained|ground|powdered|cut|torn|"
    r"small|medium|large|big"          # size words are PREP by our annotation rules
)
ADVERBS = r"finely|roughly|thinly|coarsely|freshly|lightly|thickly"
PREP_UNIT = rf"(?:(?:{ADVERBS})\s+)?(?:{PREP_WORDS})"
PREP_RE = re.compile(
    rf"\b{PREP_UNIT}(?:\s*(?:,|and|&)\s*{PREP_UNIT})*(?:\s+overnight)?\b",
    re.IGNORECASE,
)

# ---------- INGREDIENT ----------
# Anything left over that is not a quantity/unit/prep and not one of these
# function words is treated as part of the ingredient name.
STOP_WORDS = {
    "of", "and", "or", "for", "to", "as", "a", "an", "the", "with", "into", "in",
    "per", "your", "about", "approx", "optional", "required", "needed", "taste",
    "garnish", "garnishing", "frying", "deep", "tempering", "cooking", "some",
    "more", "extra", "if", "use", "fresh",
}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def quantity_unit_spans(text):
    """Return (start, end, label) spans for QUANTITY and the UNIT right after it."""
    spans = []
    for m in QTY_RE.finditer(text):
        spans.append((m.start(), m.end(), "QUANTITY"))
        u = UNIT_AFTER_QTY_RE.match(text, m.end())
        if u:
            group = 1 if u.group(1) else 2
            spans.append((u.start(group), u.end(group), "UNIT"))
    return spans


def prep_spans(text):
    return [(m.start(), m.end(), "PREP") for m in PREP_RE.finditer(text)]


def ingredient_span(text, taken):
    """Pick the longest run of consecutive 'free' words as the INGREDIENT.
    Words inside brackets are ignored (usually translations, e.g. "(dhania)")."""
    def covered(s, e):
        return any(s < te and ts < e for ts, te, _ in taken)

    # character positions that are inside (...) brackets
    in_brackets = set()
    for m in re.finditer(r"\([^)]*\)?", text):
        in_brackets.update(range(m.start(), m.end()))

    best, current = None, []
    for m in WORD_RE.finditer(text):
        free = (
            m.group().lower() not in STOP_WORDS
            and not covered(m.start(), m.end())
            and m.start() not in in_brackets
        )
        # a run continues only if just whitespace separates it from the previous word
        if free and current and text[current[-1].end():m.start()].strip() == "":
            current.append(m)
        elif free:
            current = [m]
        else:
            current = []
        if current and (best is None or len(current) > len(best)):
            best = list(current)
    if best:
        return (best[0].start(), best[-1].end(), "INGREDIENT")
    return None


def remove_overlaps(spans):
    """Keep the earliest / longest span when two overlap."""
    result = []
    for s in sorted(spans, key=lambda x: (x[0], -(x[1] - x[0]))):
        if not result or s[0] >= result[-1][1]:
            result.append(s)
    return result


def extract(text):
    """Tag one ingredient line. Returns a list of dicts sorted by position."""
    spans = remove_overlaps(quantity_unit_spans(text))
    spans = remove_overlaps(spans + [p for p in prep_spans(text)
                                     if not any(p[0] < e and s < p[1] for s, e, _ in spans)])
    ing = ingredient_span(text, spans)
    if ing:
        spans = remove_overlaps(spans + [ing])
    return [{"start": s, "end": e, "label": l, "text": text[s:e]} for s, e, l in spans]


def evaluate_on_test():
    """Score the baseline on the gold test set with spaCy's own NER scorer,
    so the numbers are directly comparable to the trained model."""
    import spacy
    from spacy.tokens import DocBin
    from spacy.training import Example
    from spacy.scorer import Scorer

    nlp = spacy.blank("en")
    gold_docs = list(DocBin().from_disk(ROOT / "data" / "spacy" / "test.spacy").get_docs(nlp.vocab))
    examples = []
    for gold in gold_docs:
        pred = nlp.make_doc(gold.text)
        ents = []
        for sp in extract(gold.text):
            # snap the regex's character span to spaCy token boundaries
            span = pred.char_span(sp["start"], sp["end"], label=sp["label"], alignment_mode="expand")
            if span is not None:
                ents.append(span)
        pred.ents = spacy.util.filter_spans(ents)
        examples.append(Example(pred, gold))
    scores = Scorer.score_spans(examples, "ents")
    print(f"Baseline on test ({len(examples)} lines): "
          f"P={scores['ents_p']:.3f} R={scores['ents_r']:.3f} F1={scores['ents_f']:.3f}")
    for label, s in sorted(scores["ents_per_type"].items()):
        print(f"  {label:<11} P={s['p']:.3f} R={s['r']:.3f} F1={s['f']:.3f}")
    return scores


if __name__ == "__main__":
    if "--eval" in sys.argv:
        evaluate_on_test()
    else:
        lines = sys.argv[1:] or [
            "2 tbsp ghee",
            "1 inch ginger, finely chopped",
            "2-3 green chillies slit",
            "2 medium onions",
            "5 cloves garlic",
            "salt to taste",
        ]
        for line in lines:
            tags = ", ".join(f"{t['label']}={t['text']!r}" for t in extract(line))
            print(f"{line!r:40} -> {tags}")
