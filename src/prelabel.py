"""
Pre-annotate ingredient lines for Label Studio.

Only the "obvious" QUANTITY and UNIT spans are pre-filled by regex (rules
shared with baseline.py). INGREDIENT and PREP are left for the human, so
the annotator corrects/extends instead of labelling everything from scratch.

Writes:
  data/annotated/labelstudio_import.json   -> import this into Label Studio
  configs/label_studio_config.xml          -> paste into Labeling Interface > Code

Usage:  python src/prelabel.py
"""

import json
from pathlib import Path

from baseline import quantity_unit_spans, remove_overlaps

ROOT = Path(__file__).resolve().parent.parent
LINES_FILE = ROOT / "data" / "raw" / "lines.txt"
MANUAL_FILE = ROOT / "data" / "raw" / "manual_lines.txt"
OUT_JSON = ROOT / "data" / "annotated" / "labelstudio_import.json"
OUT_XML = ROOT / "configs" / "label_studio_config.xml"

# Colours match the frontend spice palette.
LABEL_CONFIG = """<View>
  <Header value="Label QUANTITY, UNIT, INGREDIENT, PREP (see PROJECT.md guidelines)"/>
  <Labels name="label" toName="text">
    <Label value="QUANTITY" background="#E8A317" hotkey="q"/>
    <Label value="UNIT" background="#5B8C5A" hotkey="u"/>
    <Label value="INGREDIENT" background="#C1442E" hotkey="i"/>
    <Label value="PREP" background="#F26B1D" hotkey="p"/>
  </Labels>
  <Text name="text" value="$text" granularity="word"/>
</View>
"""
# granularity="word" makes selections snap to whole words, so spans line up
# with spaCy's tokens later (avoids half-word spans like "chop|ped").


def read_lines(path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def to_task(text, source):
    """One Label Studio task: the text + the regex spans as a 'prediction'."""
    results = []
    for start, end, label in remove_overlaps(quantity_unit_spans(text)):
        results.append({
            "from_name": "label",   # must match <Labels name="label">
            "to_name": "text",      # must match <Text name="text">
            "type": "labels",
            "value": {"start": start, "end": end, "text": text[start:end], "labels": [label]},
        })
    return {
        "data": {"text": text, "source": source},
        "predictions": [{"model_version": "regex-prelabel", "result": results}],
    }


def main():
    scraped = read_lines(LINES_FILE)
    manual = read_lines(MANUAL_FILE)
    seen, tasks = set(), []
    for text, source in [(t, "scraped") for t in scraped] + [(t, "manual") for t in manual]:
        if text.lower() not in seen:
            seen.add(text.lower())
            tasks.append(to_task(text, source))

    OUT_JSON.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_XML.write_text(LABEL_CONFIG, encoding="utf-8")

    n_spans = sum(len(t["predictions"][0]["result"]) for t in tasks)
    print(f"{len(scraped)} scraped + {len(manual)} manual lines -> {len(tasks)} tasks")
    print(f"{n_spans} QUANTITY/UNIT spans pre-filled")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_XML.relative_to(ROOT)}")
    if not manual:
        print("NOTE: data/raw/manual_lines.txt is empty - add your ~50 messy lines and re-run.")


if __name__ == "__main__":
    main()
