# indian-recipe-ner

## Goal
Extract QUANTITY, UNIT, INGREDIENT, PREP from Indian recipe ingredient lines using a custom spaCy NER model, evaluated against a regex baseline with per-label precision/recall/F1, and demonstrated through a showcase web UI.

## Tech stack
Python 3.9–3.12 (whatever is installed), spaCy 3.x, Label Studio (local annotation), pandas, scikit-learn, matplotlib, FastAPI + uvicorn (backend), vanilla HTML/CSS/JS frontend. CPU only.

## Folder structure
indian-recipe-ner/
├── PROJECT.md
├── README.md
├── requirements.txt
├── data/
│   ├── raw/urls.txt            # recipe URLs to scrape
│   ├── raw/lines.txt           # 300–500 lines, one per row
│   ├── raw/manual_lines.txt    # hand-written messy lines
│   ├── annotated/              # Label Studio JSON export
│   └── spacy/                  # train.spacy, dev.spacy, test.spacy
├── src/
│   ├── scrape.py               # collect ingredient lines
│   ├── prelabel.py             # regex pre-annotation → Label Studio import JSON
│   ├── convert.py              # Label Studio export → spaCy DocBin, 70/15/15 split
│   ├── baseline.py             # regex-only extractor
│   ├── train.py                # wraps spacy train
│   ├── evaluate.py             # P/R/F1 per label, baseline vs model → report/metrics.json + charts
│   ├── error_analysis.py       # dump and group misclassified spans
│   └── predict.py              # load model, tag a line
├── configs/config.cfg          # spaCy training config
├── models/                     # trained model output
├── app/
│   ├── server.py               # FastAPI: /predict, /baseline, /metrics, serves static/
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
└── report/                     # metrics.json, charts, results tables

## Label scheme (annotation guidelines)
- QUANTITY: numbers, fractions, ranges, words — "2", "1/2", "1-2", "half", "a pinch", "to taste", "as needed"
- UNIT: "tbsp", "tsp", "cup", "g", "kg", "ml", "inch", "pieces", "cloves", "sprigs", "leaves"
- INGREDIENT: the full ingredient phrase including adjectives that are part of the name — "green chilli", "curry leaves", "red chilli powder", "dhaniya patta", "paneer"
- PREP: action applied to the ingredient — "chopped", "finely chopped", "grated", "soaked overnight", "slit", "boiled and mashed"
- Do NOT label: connectors ("of", ",", "and"), purposes ("for garnish", "for frying"), brand names
- Edge rules: "1 inch ginger" → QUANTITY=1, UNIT=inch, INGREDIENT=ginger. "2 medium onions" → QUANTITY=2, INGREDIENT=onions; size words like "medium/large/small" are labelled PREP consistently.

## Data
300–500 ingredient lines from Hebbar's Kitchen, Archana's Kitchen, Tarla Dalal, Veg Recipes of India. Cover North + South Indian, veg + non-veg, Hinglish + English names. Plus ~50 hand-written messy lines (typos, "salt to taste", "2-3 green chillies slit") so the test set is realistic.

## Phases
1. Setup — repo, venv, requirements, PROJECT.md, README skeleton, scraper
2. Data — collect ~400 lines, dedupe, save to data/raw/lines.txt
3. Pre-annotation — regex tags obvious QUANTITY/UNIT, exported in Label Studio import format so I correct instead of labelling from scratch; also generate the Label Studio labelling config XML
4. Annotation — I do this manually in Label Studio, export JSON
5. Conversion — JSON → spaCy DocBin, 70/15/15 split, every label present in every split
6. Baseline — regex extractor, evaluated on test set
7. Training — spacy train from blank "en", ~30 epochs, save best model to models/
8. Evaluation — per-label P/R/F1 table, baseline vs model, saved as report/metrics.json + markdown table + bar chart
9. Error analysis — wrong predictions grouped by cause (unseen ingredient, Hinglish, prep-after-ingredient, quantity words, etc.)
10. Frontend — FastAPI + static showcase UI (see Frontend brief), built only after the model is trained, using real outputs
11. Report — README filled in: method, results, error analysis, NLP layers discussion

## Target metrics
Overall F1 > 0.85 on test. INGREDIENT and QUANTITY highest; PREP expected lowest (least data) — a legitimate discussion point.

## NLP layers discussion (for README)
- Lexical/morphological: tokenization of "1/2", "tbsp.", Roman-script Hindi words, spelling variants (jeera/zeera/cumin)
- Syntactic: word-order patterns — quantity → unit → ingredient; prep before or after ingredient
- Semantic: context-dependent meaning — "cup" as UNIT vs part of "cup cake"; "green" inside "green chilli"
- Pragmatic: conventional quantities — "to taste", "as needed", "optional"

## Frontend brief — "Masala Dabba"
Concept: the interface is a spice box. Each entity type is a spice; the model sorts the recipe line into compartments.

Stack: app/server.py (FastAPI) with endpoints /predict (model), /baseline (regex), /metrics (reads report/metrics.json); serves app/static/. Frontend is one index.html + style.css + app.js, vanilla JS, no build step, Google Fonts allowed. Mobile friendly.

Palette: warm cream background #F7EFE2 (paper recipe card), deep brown text #3B2416, brass/gold accents #B8862B. Entity colours from spices — QUANTITY haldi yellow #E8A317, UNIT elaichi green #5B8C5A, INGREDIENT mirchi red #C1442E, PREP kesar orange #F26B1D.

Typography: Yatra One (Google Fonts) for the title, Playfair Display for headings, Inter or Poppins for body. Title "Masala Dabba", subtitle "Ingredient & Quantity Extractor for Indian Recipes".

Ornament: a thin paisley/rangoli SVG divider between sections; subtle block-print motif in the background at ~4% opacity. Restraint — one or two motifs, not a wedding card.

Layout & interactions:
- Hero: large input styled like a lined recipe card, placeholder "2 tbsp ghee, 1 tsp jeera, 3 chopped onions". Quick-try chips below: Paneer Butter Masala, Sambar, Chole, Biryani — each loads that dish's full ingredient list.
- Result view 1 (highlight): input re-rendered with coloured pill highlights per entity and a small label tag above each span.
- Result view 2 (thali): a circular plate with four katori (bowls), one per entity, and extracted items animate into their bowls.
- Below: clean table of extracted entities + "Copy JSON" button.
- Baseline vs Model toggle: same line tagged by regex baseline and trained model, side by side — the key demo moment.
- Metrics tab: per-label P/R/F1 as horizontal bars in spice colours, dataset stats (lines, entities per label, Hinglish %), read from report/metrics.json.
- Micro-copy: loading state "Tempering the model…" with a tadka dot animation; empty/error state "Kuch nahi mila — try another line".
- Build order: highlight view first and polish it, then baseline toggle, then metrics tab, then thali animation last.
