"""
Evaluate the trained model and the regex baseline on the held-out test set.

Both are scored with spaCy's span scorer: a predicted entity counts as correct
only if its start, end AND label all match the gold annotation exactly.

Writes:
  report/metrics.json   (read by the web app's Metrics tab)
  report/results.md     (tables for the README)
  report/f1_chart.png   (per-label F1, baseline vs model)

Usage:  python src/evaluate.py
"""

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # draw to file, no window
import matplotlib.pyplot as plt
import spacy
from spacy.scorer import Scorer
from spacy.tokens import DocBin
from spacy.training import Example

import baseline

ROOT = Path(__file__).resolve().parent.parent
SPACY_DIR = ROOT / "data" / "spacy"
REPORT_DIR = ROOT / "report"
LABELS = ["QUANTITY", "UNIT", "INGREDIENT", "PREP"]

# Roman-script Hindi/regional words used to measure how "Hinglish" the data is.
HINGLISH_WORDS = {
    "jeera", "zeera", "haldi", "dhania", "dhaniya", "patta", "rai", "methi", "hing",
    "adrak", "lehsun", "mirch", "mirchi", "namak", "dahi", "imli", "gud", "kopra",
    "elaichi", "laung", "lavang", "dalchini", "tej", "saunf", "ajwain", "amchur",
    "pudina", "aloo", "gobi", "palak", "matar", "besan", "maida", "rava", "suji",
    "kasuri", "chana", "rajma", "dal", "toor", "toovar", "arhar", "urad", "moong",
    "masoor", "kadi", "kesar", "sabut", "dana", "kali", "lal", "hari", "safed",
    "javetri", "kaddu", "lauki", "doodhi", "mooli", "bhindi", "suran", "gajjar",
    "paneer", "ghee", "sarson", "kalimirch", "chilkewali", "nimbu", "phool", "saijan",
    "phalli", "bhopla", "ratalu", "karamani", "barbati", "chawli", "avarekai",
    "poosanikai", "vellai", "kadugu", "senai", "saragavo", "kabuli", "masala", "kaju",
}


def is_hinglish(text):
    return any(w in HINGLISH_WORDS for w in re.findall(r"[a-z]+", text.lower()))


def load_docs(name, nlp):
    return list(DocBin().from_disk(SPACY_DIR / f"{name}.spacy").get_docs(nlp.vocab))


def baseline_doc(nlp, text):
    """Run the regex baseline and turn its character spans into a spaCy Doc."""
    doc = nlp.make_doc(text)
    ents = []
    for sp in baseline.extract(text):
        span = doc.char_span(sp["start"], sp["end"], label=sp["label"], alignment_mode="expand")
        if span is not None:
            ents.append(span)
    doc.ents = spacy.util.filter_spans(ents)
    return doc


def summarise(scores):
    per = {l: {k: round(scores["ents_per_type"].get(l, {}).get(k, 0.0), 4) for k in ("p", "r", "f")}
           for l in LABELS}
    return {"overall": {"p": round(scores["ents_p"], 4), "r": round(scores["ents_r"], 4),
                        "f": round(scores["ents_f"], 4)},
            "per_label": per}


def dataset_stats(nlp):
    stats, all_docs = {"splits": {}}, []
    for name in ("train", "dev", "test"):
        docs = load_docs(name, nlp)
        all_docs += docs
        stats["splits"][name] = len(docs)
    counts = Counter(e.label_ for d in all_docs for e in d.ents)
    stats["lines"] = len(all_docs)
    stats["entities"] = {l: counts[l] for l in LABELS}
    stats["hinglish_pct"] = round(100 * sum(is_hinglish(d.text) for d in all_docs) / len(all_docs), 1)
    stats["manual_lines"] = sum(d.user_data.get("source") == "manual" for d in all_docs)
    return stats


def draw_chart(results, path):
    """Grouped horizontal bars: per-label F1, baseline vs model."""
    labels = LABELS + ["OVERALL"]
    base = [results["baseline"]["per_label"][l]["f"] for l in LABELS] + [results["baseline"]["overall"]["f"]]
    model = [results["model"]["per_label"][l]["f"] for l in LABELS] + [results["model"]["overall"]["f"]]

    fig, ax = plt.subplots(figsize=(7, 4.2), facecolor="#F7EFE2")
    ax.set_facecolor("#F7EFE2")
    y = range(len(labels))
    h = 0.36
    colours = {"Regex baseline": "#3576C4", "spaCy NER model": "#A0621A"}
    for offset, values, name in ((-h / 2 - 0.01, base, "Regex baseline"), (h / 2 + 0.01, model, "spaCy NER model")):
        bars = ax.barh([i + offset for i in y], values, height=h, color=colours[name], label=name)
        for bar, v in zip(bars, values):
            ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2, f"{v:.2f}",
                    va="center", fontsize=8, color="#3B2416")
    ax.set_yticks(list(y), labels, color="#3B2416")
    ax.invert_yaxis()
    ax.set_xlim(0, 1.08)   # bars start at 0 so their lengths are honest
    ax.set_xlabel("F1 on test set (exact span match)", color="#3B2416")
    ax.set_title("Per-label F1: regex baseline vs spaCy NER", color="#3B2416", loc="left", pad=28)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#B8A99A")
    ax.spines["bottom"].set_color("#B8A99A")
    ax.tick_params(colors="#6B5747")
    ax.grid(axis="x", color="#E4D8C6", linewidth=0.8)
    ax.set_axisbelow(True)
    # legend in a row above the plot so it never covers a bar
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())


def markdown_table(results):
    rows = ["| Label | Baseline P | Baseline R | Baseline F1 | Model P | Model R | Model F1 |",
            "|---|---|---|---|---|---|---|"]
    for l in LABELS + ["OVERALL"]:
        b = results["baseline"]["overall"] if l == "OVERALL" else results["baseline"]["per_label"][l]
        m = results["model"]["overall"] if l == "OVERALL" else results["model"]["per_label"][l]
        name = f"**{l}**" if l == "OVERALL" else l
        rows.append(f"| {name} | {b['p']:.3f} | {b['r']:.3f} | {b['f']:.3f} | "
                    f"{m['p']:.3f} | {m['r']:.3f} | {m['f']:.3f} |")
    return "\n".join(rows)


def main():
    blank = spacy.blank("en")
    model = spacy.load(ROOT / "models" / "model-best")
    test_docs = load_docs("test", blank)

    # Example(predicted, gold) pairs for each system
    model_examples = [Example(model(g.text), g) for g in test_docs]
    base_examples = [Example(baseline_doc(blank, g.text), g) for g in test_docs]

    results = {
        "model": summarise(Scorer.score_spans(model_examples, "ents")),
        "baseline": summarise(Scorer.score_spans(base_examples, "ents")),
        "dataset": dataset_stats(blank),
        "test_lines": len(test_docs),
    }

    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    table = markdown_table(results)
    (REPORT_DIR / "results.md").write_text(
        f"# Results (test set, {len(test_docs)} lines)\n\n{table}\n\n![F1 chart](f1_chart.png)\n",
        encoding="utf-8")
    draw_chart(results, REPORT_DIR / "f1_chart.png")

    print(table)
    print(f"\nDataset: {results['dataset']}")
    print("Wrote report/metrics.json, report/results.md, report/f1_chart.png")


if __name__ == "__main__":
    main()
