"""
Tag ingredient lines with the trained NER model.

Usage:
    python src/predict.py "2 tbsp ghee, 1 tsp jeera, 3 chopped onions"
"""

import sys
from pathlib import Path

import spacy

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "model-best"

_nlp = None


def load_model():
    """Load the model once and reuse it (loading takes ~1 second)."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(MODEL_DIR)
    return _nlp


def tag(text):
    """Return the entities the model finds, as a list of dicts sorted by position."""
    doc = load_model()(text)
    return [{"start": e.start_char, "end": e.end_char, "label": e.label_, "text": e.text}
            for e in doc.ents]


if __name__ == "__main__":
    for line in sys.argv[1:] or ["2 tbsp ghee, 1 tsp jeera, 3 chopped onions"]:
        print(line)
        for ent in tag(line):
            print(f"  {ent['label']:<11} {ent['text']}")
