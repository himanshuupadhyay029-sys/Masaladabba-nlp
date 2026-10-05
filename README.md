# indian-recipe-ner

A custom spaCy NER model that extracts **QUANTITY**, **UNIT**, **INGREDIENT** and **PREP** entities from Indian recipe ingredient lines. It is compared against a hand-written regex baseline and demonstrated in a web UI called *Masala Dabba*.

```
2 tbsp ghee, 1 tsp jeera, 3 chopped onions
│  │    │     │  │   │      │    │      │
Q  U    I     Q  U   I      Q    P      I
```

**Result:** the model gets an overall F1 of **0.952** on the held-out test set. The regex baseline gets **0.901**, and the project target was 0.85.

---

## Problem

Recipe ingredient lines look structured but aren't. The same idea gets written many ways:

| Line | What makes it hard |
|---|---|
| `1½ cup toor dal (cooked)` | unicode fraction; prep inside brackets |
| `5 cloves garlic` vs `4 cloves` | "cloves" is a UNIT in one line and an INGREDIENT (the spice) in the other |
| `1 tsp kasuri methi / dry fenugreek leaves (crushed)` | Hinglish + English names for the same thing |
| `salt (namak) to taste, restricted salt for health` | word quantity, translation, extra advice |
| `2 Onions finely chopped` vs `3 chopped onions` | prep after the ingredient vs before it |

The task is **named entity recognition** at the level of character spans. Every span needs exactly the right start, end and label to count as correct.

## Data

| | |
|---|---|
| Scraped lines | **486** unique lines from 36 recipes (`src/scrape.py`) |
| Hand-written messy lines | **52** (`data/raw/manual_lines.txt`): typos (`chiken`, `tomatos`), Hinglish (`lehsun`, `methi dana`), ranges (`6-7`), `namak to taste` |
| Total annotated | **538** lines → **1,788** entities |
| Entities per label | QUANTITY 535 · UNIT 370 · INGREDIENT 694 · PREP 189 |
| Hinglish lines | **41.3 %** contain at least one Roman-script Hindi/regional word |
| Split (seeded, every label in every split) | train **376** · dev **80** · test **82** |

**Sources:**
- **Hebbar's Kitchen:** 13 recipes. Vegetarian, North + South Indian.
- **Archana's Kitchen:** 14 recipes. Chicken, mutton, egg, keema and prawn dishes, plus Kerala/Tamil vegetables.
- **Tarla Dalal:** 9 recipes. Vegetarian, including Punjabi and Gujarati dishes.
- **Veg Recipes of India** returns HTTP 403 to scrapers, so it was left out rather than worked around.

**Data notice:** the ingredient lines were collected from the public recipe pages listed in `data/raw/urls.txt`, for this educational NLP project only. The recipes and their text belong to their original sites. If you reuse this data, check each site's terms first.

**How the scraper reads a page:**
- It uses the schema.org `recipeIngredient` data (JSON-LD) that recipe sites publish for search engines.
- If a page has none, it falls back to CSS selectors.
- It waits 2 seconds between requests and sends a user-agent header.
- Cleaning is kept minimal: it unescapes HTML entities, collapses whitespace, and drops the literal word `None` that one site prints when a quantity is missing. Case, spelling and fractions are left untouched on purpose, because that messiness is what the model has to learn.

**A real data artefact:** Tarla Dalal's `1/2 chopped capsicum` arrives as `45661 chopped capsicum`. Most likely a spreadsheet turned the fraction into a date serial number. It was kept and labelled as a QUANTITY, because it is genuine scraped noise.

## Annotation guidelines

The base label scheme is in [PROJECT.md](PROJECT.md#label-scheme-annotation-guidelines). Annotation brought up more cases that needed a rule; these are the decisions made:

1. **Alternative names are separate INGREDIENT spans.**
   - `rajma / kidney beans` → `rajma` and `kidney beans` are two spans.
   - `garlic (lehsun)` → `garlic` and `lehsun` are two spans.
   - **Exception:** if a translation interrupts the name, the whole phrase is one span. Examples: `Coriander (Dhania) Leaves` and `tamarind (imli) pulp`.
2. **State adjectives before the noun belong to the INGREDIENT.** This covers `dry`, `dried`, `fresh`, `whole`, `hot` and `raw`, as in `dry red chilli`, `Fresh coconut` and `Hot water`.
3. **Cooking actions are PREP wherever they appear:** before the ingredient (`3 chopped onions`, `roasted peanut`), after it (`Onions fried`), or in brackets (`(sliced)`).
4. **Size words are always PREP:** `small`, `medium`, `large`, `big`, `medium sized`.
5. **Numbers inside a prep phrase belong to the PREP.** `soaked 20 minutes` and `cut into 1/2 inch pieces` are single PREP spans, not QUANTITY + UNIT.
6. **Form words after the ingredient are PREP.** In `potato cubes` and `radish (mooli) slices`, `cubes` and `slices` are PREP. Before the ingredient they are UNIT, as in `20 cubes paneer` or `6 slices bread`.
7. **Count words are UNIT only when an ingredient follows.** `5 cloves garlic`, `1 pod black cardamom`, `2 sprig Curry leaves`, `15 florets gobi`.
8. **Word quantities:**
   - `pinch`, `a pinch`, `few`, `handful`, `to taste`, `as required` and `as needed` are QUANTITY on their own.
   - With a number in front, `pinch` becomes the UNIT: `2 pinches of asafoetida` → Q `2`, U `pinches`.
9. **Some things are not labelled:**
   - connectors: `of`, `/`, `,`, `or`
   - purposes: `for garnish`, `for grinding`
   - conditionals and advice: `(if required)`, `(optional)`, `or as per your heat tolerance`
   - side notes: `(chicken with bones gives better taste)`

**Who annotated:** the gold labels were produced by an LLM (Claude), which read every line and applied the rules above. **No human reviewed them.** The annotations are stored as readable inline markup in `data/annotated/gold_markup.txt`, for example `[[2|Q]] [[tbsp|U]] [[ghee|I]]`. `src/markup_to_ls.py` checks that removing the markup gives back each original line character for character. It then writes `gold_export.json` in Label Studio's export format, so the labels can be imported into Label Studio and reviewed or corrected at any time.

## Method

**1. Regex baseline** (`src/baseline.py`) encodes the usual word order, `QUANTITY → UNIT → (PREP) → INGREDIENT → (PREP)`. It has four steps:
- **QUANTITY:** a regex for integers, decimals, `1/2`, `½`, mixed fractions like `2 1/2` and `1½`, ranges like `2-3` and `3 to 4`, and word quantities.
- **UNIT:** a unit list, applied only directly after a quantity. Count units such as `cloves` also need another word after them.
- **PREP:** a list of action verbs, optionally with an adverb (`finely`, `roughly`) or joined by `and`/`&`.
- **INGREDIENT:** the longest run of left-over words that are not stop-words and not inside brackets.

**2. spaCy NER model** (`configs/config.cfg`, `src/train.py`):
- It starts from a blank English pipeline, with no pretrained vectors or embeddings.
- Architecture: `tok2vec` (a hash embedding of each token's NORM, PREFIX, SUFFIX and SHAPE, then a CNN encoder with window 1 and depth 4) followed by a **transition-based NER** parser.
- Training: CPU only, 30 epochs, Adam (lr 0.001), batches that grow in size, dropout 0.1, evaluated on the dev set every 20 steps.
- `model-best` is the checkpoint with the best dev-set F1: **0.977**, reached at epoch 20.
- The prefix, suffix and shape features give the model a way to generalise to words it has not seen, because it can use the spelling pattern instead of needing an exact match. We did not measure this separately. In a quick check, both systems handled typos like `haldii` and `onoins`, so no advantage over the baseline is claimed.

**3. Conversion** (`src/convert.py`):
- Label Studio character offsets are mapped to spaCy tokens with `alignment_mode="contract"`.
- The data is split 70/15/15, reshuffling until every label appears in all three splits (seed 42).

**4. Evaluation** (`src/evaluate.py`):
- Both systems are scored with spaCy's `Scorer.score_spans` on the same test set, with exact span and label match.
- The baseline's character spans are snapped to the same tokens first, so the comparison is fair.

## Results

Test set: 82 held-out lines, 257 gold entities.

| Label | Baseline P | Baseline R | Baseline F1 | Model P | Model R | Model F1 |
|---|---|---|---|---|---|---|
| QUANTITY | 0.976 | 1.000 | 0.988 | **1.000** | 1.000 | **1.000** |
| UNIT | 0.980 | 1.000 | **0.990** | 0.942 | 0.980 | 0.961 |
| INGREDIENT | 0.890 | 0.745 | 0.811 | **0.940** | **0.959** | **0.950** |
| PREP | 0.840 | 0.724 | 0.778 | 0.800 | **0.828** | **0.814** |
| **OVERALL** | 0.933 | 0.872 | 0.901 | **0.943** | **0.961** | **0.952** |

![Per-label F1, baseline vs model](report/f1_chart.png)

**What the numbers say:**
- **INGREDIENT is where learning pays off.** F1 goes from 0.81 to 0.95, and recall from 0.75 to 0.96. The regex can't know where a multi-word name like `Whole Black Peppercorns` or `Coriander (Dhania) Leaves` starts and ends. The model learns this from context.
- **QUANTITY is nearly solved by both systems.** Numbers have a very regular shape.
- **The baseline wins on UNIT (0.99 vs 0.96).** A closed list of units is hard to beat. The model's UNIT errors are words it has seldom seen in that position (see the error analysis).
- **PREP is the lowest label for both,** as predicted in PROJECT.md. It has the fewest examples (189), the most varied wording (`crushed between palms`, `soaked in 2 tablespoons water`), and it can appear before or after the ingredient.

**Caveats:**
- **The test set is small.** 82 lines and 257 entities means a single error moves an F1 score by about 0.4 points. The gap between the systems on UNIT (0.03) is only a few spans.
- **The annotations come from one LLM annotator** with no human review, so there's no inter-annotator agreement figure.
- **The baseline was written knowing what this data looks like.** That makes it a strong baseline, not a straw man.
- **The model has no "not an ingredient line" option.** It was only trained on ingredient lines, so for non-recipe text it still labels something. For example, `hello world` gets `hello` as PREP, and `!!!` gets a QUANTITY.
- **Roman script only.** Text in Devanagari script (e.g. `१ चम्मच घी`) is outside the training data, so the output is not meaningful.
- **The demo app tags at most 60 lines per request** (`MAX_LINES` in `app/server.py`).

## Error analysis

`python src/error_analysis.py` → `report/error_analysis.md`. The model makes **11 errors** on the test set:
- 7 **boundary** errors (the span overlaps the gold span but starts or ends differently)
- 3 **wrong-label** errors
- 1 **spurious** span

| Cause | Example (gold → predicted) |
|---|---|
| **Unseen ingredient** (5) | `tomatos` (a typo never seen in training) → tagged UNIT. `black cardamom` → `black` as UNIT. `green peas` swallowed into a PREP span. |
| **Prep after ingredient** (3) | `1 cup Onions fried`: `fried` → INGREDIENT (it looks like part of the name). `soaked in 2 tablespoons water` → the model only found `water` as an INGREDIENT. |
| **Boundaries on punctuation** | `washed and soaked overnight.` includes the full stop. `small sized` → only `small`. |
| **Inside brackets** | `(colour of your choice)`: `colour` → spurious INGREDIENT. |
| **Hinglish compound** | `coriander-cumin seeds (dhania-jeera) powder` → only `dhania-jeera`. |

**Seen in the live demo (not in the test set):**
- In `2 medium onions`, the model tags `medium` as a **UNIT**; guideline 4 says PREP. Size words appear only a few times in training, and they sit where units usually sit (straight after a number). The model has learned the *position* instead of the *word*. The regex gets this right because `medium` is on its list.
- `3 tomatoes pureed` → the model tags `tomatoes` as PREP, and `1 tea bag` → `tea` as UNIT and `bag` as INGREDIENT. The regex gets both right.
- `half cup grated coconut` → the model tags `half` as an INGREDIENT, because it rarely saw word quantities at the start of a line. The regex gets it right, because `half` is on its list.
- The baseline tags **at most one INGREDIENT per line** (it picks the longest run of left-over words). On a comma-separated line such as `2 tbsp ghee, 1 tsp jeera, 3 chopped onions` it misses `jeera` and `onions`. This is a limit of how the baseline was written, not of regex in general, and the test-set comparison is not affected, because those lines hold one ingredient each.
- A fully Hindi prep phrase such as `hari mirch barik kati hui` ("finely chopped green chilli") is mis-tagged. The training data has Hinglish *ingredient names* but no Hindi *grammar*.

**Planned fix:** annotate more lines with size words and prep after the ingredient, then re-split and retrain. Any such change has to happen *before* the test set is looked at again, otherwise the evaluation is no longer independent.

## NLP layers discussion

**Lexical / morphological:**
- **Tokenization decides what can be labelled.**
  - spaCy keeps `1/2` and `1½` as single tokens.
  - It splits `2-3` into `2` `-` `3`, so a range is a multi-token QUANTITY span.
  - It splits `250g` into `250` + `g` and `Lady Finger/Okra` at the slash, so each name can be its own span.
- **Tokenizer limit:** spaCy doesn't split `Rai/` when a space follows the slash, as in `(Rai/ Kadugu)`. That made **2 gold spans impossible to align**, and `convert.py` reports them.
- **Spelling variation is everywhere:** `jeera` / `cumin`, `asafoetida` / `asaofetida` / `hing`, `chilli` / `chili`, `tbsp` / `tbps`, `powder` / `pwoder` / `powdr`, `to mato`, `crardamom`.
- The model's prefix, suffix and shape features give it a way to cope with spelling variants it has not seen. This was not measured separately. Both systems handled `haldii` and `onoins` in a spot check, and the model failed on `tomatos` (→ UNIT) in the test set.

**Syntactic:**
- The dominant order is QUANTITY → UNIT → INGREDIENT, and both systems exploit it.
- Prep is the hard part because it moves: `3 chopped onions` / `Onions finely chopped` / `onion (finely chopped)`.
- Most PREP errors come from prep *after* the ingredient, where it reads like part of the name (`Onions fried`).

**Semantic:**
- **The same word takes different labels in different contexts.** `cloves` is a UNIT in `5 cloves garlic` but an INGREDIENT in `4 cloves`. `leaves` is part of the INGREDIENT in `curry leaves` but a UNIT in `few leaves`. `cubes` is a UNIT before the noun but PREP after it.
- **Words like `green`, `red` and `black` are part of the name,** as in `green chilli`, `red chilli powder` and `black cardamom`. The model got `black cardamom` wrong, splitting off `black` as a UNIT.
- The "cup" in `cupcake flour` is not ambiguous here, because tokenization keeps `cupcake` as one token and the model tags `cupcake flour` as an INGREDIENT.

**Pragmatic:**
- **Some quantities are conventional rather than numeric:** `to taste`, `as required`, `as needed`, `a pinch`, `few`, `handful`. Readers understand them from cooking culture.
- **Nearby phrases are advice, not quantities:** `(if required)`, `(optional)`, `or as per your heat tolerance`, `(chicken with bones gives better taste)`. Deciding these are *not* entities is itself a pragmatic judgement.
- Both systems get word quantities right (QUANTITY F1 ≈ 1.0), because the set of conventional phrases is small.

## How to run

```powershell
# 1. Environment (Python 3.9–3.12; on this machine `py` defaults to 3.14, so pick 3.11)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Data
python src/scrape.py                 # -> data/raw/lines.txt (486 lines)
python src/prelabel.py               # optional: regex pre-annotations for Label Studio

# 3. Gold annotations -> spaCy splits
python src/markup_to_ls.py           # gold_markup.txt -> data/annotated/gold_export.json (verified)
python src/convert.py data/annotated/gold_export.json   # -> data/spacy/{train,dev,test}.spacy

# 4. Baseline, training, evaluation
python src/baseline.py --eval        # regex baseline on the test set
python src/train.py                  # a few minutes on CPU -> models/model-best
python src/evaluate.py               # -> report/metrics.json, results.md, f1_chart.png
python src/error_analysis.py         # -> report/error_analysis.md, errors.json

# 5. Try it
python src/predict.py "2 tbsp ghee, 1 tsp jeera, 3 chopped onions"
uvicorn app.server:app --reload      # open http://localhost:8000
```

**Reviewing the annotations in Label Studio (optional):**
1. Run `label-studio start`.
2. Create a project and paste `configs/label_studio_config.xml` into the labelling config.
3. Import `data/annotated/gold_export.json` and correct any labels that look wrong.
4. Export as JSON and run `convert.py` on the export.

**Demo deep links:**
- `/#dish=sambar&mode=compare` shows the baseline and the model side by side.
- `/#dish=biryani&view=thali` shows the thali view.
- `/#tab=metrics` opens the metrics tab.
- `/#tab=about` opens **The Recipe**: the project brief written as a recipe card (ingredients, method, tasting notes, chef's notes). Its numbers are read live from `report/metrics.json`, and its example cards run in the Extract tab.
- `/#text=2-3%20green%20chillies%20slit&view=tokens` shows how spaCy tokenizes a line and the B/I/O tag of each token.
- `/#text=2%20cups%20basmati%20rice%20soaked%20for%2030%20minutes&mode=compare&scale=2` shows the **Scale recipe** control (½×/1×/2×/3×). It multiplies only spans tagged QUANTITY, so the regex baseline's mistake (`30` minutes → `60`) is visible.

### Project layout

```
data/raw/          lines.txt (scraped), manual_lines.txt, urls.txt
data/annotated/    gold_markup.txt (gold labels), gold_export.json, labelstudio_import.json
data/spacy/        train/dev/test .spacy + split.json
src/               scrape, prelabel, markup_to_ls, convert, baseline, train, evaluate, error_analysis, predict
configs/           config.cfg (spaCy), label_studio_config.xml
models/            model-best, model-last (git-ignored)
app/               server.py (FastAPI) + static/ (Masala Dabba UI)
report/            metrics.json, results.md, f1_chart.png, error_analysis.md, errors.json, train_log.txt
```
