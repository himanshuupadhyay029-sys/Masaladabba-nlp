"""
Convert a Label Studio JSON export into spaCy training data.

  data/annotated/<export>.json  ->  data/spacy/train.spacy, dev.spacy, test.spacy

- Character spans from Label Studio are mapped onto spaCy tokens.
- 70/15/15 random split, re-shuffled until every label appears in every split.
- The split is saved to data/spacy/split.json so it is reproducible.

Usage:  python src/convert.py data/annotated/project-1-export.json
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "spacy"
LABELS = ["QUANTITY", "UNIT", "INGREDIENT", "PREP"]
SEED = 42


def load_export(path):
    """Return a list of (text, [(start, end, label)], source) from a Label Studio export."""
    tasks = json.loads(Path(path).read_text(encoding="utf-8"))
    records, skipped = [], 0
    for task in tasks:
        # use the first annotation that was submitted (not skipped/cancelled)
        anns = [a for a in task.get("annotations", []) if not a.get("was_cancelled")]
        if not anns:
            skipped += 1
            continue
        text = task["data"]["text"]
        spans = [(r["value"]["start"], r["value"]["end"], r["value"]["labels"][0])
                 for r in anns[0]["result"] if r.get("type") == "labels"]
        records.append((text, spans, task["data"].get("source", "scraped")))
    print(f"Loaded {len(records)} annotated lines ({skipped} unannotated tasks skipped)")
    return records


def make_doc(nlp, text, spans, problems):
    """Tokenize the text and attach the entity spans.

    Label Studio stores character offsets; spaCy needs token-aligned spans.
    'contract' shrinks a span to the tokens fully inside it, which fixes
    selections that accidentally include a trailing space or comma.
    """
    doc = nlp.make_doc(text)
    ents = []
    for start, end, label in spans:
        span = doc.char_span(start, end, label=label, alignment_mode="contract")
        if span is None or len(span) == 0:
            problems.append(f"  could not align {label} {text[start:end]!r} in {text!r}")
            continue
        ents.append(span)
    kept = filter_spans(ents)        # drop overlapping spans (keeps the longest)
    if len(kept) < len(ents):
        problems.append(f"  overlapping spans removed in {text!r}")
    doc.ents = kept
    return doc


def labels_in(docs):
    return {ent.label_ for d in docs for ent in d.ents}


def split(docs):
    """70/15/15 split; re-shuffle with a new seed until every split has every label."""
    for attempt in range(1000):
        rng = random.Random(SEED + attempt)
        shuffled = docs[:]
        rng.shuffle(shuffled)
        n_train, n_dev = int(0.70 * len(docs)), int(0.15 * len(docs))
        parts = {
            "train": shuffled[:n_train],
            "dev": shuffled[n_train:n_train + n_dev],
            "test": shuffled[n_train + n_dev:],
        }
        if all(set(LABELS) <= labels_in(p) for p in parts.values()):
            return parts, SEED + attempt
    sys.exit("Could not find a split with every label in every part - annotate more PREP/UNIT examples.")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/convert.py data/annotated/<label-studio-export>.json")

    nlp = spacy.blank("en")
    problems, docs = [], []
    for text, spans, source in load_export(sys.argv[1]):
        doc = make_doc(nlp, text, spans, problems)
        doc.user_data["source"] = source      # kept so we can analyse manual vs scraped lines
        docs.append(doc)

    if problems:
        print(f"{len(problems)} alignment warnings (fix these in Label Studio if many):")
        print("\n".join(problems[:20]))

    parts, seed = split(docs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, part in parts.items():
        DocBin(docs=part, store_user_data=True).to_disk(OUT_DIR / f"{name}.spacy")
    (OUT_DIR / "split.json").write_text(json.dumps(
        {name: [d.text for d in part] for name, part in parts.items()} | {"seed": seed},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nSplit (seed {seed}):")
    print(f"{'split':<6} {'lines':>5}  " + "  ".join(f"{l:>10}" for l in LABELS))
    for name, part in parts.items():
        c = Counter(ent.label_ for d in part for ent in d.ents)
        print(f"{name:<6} {len(part):>5}  " + "  ".join(f"{c[l]:>10}" for l in LABELS))
    print(f"\nWrote train/dev/test .spacy files to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
