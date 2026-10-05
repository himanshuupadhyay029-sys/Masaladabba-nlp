"""
Train the NER model from a blank English pipeline (CPU).

Wraps `python -m spacy train` with our paths. Settings live in configs/config.cfg:
  - pipeline: tok2vec + ner, no pretrained vectors (blank "en")
  - 30 epochs, evaluated on dev.spacy every 20 steps
  - spaCy keeps the checkpoint with the best dev F1 in models/model-best

Usage:  python src/train.py
"""

from pathlib import Path

from spacy.cli.train import train

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    train(
        ROOT / "configs" / "config.cfg",
        output_path=ROOT / "models",
        overrides={
            "paths.train": str(ROOT / "data" / "spacy" / "train.spacy"),
            "paths.dev": str(ROOT / "data" / "spacy" / "dev.spacy"),
        },
    )
    print(f"\nBest model saved to {ROOT / 'models' / 'model-best'}")
