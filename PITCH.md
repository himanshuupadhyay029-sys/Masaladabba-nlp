# PITCH.md — Presenting *Masala Dabba* to your NLP professor

**Length:** about 13 minutes of talking plus questions. **Audience:** an NLP professor, so she will care about the method,
the evaluation and the limits more than the pretty interface. The interface is your hook, not your argument.

**Rule for the whole talk:** be the first person to mention every weakness. A professor trusts a student who says
"this is where it fails and why" far more than one who hides it.

---

## 0. The cheat card (print this or keep it on your phone)

| Min | Part | What's on screen |
|---|---|---|
| 0:00 | Hook + problem | Browser, empty Extract tab |
| 1:00 | Data and labelling (the honest bit) | `gold_markup.txt` in your editor |
| 2:30 | Pipeline in one picture | README "Method" or the map in `LEARN.md` |
| 3:30 | **Live demo** | `http://localhost:8000` |
| 9:00 | Results | Metrics tab, then `report/f1_chart.png` |
| 10:30 | NLP layers + error analysis | `report/error_analysis.md` |
| 12:00 | Limits + next steps | Back to the README |
| 12:45 | Close | Back to the browser |

**Tight on time?** Cut §4c (three quick lines), §4d (tokens) and §4f (thali). Keep 4a, 4b, 4e (scale) and the Metrics tab (4h).

### Before you walk in (do this 15 minutes early)

```powershell
cd "C:\Users\Asus\Desktop\NLP MINIPROJ\indian-recipe-ner"
.\venv\Scripts\Activate.ps1
uvicorn app.server:app
```

1. Wait until the terminal says `Application startup complete`, then open `http://localhost:8000`.
2. **Open these tabs in advance** so you never have to search for anything on stage:
   - `http://localhost:8000/#dish=paneer&mode=compare` (side-by-side)
   - `http://localhost:8000/#dish=biryani&view=thali` (thali)
   - `http://localhost:8000/#tab=metrics` (metrics)
   - `http://localhost:8000/#text=2%20cups%20basmati%20rice%20soaked%20for%2030%20minutes&mode=compare&scale=2` (scale demo, §4e)
   - `http://localhost:8000/#text=2-3%20green%20chillies%20slit&view=tokens` (tokens view, §4d)
   - `http://localhost:8000/#tab=about` (**The Recipe** tab: the project brief as a recipe card. Good as an opening slide or as the summary while she asks questions)
3. **Open these files** in your editor: `data/annotated/gold_markup.txt`, `src/baseline.py`, `src/convert.py`, `configs/config.cfg`, `src/evaluate.py`, `report/error_analysis.md`.
4. Zoom the browser to about 125% so the back row can read the pills.
5. **Backup plan:** if the server dies, run `python src/predict.py "2 tbsp ghee, 1 tsp jeera, 3 chopped onions"` in a second terminal. It proves the model works, with no browser needed. Keep screenshots of the three views on your phone.
6. Run the whole demo once. **Do not change any code the day before.**

> Internet is only needed for the Google Fonts. Without it the page still works and just uses default fonts.

---

## Tech stack (put this on one slide, or read it out in 20 seconds)

| Layer | Tool (version used) | What it does here | Why this one |
|---|---|---|---|
| Language | **Python 3.11** | Everything except the frontend | spaCy supports 3.9–3.12 |
| NLP / ML | **spaCy 3.8** | Tokenizer, `tok2vec` + transition-based NER, `DocBin` data format, training CLI, `Scorer` | Small CPU-friendly models, exact character spans, built-in evaluation |
| Annotation | **Label Studio 1.23** | Labelling interface and the export format our labels use (optional audit/review) | Free, local, standard NER format |
| Data collection | **requests 2.34** + **BeautifulSoup4 4.15** | Fetching pages and reading their HTML / JSON-LD | Simple and readable |
| Baseline | Python **`re`** (regular expressions) | The rule-based comparison system | No dependencies, fully transparent |
| Reporting | **matplotlib 3.11** | The per-label F1 bar chart | Standard |
| Backend | **FastAPI 0.142** + **Uvicorn 0.54** + **Pydantic 2.13** | `/predict`, `/baseline`, `/metrics`, serves the page | Light, fast, validates input, auto-generates `/docs` |
| Frontend | **Vanilla HTML + CSS + JavaScript** | The whole Masala Dabba UI | No framework or build step, so nothing to install |
| Fonts | **Google Fonts**: Yatra One, Playfair Display, Inter | Title, headings, body text | Free, and gives the spice-box character |
| Data formats | Plain text, **JSON**, spaCy **DocBin** (`.spacy`) | Raw lines, labels, model-ready data | |
| Hardware | **CPU only** (Windows 11 laptop) | Training took a few minutes; model is about 6 MB | |

**Say honestly if asked:**
- "`pandas` and `scikit-learn` are in `requirements.txt` because the project spec listed them, but no code uses them. Evaluation uses spaCy's own scorer."
- "I built this with AI assistance (Claude Code), including writing the code and producing the labels. I can explain every part, and the labels are disclosed as LLM-made." *(Decide beforehand how you want to word this. A professor asking about a student's process is normal, and being upfront is the safe answer.)*

---

## 1. Hook and problem (≈ 1 min)

**SAY**

> "Ma'am, every recipe website writes ingredients in free text: *'2 medium onions, finely chopped'*.
> To a person that's an amount, a thing, and an instruction. To a computer it's just a string.
> My project teaches a model to read these lines and pull out four things: **quantity, unit, ingredient and
> preparation**.
> I built it as a custom spaCy NER model, compared it honestly against a regex baseline, and wrapped it in
> a demo I call **Masala Dabba**, because an Indian kitchen's spice box has compartments, and the model's job is to
> sort each line into the right compartment."

**Alternative opening:** start on **The Recipe** tab instead of the empty Extract tab. It shows the project as a recipe card
("Serves one NLP viva · Prep 538 labelled lines · Cook 30 epochs, CPU · Yield 0.95 F1"), the four spices, the method and the
limits in one scroll. Say the hook over it, then click **Extract** for the live demo. Come back to it at the end for Chef's
notes (the limits) if you want them on screen while answering questions.

**DO**: show the empty Extract tab and point at the four legend colours.

> "Each entity is a spice. **Haldi** yellow is the quantity, **elaichi** green is the unit, **mirchi** red is the
> ingredient, and **kesar** orange is the preparation."

**Why it's hard** (say one or two of these, not all):
- `4 cloves` → cloves is the *spice*. `5 cloves garlic` → cloves is a *unit*. Same word, different role.
- Hinglish: *jeera, haldi, dhaniya patta, adrak* sit beside English *cumin, ginger*.
- Quantities that aren't numbers: *to taste, a pinch, few*.

---

## 2. Data and labelling (≈ 1.5 min)

**SAY**

> "The data is **538 ingredient lines**. 486 were scraped from 36 recipes on Hebbar's Kitchen, Archana's Kitchen
> and Tarla Dalal, covering North and South Indian, vegetarian and non-vegetarian dishes. I added 52 deliberately
> messy lines of my own with typos, ranges and Hinglish, so the test isn't only clean text. I tried a fourth site,
> but it blocked scrapers, so I left it out."

**DO**: open `gold_markup.txt` and show a few lines, e.g. `[[2|Q]] [[tbsp|U]] [[ghee|I]]`.

> "I wrote annotation guidelines first, because the model can only learn what the labels teach it. One example: size
> words like 'medium' are always PREP. And every annotated line is **automatically checked**: if I strip the markup, it
> must equal the original text character for character."

**Say this part yourself, before she asks** (do not skip it):

> "One honest point: **the gold labels were produced by an LLM, Claude, following my guidelines, with no human review.**
> So the labels are consistent but not independently validated, and I can't report inter-annotator agreement. They're
> exported in Label Studio format, so a human can audit and correct them, and that is the first thing I'd do next."

---

## 3. Pipeline in one picture (≈ 1 min)

**SAY**

```
scrape  →  label  →  split 70/15/15  →  baseline (regex)
                              └──────→  train spaCy NER  →  evaluate on test  →  error analysis  →  web app
```

> "Split is train 376, dev 80, test 82, fixed seed, and I made sure every label appears in every split. **Dev** picks
> the best checkpoint during training. **Test** I look at only for the final scores. Training is blank English spaCy,
> a `tok2vec` layer feeding a transition-based NER, 30 epochs on CPU. The best checkpoint was epoch 20, with dev F1 0.977."

**If she asks about the model internals** (see §7 for the code to open):
> "`tok2vec` embeds each token using four features, its normalised form, prefix, suffix and shape, then a small
> window encoder mixes in neighbouring tokens. The NER head reads left to right and chooses a transition at each
> token: begin, continue or end an entity."

---

## 4. Live demo (≈ 5.5 min) ← the main event

Every output below was checked against the real model and baseline before this script was written.

### 4a. The hero line (45 sec)

**DO**: go to the first tab, click **Sort into the dabba** with the placeholder line (or type it):
`2 tbsp ghee, 1 tsp jeera, 3 chopped onions`

**SAY**
> "Three ingredients in one line. The model finds all of them: ghee, jeera and onions, each with its quantity,
> and 'chopped' as preparation. The small tag over each pill is the entity type."

Now click **Side by side**.

> "Here's the regex baseline next to it. It misses *jeera* and *onions*."

**Then immediately be fair:**
> "I should be honest about why: my baseline only picks **one ingredient per line**, because I wrote it for one-ingredient
> lines. A smarter regex could split on commas. So this particular line is not a fair fight. The fair comparison is the
> test-set score, where every line has one ingredient."

### 4b. Where learning really helps: the Paneer Butter Masala chip (1.5 min)

**DO**: click the **Paneer Butter Masala** chip, stay on **Side by side**. The header says *"4 of 13 lines differ"*; the
differing lines have a small dot beside the line number.

Walk through the four rows. It is a **2–2 split**, which is the point:

| Line | Who's right | What to say |
|---|---|---|
| `10 cashews soaked in hot water` | **Model** | "The regex sees 'soaked', then takes *hot water* as the ingredient. The model understands *soaked in hot water* is one preparation phrase and keeps *cashews* as the ingredient. That's context." |
| `2 tbsp fresh cream` | **Model** (by our guideline) | "Guideline: state words like *fresh* belong to the ingredient. The regex treats 'fresh' as a stop-word and drops it." |
| `2 medium onions, finely chopped` | **Regex** | "This is the model's known bug: it tags *medium* as a **UNIT**. By our guideline size words are PREP. I'll explain why in a moment." |
| `3 tomatoes pureed` | **Regex** | "Here the model tags *tomatoes* itself as PREP, which is wrong. The model can fail on common words too." |

**SAY about the `medium` bug** (this is the best moment of the talk):
> "Why? In training, units almost always sit right after a number. 'Medium' also sits right after a number in
> `2 medium onions`, and there are only a few size-word examples. So the model learned the **position pattern, not the
> word**. That's a data-coverage problem, and the fix is more targeted examples, not a bigger model. I didn't add them after
> seeing the test results, because that would leak the test set into training."

### 4c. Context and pragmatics: three quick lines (45 sec)

Click **Regex baseline** or **spaCy model** and type each line into the box, then **Sort into the dabba**:

1. `4 cloves` then `5 cloves garlic` → "Same word. In the first it's the **ingredient**, in the second it's a **unit**. The model gets both right, using the neighbouring word."
2. `salt to taste` and `water as needed` → "The quantity isn't a number. *To taste* is a conventional phrase, a **pragmatic** convention of recipe language, and both systems tag it as QUANTITY."
3. `half cup grated coconut` → **a deliberate failure**. "Here the model tags *half* as an INGREDIENT. It rarely saw a word-quantity at the start of a line. The regex gets it because 'half' is on its list. Rules win when the vocabulary is a closed list."

### 4d. Tokens view: what the model actually sees (45 sec)

**DO**: open the prepared tokens link, or click **Tokens** in the view toggle after running `2-3 green chillies slit`.

**SAY**
> "This is the lexical layer made visible. spaCy first chops the line into **tokens**: notice `2-3` becomes three
> tokens, `2`, `-`, `3`. The model then makes one decision per token. Underneath each token you see B, I or O: **B** begins
> an entity, **I** is inside it, **O** is outside. `2 - 3` is B-QTY, I-QTY, I-QTY, and `green chillies` is B-ING, I-ING."

**Be precise if asked:** "The labels are stored as spans. The B/I/O row is derived from the spans for display, and spaCy
uses a BILUO-style scheme internally."

### 4e. Why extraction matters: scale the recipe (60 sec) ← the best 60 seconds

**DO**: open the prepared scale link. It runs `2 cups basmati rice soaked for 30 minutes` side by side with the scale already at **2×**. (Or type the line yourself, choose **Side by side**, then click **2×**.)

**SAY**
> "Why bother extracting quantities at all? Here's a downstream use. The **Scale recipe** control multiplies *only the
> spans tagged QUANTITY*. Watch what happens with this line. The regex baseline tagged `30`, the minutes, as a quantity,
> so at 2× it says **sixty minutes**. The model tagged `soaked for 30 minutes` as one *preparation* phrase, so it leaves
> it alone and only doubles the 2 cups to 4. **A tagging error becomes a visible cooking error.** That's why precision
> matters here, and it's the pragmatic side of the project."

Then click **½×** and **3×** to show fractions work (`1/2 cup` becomes `1½ cup` at 3×; `2-3` becomes `6-9`).

> It's a fair demo because the baseline's error is real and reproducible, but note it's one line. Don't claim the model
> never makes such mistakes: it labelled `tomatoes` in `3 tomatoes pureed` as PREP, which would break a scaling feature too.

### 4f. Thali view (30 sec)

**DO**: click the **Biryani** chip, switch the view toggle to **Thali**.

> "Same output, a different view. The plate has four katori, one per entity type, and the extracted values fly into
> their bowls with counts. It's a way to see a whole recipe's *shopping list structure* at a glance: all the quantities
> together, all the units, all the ingredients."

### 4g. Table and JSON (15 sec)

> "Underneath is a clean table, and **Copy JSON** gives the exact character offsets. That's what a downstream app
> would use, for example to scale a recipe for more servings."

### 4h. Metrics tab (45 sec)

**DO**: click **Metrics**.

> "These come straight from `report/metrics.json`, not typed in. The model's overall F1 is **0.952** on 82 held-out
> lines; the regex gets **0.901**. Each bar is the model, and the black tick marks the baseline. Quantity is near
> perfect for both. Ingredient is where learning pays off: **0.95 against 0.81**. Prep is the hardest for both, as I
> expected, because it has the fewest examples. And on **unit the regex actually wins, 0.99 to 0.96**."

---

## 5. Results (≈ 1.5 min)

**DO**: show the table in `report/results.md` or the chart `report/f1_chart.png`.

| Label | Baseline F1 | Model F1 |
|---|---|---|
| QUANTITY | 0.988 | **1.000** |
| UNIT | **0.990** | 0.961 |
| INGREDIENT | 0.811 | **0.950** |
| PREP | 0.778 | **0.814** |
| **Overall** | 0.901 | **0.952** |

**SAY**
> "Scoring is **exact match**: start, end and label must all be right, so predicting *chilli* for *green chilli* counts
> as one miss and one false alarm. The target was 0.85 and we reached 0.95."

**The caveats to volunteer:**
1. "The test set is small: 82 lines, 257 entities. One error moves F1 by about 0.4 points, so I wouldn't read much into
   the 0.03 gap on UNIT."
2. "This is a **single training run**. I did not measure variance across seeds or do cross-validation."
3. "Dev F1 (0.977) is higher than test F1 (0.952) because I chose the best epoch *on dev*. That mildly flatters dev. Test is the honest number."
4. "The baseline was written knowing this data, so it's a fairly strong baseline, not a straw man."

---

## 6. NLP layers and error analysis (≈ 1.5 min)

**SAY**: "I analysed the model's 11 test errors, and they line up with the layers of language we studied."

| Layer | Evidence from this project |
|---|---|
| **Lexical / morphological** | Tokenization decides what can be labelled. spaCy splits `2-3` into three tokens, keeps `1/2` as one, and glues `Rai/` to its slash, which made 2 gold spans impossible to align. Spelling variants: *jeera/zeera/cumin*, *chilli/chili*, *tbsp/tbps*. |
| **Syntactic** | The word-order pattern QUANTITY → UNIT → INGREDIENT is strong. The errors cluster where order changes: **prep after the ingredient**, e.g. `Onions fried` → *fried* taken as part of the name. |
| **Semantic** | Role depends on context: *cloves* (spice vs unit), *leaves* (part of *curry leaves* vs a unit in *few leaves*), *cubes* before vs after the noun. Colour words are part of the name in *green chilli*, and the model split *black cardamom*. |
| **Pragmatic** | *To taste*, *as required*, *a pinch* are quantities by convention, not by number. And advice such as *(if required)* or *(optional)* is deliberately **not** labelled. |

**DO**: open `report/error_analysis.md` and show the table "by cause": unseen ingredient 5, prep after ingredient 3, other 3 (one error can have several causes).

---

## 7. Limits and next steps (≈ 1 min)

**SAY**

> "Three limits. **One:** the labels are LLM-made and unreviewed. **Two:** a small test set and one training run, so
> the scores are indicative, not definitive. **Three:** all text comes from three recipe sites, so it may not
> generalise to handwritten or social-media recipes.
> Next steps, in order: have a human correct the labels and report agreement; add targeted examples for size words,
> word-quantities and prep-after-ingredient, then retrain **and keep a fresh test set**; compare with a pretrained
> transformer such as a BERT-based NER; and use cross-validation to get confidence intervals."

---

## 8. Close (≈ 20 sec)

**DO**: go back to the browser with the highlight view showing.

> "So the idea in one line: **a spice box that sorts a messy recipe line into four compartments, built with a model
> small enough (about 6 MB) to run on a laptop CPU and fast enough for a live demo.** Thank you, ma'am. I'm happy
> to open any part of the code."

---

# If she wants to see code

Open only the file she asks about. 30 seconds each.

| File | Open | Say |
|---|---|---|
| `src/scrape.py` | `from_json_ld()` | "Most recipe sites publish a schema.org `recipeIngredient` list for search engines. I read that first, and fall back to HTML selectors. 2-second delay, user-agent header." |
| `data/annotated/gold_markup.txt` and `src/markup_to_ls.py` | `parse()` and the equality check in `main()` | "Inline markup is easy to read and edit. The script checks that stripping it returns the original text exactly, then writes a Label Studio JSON export." |
| `src/convert.py` | `make_doc()` | `doc.char_span(start, end, label=..., alignment_mode="contract")`: "Label Studio gives character offsets, spaCy needs token-aligned spans. `contract` shrinks a span to the tokens fully inside it. Two spans couldn't align, and the script reports them." Then `split()`: "Reshuffles with a new seed until every label is in every split." |
| `src/baseline.py` | `extract()` | "Four steps: quantity regex, unit directly after a quantity, prep word list with optional adverb, and INGREDIENT as the longest run of left-over words that aren't stop-words or in brackets. That last rule is why it only finds one ingredient per line." |
| `configs/config.cfg` | `[components.tok2vec.model.embed]`, `[training]` | "`MultiHashEmbed` over NORM, PREFIX, SUFFIX, SHAPE; `MaxoutWindowEncoder` with width 96, depth 4; `TransitionBasedParser` for NER. Adam, learning rate 0.001, dropout 0.1, 30 epochs, evaluated on dev every 20 steps." |
| `src/evaluate.py` | `main()` | "Both systems go through the same `Scorer.score_spans`, so the comparison is fair. The baseline's character spans are snapped to tokens first. Results are written to `metrics.json`, which the web app reads." |
| `app/static/app.js` | `scaleLine()`, `parseQuantity()`, `renderTokens()` | "Scaling parses only spans tagged QUANTITY, handling `1/2`, `½`, `1½`, `2 1/2`, `1-1/2` and ranges like `2-3`, then rebuilds the line so every span's offsets stay correct. The tokens view derives B/I/O from the spans." |
| `app/server.py` | the route functions | "Two endpoints, `/predict` and `/baseline`, return character offsets as JSON; the frontend only paints boxes at those offsets. The model loads once at startup." |

---

# Questions she might ask, and strong answers

**Method**

1. **Why spaCy's NER instead of a CRF, a BiLSTM-CRF or BERT?**
   "It's CPU-friendly, small, fast, runs offline, and returns exact character spans, which the UI needs. A pretrained
   transformer would probably do better, especially on unseen vocabulary, and comparing against one is my first
   next step. I didn't do it here because of the CPU-only constraint and the time."

2. **How does the model represent a word? Why not use pretrained word vectors?**
   "It builds the representation from hashed features of the token: normalised form, prefix, suffix and shape.
   I started from a blank pipeline so that everything it knows comes from this domain. Pretrained vectors might help with
   rare words, and are worth testing."

3. **Is this BIO tagging?**
   "Not exactly. spaCy's NER is transition-based: at each token it picks an action (begin, in, last, unit, out).
   It's a sequence of decisions rather than per-token BIO tags, but the end result is the same kind of span output."

4. **Why a regex baseline, and is it fair?**
   "To show whether learning adds value over rules. It's fairly strong, because I wrote it knowing the data, and it
   has one structural limit: one ingredient per line. Both systems are scored by the same scorer on the same tokens."

**Data and evaluation**

5. **How were the labels made, and how do you know they're correct?**
   "An LLM labelled them from written guidelines, and every line is checked mechanically against the source text.
   But there is no human review and no inter-annotator agreement, so correctness is not independently verified.
   That's the main limitation, and why the labels are exportable to Label Studio."

6. **Why exact-match scoring, and why micro-averaged F1?**
   "Exact match is the standard for NER and avoids giving partial credit for wrong boundaries. Micro-average pools all
   entities, so frequent labels weigh more; I also report per-label scores so nothing is hidden."

7. **Is 82 test lines enough?**
   "No, not for strong claims. One error is about 0.4 F1 points. I'd call the result indicative. With more time I'd
   use k-fold cross-validation and report confidence intervals."

8. **Dev F1 was 0.977 but test is 0.952. Why?**
   "I picked the best checkpoint on dev, which introduces mild selection bias, and dev is also only 80 lines. Test is
   the unbiased number."

9. **Could the test set have leaked?**
   "I split once with a fixed seed and did not retrain or relabel after seeing the test results. The error analysis
   found issues like the `medium` bug, and I deliberately did not fix them by adding data, because that would contaminate the evaluation."

10. **Did you run it more than once? What's the variance?**
    "Once. Training starts from random initial values, so another run could differ by a point or so. I haven't measured it."

**Results and analysis**

11. **Why does the regex beat the model on UNIT?**
    "Units are a small closed list, so rules are almost perfect. The model's few UNIT errors involve words in unit-like
    positions, e.g. `medium` right after a number, or a word like `cubes` whose role flips with position."

12. **Why is PREP the worst label?**
    "The fewest examples (189 total), the most varied wording, and it can come before or after the ingredient, which makes
    the boundary harder to learn."

13. **How does the model handle words it never saw, such as typos?**
    "In principle prefix, suffix and shape features let it generalise, but I haven't measured it. In a spot check both
    systems handled typos like `haldii`, and the model failed on `tomatos`. So I don't claim an advantage."

14. **Hinglish: did you handle it specially?**
    "No special handling. Roman-script Hindi words are just tokens, learned from examples. About 41% of lines contain
    one, measured with a keyword list, so that figure is approximate."

15. **What would you do with more time?**
    "Human-validated labels with agreement scores; targeted examples for size words and prep-after-ingredient;
    cross-validation; a transformer baseline; and normalising ingredients, so that jeera, zeera and cumin map to
    one canonical item."

**Practical**

16. **Is scraping those sites allowed?**
    "I used a 2-second delay, an honest user-agent, and only public ingredient lists. One site returned 403 and I
    excluded it instead of working around the block. For a public release I'd check each site's terms."

17. **Could this just be done by prompting an LLM?**
    "Yes, and an LLM would likely be accurate. This model is 6 MB, free, offline, fast on a laptop CPU, deterministic and
    returns exact offsets. The tradeoff is that it needs labelled data and handles unseen patterns less gracefully."

---

# Making it creative without overdoing it

- Use the **spice-box metaphor** at the start and the end only. The middle should stay technical.
- Say the names **haldi, elaichi, mirchi, kesar** once, at the legend. After that, say QUANTITY, UNIT, INGREDIENT, PREP.
- Let the **side-by-side view** be the climax. The Paneer Butter Masala chip is your best moment because it shows a fair
  fight with wins on both sides.
- Don't rush the failures. A professor remembers "the student who showed me where the model breaks and explained why".

---

# For your personal-project / GitHub / LinkedIn version

**One-line description (GitHub "About"):**
> Custom spaCy NER model that extracts quantity, unit, ingredient and prep from Indian recipe lines, benchmarked against a regex baseline, with a spice-box demo UI.

**60-second pitch:**
> "Recipe sites write ingredients as free text. I built *Masala Dabba*: a custom spaCy NER model trained on 538
> annotated Indian ingredient lines, including Hinglish names like *jeera* and *dhaniya patta*. It reaches 0.95 F1
> against 0.90 for a hand-written regex baseline, and the biggest gain is on ingredient names (0.95 vs 0.81). The
> demo shows both systems side by side, and I wrote up where the model fails and why."

**What to add to the repo before posting:** 3–4 screenshots in the README (highlight, side-by-side, thali, metrics), and
keep the "labels are LLM-made" note, which reads as maturity rather than weakness.
