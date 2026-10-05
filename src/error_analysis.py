"""
Error analysis: list every wrong prediction of the model and group it by cause.

For each test line we compare gold spans with predicted spans:
  - wrong label : same text span, different label        (e.g. PREP predicted as INGREDIENT)
  - boundary    : overlapping span, different start/end   (e.g. "chilli" vs "green chilli")
  - missed      : gold span with no overlapping prediction (false negative)
  - spurious    : predicted span with no overlapping gold  (false positive)

Each error also gets a linguistic "cause" tag (see cause_tags) so the
errors can be discussed in terms of the NLP layers in the README.

Writes report/error_analysis.md and report/errors.json.
Usage:  python src/error_analysis.py            (test set)
        python src/error_analysis.py dev        (dev set)
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import spacy

from evaluate import is_hinglish, load_docs

ROOT = Path(__file__).resolve().parent.parent


def spans(doc):
    return {(e.start_char, e.end_char, e.label_) for e in doc.ents}


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def cause_tags(text, span, train_ingredients, gold):
    """Heuristic reasons why a span might be hard for the model."""
    s, e, label = span
    piece = text[s:e]
    tags = []
    if label == "INGREDIENT" and piece.lower() not in train_ingredients:
        tags.append("unseen ingredient")
    if is_hinglish(piece):
        tags.append("Hinglish word")
    if label == "QUANTITY" and not re.search(r"\d|[½¼¾⅓⅔]", piece):
        tags.append("quantity word (no digits)")
    # word order: PREP normally comes before the ingredient ("chopped onions")
    if label == "PREP" and any(g[2] == "INGREDIENT" and g[1] <= s for g in gold):
        tags.append("prep after ingredient")
    if text[:s].count("(") > text[:s].count(")"):
        tags.append("inside brackets")
    if re.search(r"\d", piece) and label == "PREP":
        tags.append("number inside prep")
    return tags or ["other"]


def classify(gold, pred):
    """Pair up gold and predicted spans into error records."""
    errors = []
    for g in gold - pred:
        same_place = [p for p in pred if p[:2] == g[:2]]
        overlapping = [p for p in pred if overlaps(p, g) and p not in gold]
        if same_place:
            errors.append(("wrong label", g, same_place[0]))
        elif overlapping:
            errors.append(("boundary", g, overlapping[0]))
        else:
            errors.append(("missed", g, None))
    for p in pred - gold:
        if not any(overlaps(p, g) for g in gold):
            errors.append(("spurious", None, p))
    return errors


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "test"
    blank = spacy.blank("en")
    model = spacy.load(ROOT / "models" / "model-best")
    train_ingredients = {e.text.lower() for d in load_docs("train", blank) for e in d.ents
                         if e.label_ == "INGREDIENT"}

    records = []
    for gold_doc in load_docs(split, blank):
        text = gold_doc.text
        gold = spans(gold_doc)
        for kind, g, p in classify(gold, spans(model(text))):
            ref = g or p
            records.append({
                "text": text,
                "type": kind,
                "gold": None if g is None else {"text": text[g[0]:g[1]], "label": g[2]},
                "pred": None if p is None else {"text": text[p[0]:p[1]], "label": p[2]},
                "causes": cause_tags(text, ref, train_ingredients, gold),
            })

    by_type = Counter(r["type"] for r in records)
    by_cause = Counter(c for r in records for c in r["causes"])
    by_label = Counter((r["gold"] or r["pred"])["label"] for r in records)

    out = ROOT / "report"
    (out / "errors.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# Error analysis ({split} set)\n", f"Total errors: **{len(records)}**\n",
          "## By error type\n", "| Type | Count |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in by_type.most_common()]
    md += ["\n## By label (gold label, or predicted label for spurious)\n", "| Label | Count |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in by_label.most_common()]
    md += ["\n## By cause (an error can have several)\n", "| Cause | Count |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in by_cause.most_common()]
    md += ["\n## All errors\n", "| Line | Type | Gold | Predicted | Causes |", "|---|---|---|---|---|"]
    fmt = lambda s: "—" if s is None else f"`{s['text']}` {s['label']}"
    for r in records:
        md.append(f"| {r['text']} | {r['type']} | {fmt(r['gold'])} | {fmt(r['pred'])} | "
                  f"{', '.join(r['causes'])} |")
    (out / "error_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"{len(records)} errors on {split}: {dict(by_type)}")
    print(f"by cause: {dict(by_cause)}")
    print("Wrote report/error_analysis.md and report/errors.json")


if __name__ == "__main__":
    main()
