"""
Turn the inline annotation file into a Label Studio-style JSON export.

data/annotated/gold_markup.txt has one annotated line per source line, e.g.
    [[2|Q]] [[tbsp|U]] [[ghee|I]]
Q=QUANTITY, U=UNIT, I=INGREDIENT, P=PREP. Removing the markup must give back
the original line exactly - this is checked for every line, so the gold
labels always refer to the real scraped/manual text.

The output has the same format as a Label Studio JSON export, so convert.py
works on it unchanged, and it can also be imported into Label Studio to review.

Usage:  python src/markup_to_ls.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKUP_FILE = ROOT / "data" / "annotated" / "gold_markup.txt"
OUT_FILE = ROOT / "data" / "annotated" / "gold_export.json"
CODES = {"Q": "QUANTITY", "U": "UNIT", "I": "INGREDIENT", "P": "PREP"}
TAG_RE = re.compile(r"\[\[(.+?)\|([QUIP])\]\]")


def read_source(path):
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def parse(markup):
    """Return (plain_text, [(start, end, label)]) for one marked-up line."""
    text, spans, pos = "", [], 0
    for m in TAG_RE.finditer(markup):
        text += markup[pos:m.start()]
        start = len(text)
        text += m.group(1)
        spans.append((start, len(text), CODES[m.group(2)]))
        pos = m.end()
    text += markup[pos:]
    return text, spans


def main():
    sources = ([(t, "scraped") for t in read_source(ROOT / "data" / "raw" / "lines.txt")]
               + [(t, "manual") for t in read_source(ROOT / "data" / "raw" / "manual_lines.txt")])
    markup = MARKUP_FILE.read_text(encoding="utf-8").splitlines()
    if len(markup) != len(sources):
        sys.exit(f"{len(markup)} annotated lines but {len(sources)} source lines")

    tasks, errors = [], 0
    for i, (line, (original, source)) in enumerate(zip(markup, sources), 1):
        text, spans = parse(line)
        if text != original:
            print(f"line {i}: markup text differs from source\n  {text!r}\n  {original!r}")
            errors += 1
            continue
        tasks.append({
            "id": i,
            "data": {"text": text, "source": source},
            "annotations": [{"result": [
                {"from_name": "label", "to_name": "text", "type": "labels",
                 "value": {"start": s, "end": e, "text": text[s:e], "labels": [label]}}
                for s, e, label in spans]}],
        })
    if errors:
        sys.exit(f"{errors} mismatched lines - fix gold_markup.txt")

    OUT_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"All {len(tasks)} lines verified against the source text -> {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
