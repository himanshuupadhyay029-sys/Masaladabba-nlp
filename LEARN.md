# LEARN.md — The whole project, taught from zero

You said this is your first time with machine learning. This course assumes that. Every term is explained the first
time it appears, and every lesson ends with something you can **do** on your own laptop.

Work through it in order. Each lesson is about 15–30 minutes. Commands are for **PowerShell** on Windows, run from the
`indian-recipe-ner` folder with the virtual environment active (Lesson 4 shows how).

| # | Lesson | You will be able to... |
|---|---|---|
| 1 | Machine learning in 5 minutes | explain what "training a model" means |
| 2 | The NLP words you need | use *token, entity, label, corpus* correctly |
| 3 | What is spaCy? | read and write basic spaCy code |
| 4 | Setting up | create a clean Python environment |
| 5 | Collecting data | explain and run the scraper |
| 6 | Labelling | label data by hand and in Label Studio |
| 7 | Converting & splitting | explain train / dev / test |
| 8 | The baseline | read regex rules |
| 9 | Inside the model | draw how spaCy's NER works |
| 10 | Training | run training and read the log |
| 11 | Evaluation | calculate precision, recall, F1 by hand |
| 12 | Error analysis | decide what to fix next |
| 13 | The web app | trace a click from browser to model and back |
| 14 | Redo it all from scratch | rebuild the project start to finish |
| 15 | A recipe for any NLP project | reuse this for your next idea |
| 16 | Glossary and viva Q&A | prepare to present |

---

## Lesson 1 — Machine learning in 5 minutes

### Normal programming vs machine learning

**Normal programming:** you write the rules. *If the word is "tbsp", call it a UNIT.*
You get exactly what you wrote, and nothing more. Every new case needs a new rule.

**Machine learning:** you give the computer **examples with the right answers** and it works out the rules itself.
*Here are 376 lines, each with the correct labels. Figure out the pattern.*

This is called **supervised learning** ("supervised" because every example comes with an answer key).

### The three words that matter

| Word | Plain meaning | In this project |
|---|---|---|
| **Data** | The examples | 538 ingredient lines |
| **Model** | The thing that learns: a big pile of adjustable numbers ("dials") | The spaCy NER model, about 6 MB on disk |
| **Training** | Adjusting the dials until the model's guesses match the answer key | `python src/train.py` |

After training you have two phases:
- **Training:** learning from labelled examples. Slow, done once.
- **Inference** (also called *prediction*): using the trained model on new text. Fast, done every time someone clicks the button in your web app.

### Why not just write rules?

We tried exactly that, as the **baseline** (Lesson 8). Rules were great for fixed lists like units, and weak for open-ended things like ingredient names, where the right answer depends on the *words around it*. Machine learning is useful when the answer depends on context and you can't list every case.

> **Do it:** open `report/results.md`. Compare the INGREDIENT row for baseline and model. That gap is the entire reason machine learning exists.

---

## Lesson 2 — The NLP words you need

**NLP (Natural Language Processing):** getting computers to work with human language.

| Term | Plain meaning | Example from this project |
|---|---|---|
| **Corpus** | A collection of text you work on | The 538 ingredient lines |
| **Token** | A piece of text after chopping. Roughly a word, but punctuation counts too | `2-3 green chillies` → `2`, `-`, `3`, `green`, `chillies` |
| **Tokenization** | The chopping step | Done by spaCy automatically |
| **Entity** | A meaningful chunk of text that belongs to a category | `green chillies` is an INGREDIENT |
| **Span** | A continuous stretch of text, one or more tokens | `finely chopped` is a 2-token span |
| **Label / tag** | The category name stuck on a span | QUANTITY, UNIT, INGREDIENT, PREP |
| **NER** | *Named Entity Recognition*: finding spans and giving each a label | The whole project |
| **Annotation** | The human act of adding labels to data | Lesson 6 |
| **Gold labels** | The trusted answer key | `gold_markup.txt` |
| **Feature** | A measurable clue the model uses | "the word ends in -ed" |
| **Embedding** | A word turned into a list of numbers a computer can calculate with | Lesson 9 |

### Why "NER" and not just "classification"?

*Classification* gives one label to a whole item (is this email spam?). NER gives **many labels inside one line**, with exact positions. `2 tbsp ghee` contains three entities, each with a start and end.

---

## Lesson 3 — What is spaCy?

**spaCy** is a free Python library for NLP. It's a toolbox that already knows how to tokenize text, store labels, and train and run models. We didn't write a neural network from scratch; we used spaCy's.

### The four objects to know

```python
import spacy
nlp = spacy.blank("en")            # nlp  = the pipeline (a conveyor belt of steps)
doc = nlp("2-3 green chillies slit")   # Doc  = one processed piece of text
print([t.text for t in doc])       # Token = one piece
# ['2', '-', '3', 'green', 'chillies', 'slit']
```

- **`nlp`** is the pipeline. Text goes in one end and a `Doc` comes out the other.
- **`Doc`** is a text plus everything known about it (tokens, entities).
- **`Token`** is one word or punctuation mark.
- **`Span`** is a slice of a Doc. An entity is a Span with a label.

### Blank vs pretrained

`spacy.blank("en")` is an English tokenizer with **no knowledge**. It can't tell a noun from a verb, let alone a QUANTITY from a UNIT. That's what we want: it knows nothing, so everything it learns comes from *our* data. (spaCy also sells pretrained models like `en_core_web_sm` that know people and places, but they know nothing about "PREP", so we train our own.)

### Labels in spaCy are spans with positions

```python
doc = nlp.make_doc("2 tbsp ghee")
doc.ents = [doc.char_span(0, 1,  label="QUANTITY"),
            doc.char_span(2, 6,  label="UNIT"),
            doc.char_span(7, 11, label="INGREDIENT")]
print([(e.text, e.label_, e.start_char, e.end_char) for e in doc.ents])
# [('2','QUANTITY',0,1), ('tbsp','UNIT',2,6), ('ghee','INGREDIENT',7,11)]
```

`0, 1` means "from character 0 up to (not including) character 1". Reading text as a numbered row of characters is how every label in this project is stored.

### Using the trained model

```python
import spacy
nlp = spacy.load("models/model-best")
doc = nlp("2 tbsp ghee")
print([(e.text, e.label_) for e in doc.ents])
# [('2','QUANTITY'), ('tbsp','UNIT'), ('ghee','INGREDIENT')]
print(nlp.pipe_names)      # ['tok2vec', 'ner']  <- the two stages of our pipeline
```

> **Do it:** paste the snippets above into a file `play.py` in the project folder and run `python play.py`. Then change the text and see what the model does with it.

---

## Lesson 4 — Setting up (Python, venv, pip)

### The concepts

- **Python** is the programming language. This laptop has two versions: 3.11 and 3.14.
  spaCy doesn't support 3.14 yet, so we always pick 3.11 with `py -3.11`.
- **A virtual environment ("venv")** is a private folder of libraries for *this project only*. It stops one project's libraries from clashing with another's. Think of it as a separate toolbox per project.
- **pip** is Python's app store. `pip install spacy` downloads a library into the active venv.
- **`requirements.txt`** is the shopping list of libraries, so anyone can rebuild the same toolbox in one command.

### The steps

```powershell
cd "C:\Users\Asus\Desktop\NLP MINIPROJ\indian-recipe-ner"
py -3.11 -m venv venv              # create the toolbox (once)
.\venv\Scripts\Activate.ps1        # pick up the toolbox (every new terminal)
pip install -r requirements.txt    # fill it (once)
```

You know the venv is active when `(venv)` appears at the start of your prompt.

**If activation is blocked:** run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

### The folder structure, in plain words

```
data/raw/          the raw text we collected
data/annotated/    the answer key (labels)
data/spacy/        the data in the format spaCy trains on (train / dev / test)
src/               the Python scripts, one per step
configs/           the settings file for training
models/            the trained model (git-ignored because it's big)
app/               the web demo
report/            scores, charts, error lists
```

One script per step is deliberate. You can always run just one step and look at what it produced.

---

## Lesson 5 — Collecting data (`src/scrape.py`)

### Why scrape?

A model needs hundreds of realistic examples. Typing them all is slow, and scraping real recipe pages gives genuinely messy text.

### How a web page becomes text

When you open a recipe page, your browser downloads **HTML**, the page's code. Our script does the same with the **`requests`** library, then uses **BeautifulSoup** to search through the HTML and pull out the parts we want.

Most recipe sites hide a neat **JSON-LD** block in their HTML for Google, with a ready-made `recipeIngredient` list. The scraper reads that first. If a page doesn't have it, it falls back to searching the HTML for ingredient lists.

### Being a good citizen

- It waits **2 seconds** between pages, so we don't overload anyone's server.
- It sends a **user-agent** saying who is asking.
- When a site refuses (HTTP 403 means "forbidden"), it reports that and moves on. Veg Recipes of India refused, so we don't use it. Working around a block is not okay.

### Cleaning, kept light

We fixed `&amp;` → `&`, collapsed extra spaces, and removed a stray word "None". We did **not** fix typos or fractions, because the model has to cope with those in real life.

### Run it

```powershell
python src/scrape.py
```

It reads `data/raw/urls.txt` and writes `data/raw/lines.txt`. The last line printed should say `Wrote 486 unique lines`.

> **Do it:** open `lines.txt` and read 30 lines. Spot three odd ones. These are exactly the cases that will trip up rules.
> **Stretch:** add a new recipe URL from Hebbar's Kitchen to `urls.txt` and run the scraper again.

---

## Lesson 6 — Labelling

This is the most important lesson. A model cannot learn anything its answer key doesn't teach.

### What a label looks like

For the line `3 chopped onions`:

| Text | Characters | Label |
|---|---|---|
| `3` | 0–1 | QUANTITY |
| `chopped` | 2–9 | PREP |
| `onions` | 10–16 | INGREDIENT |

### Guidelines: the rulebook for labellers

Reality is messy, so before labelling you write rules. Ours are in `PROJECT.md` and the README. Two real examples:

- `4 cloves` → `cloves` is an INGREDIENT (the spice). But `5 cloves garlic` → `cloves` is a UNIT. The word after it decides.
- `2 medium onions` → `medium` is PREP, because we decided so for all size words.

**Why it matters:** if you label `medium` as PREP on Monday and ignore it on Tuesday, the model sees contradictory lessons and gets confused. **Consistent labels beat clever models.**

### How the labels in this project were made

I read every line and wrote it in a readable inline format in `data/annotated/gold_markup.txt`:

```
[[3|Q]] [[chopped|P]] [[onions|I]]
```

Q = QUANTITY, U = UNIT, I = INGREDIENT, P = PREP. Then `markup_to_ls.py` does a safety check: strip the brackets and the text must equal the original line, character for character. If it doesn't, the script stops and shows the line. This means a typo in the labels can't silently move a label to the wrong place.

### Now do it yourself in Label Studio

Label Studio is a free labelling tool that runs on your laptop. Here's the click-by-click:

1. **Start it:** in the activated venv, run `label-studio start`. A browser tab opens at `http://localhost:8080`.
2. **Create an account** with any email and password. It only exists on your laptop.
3. **Create Project** (button, top right). Name it `recipe-ner`.
4. **Data Import tab:** drag `data/annotated/labelstudio_import.json` in. This file holds all 486 lines **with QUANTITY and UNIT already guessed by regex**, so you correct instead of starting from nothing.
5. **Labeling Setup tab → Custom template → Code.** Delete what's there, paste the contents of `configs/label_studio_config.xml`, click **Save**. This defines the four labels and their colours. The keys `q`, `u`, `i`, `p` select a label.
6. **Settings → Annotation:** turn on **Use predictions to prelabel tasks** and pick `regex-prelabel`. (Menu names shift slightly between Label Studio versions. Look for "prelabel".)
7. **Open the project and click Label All Tasks.** For each line:
   - Select a label (press its key or click it), then drag over the words to label them.
   - Fix any wrong pre-filled span. Click a span, then press Backspace to delete it.
   - Click **Submit**.
8. **Export:** when done, click **Export**, choose **JSON** (not JSON-MIN), and save the file into `data/annotated/`.
9. Convert it: `python src/convert.py data/annotated/<your-file>.json` (Lesson 7).

**To review my labels instead of starting fresh:** in step 4, import `data/annotated/gold_export.json`. It already contains my answers, which you can accept or fix, and that makes the labels truly yours.

**Tip:** the config has `granularity="word"`, which makes the selection snap to whole words. This avoids accidentally selecting half of "chopped".

> **Do it:** open `gold_markup.txt`, take 10 lines, and write down *your* labels first on paper. Then compare. Where you disagree is where a model will struggle too.

---

## Lesson 7 — Converting and splitting (`src/convert.py`)

### Two jobs

1. **Translate** the labels from "character positions" (Label Studio) into spaCy's token-aligned spans. We used `alignment_mode="contract"`, which shrinks a span to the tokens fully inside it. If a span lands in the middle of a token (like our `Rai/` glitch), it can't align, and the script prints a warning. That happened twice in 538 lines.
2. **Split** the data into three piles and save each as a `.spacy` file.

### Why three piles?

Think of studying for an exam:

| Pile | Size | Purpose | Analogy |
|---|---|---|---|
| **train** | 376 (70%) | The model learns from these | Practice questions |
| **dev** | 80 (15%) | Used *during* training to check progress and pick the best version | Mock exams |
| **test** | 82 (15%) | Used **once, at the end**, for the final score | The real exam |

If you let the model see the test questions, even indirectly, your score is meaningless. This is called **data leakage**. It's also why I didn't fix the `medium` bug by adding data after seeing the test results.

### Details that matter

- **Random split with a fixed seed (42):** the order is shuffled randomly, but "seed 42" makes it shuffle identically every time, so your results are reproducible.
- **Every label in every pile:** the script reshuffles until train, dev and test all contain QUANTITY, UNIT, INGREDIENT and PREP. Otherwise the test might hold zero PREP examples.
- **Output files:** `train.spacy`, `dev.spacy`, `test.spacy` (a spaCy binary format called DocBin), plus `split.json`, which lists exactly which lines went where.

### Run it and read the table

```powershell
python src/markup_to_ls.py
python src/convert.py data/annotated/gold_export.json
```

You'll see a table of how many lines and entities of each type landed in each pile. PREP is the smallest (131 in train), which already hints that PREP will be the hardest label.

> **Do it:** open `data/spacy/split.json` and find 5 lines in the test pile. Run each through `python src/predict.py "<line>"`.

---

## Lesson 8 — The baseline (`src/baseline.py`)

### Why build something simple first?

If your model scores 95%, is that good? Only if you know what simple methods score. The baseline is the "no-learning" competitor. If a model can't beat it, the machine learning wasn't worth it.

### Regular expressions in 2 minutes

A **regex** is a pattern that describes text. Examples from the baseline:

| Pattern idea | Matches |
|---|---|
| `\d+` | one or more digits: `2`, `250` |
| `\d+/\d+` | a fraction: `1/2` |
| `\d+\s*(-\|to)\s*\d+` | a range: `2-3`, `3 to 4` |
| `tbsp\|tsp\|cup` | any of those words |

### How the baseline thinks, in four steps

1. **Quantities:** find numbers, fractions and ranges, plus phrases like `to taste` and `a pinch`.
2. **Units:** if a unit word comes right after a quantity, label it UNIT. For count words like `cloves`, only if another word follows.
3. **Prep:** find action words like `chopped, sliced, grated`, plus size words, optionally with `finely`, `roughly` in front.
4. **Ingredient:** whatever words are left over, skipping stop-words like `of`, `for`, `to`, and anything in brackets, with the **longest run** becoming the INGREDIENT.

### Where it fails (this is the lesson)

Step 4 is a guess. If it sees `Whole Black Peppercorns soaked`, it can't know where the name ends. Rules only know the lists we gave them, so any word they haven't heard of is invisible to them.

Try it:

```powershell
python src/baseline.py "2 medium onions" "5 cloves garlic" "4 cloves"
python src/baseline.py --eval        # score on the test set
```

> **Do it:** write your own line with a word that isn't in the prep list (e.g. `2 tomatoes blanched`). Watch the baseline miss it, and see whether the model catches it.

---

## Lesson 9 — Inside the model

You don't need the maths. You need the picture.

### The model starts as a blank slate

Before training, the model's dials hold random numbers, so it guesses randomly. It has never seen the word "ghee".

### Stage 1 — `tok2vec`: words → numbers

"tok2vec" means *token to vector*. A **vector** is just a list of numbers. For each token, spaCy collects four clues:

| Clue | For `Onions` | Why it helps |
|---|---|---|
| **NORM** | `onions` (lowercased form) | Same word, different capitals, treated alike |
| **PREFIX** | `oni` (first letters) | Shared starts hint at related words |
| **SUFFIX** | `ons` (last letters) | `-ed` ending often means PREP, `-powder` often an ingredient |
| **SHAPE** | `Xxxxx` (pattern of capitals, small letters, digits) | `250` becomes `ddd`, so any 3-digit number looks alike |

Each clue is looked up in a table of learned numbers and combined into a vector for the word. In principle this lets the model generalise to a spelling it has never seen, because the suffix and shape can look familiar. (We didn't measure this separately. In a spot check, the regex baseline handled typos like `haldii` just as well, so don't claim an advantage here.)

Then a small neural network (spaCy's `MaxoutWindowEncoder`, a CNN-style design, with `window_size = 1`, `depth = 4`, `width = 96` in our `config.cfg`) lets each word **peek at its neighbours**. Why? Because `cloves` means different things depending on what follows. After this step each token's vector reflects both the word and its surroundings.

### Stage 2 — `ner`: numbers → labels

The `ner` part reads the line **left to right**, one token at a time, and for each token chooses an action like: *start a new INGREDIENT here*, *continue the current entity*, or *this is outside any entity*. This is called a **transition-based** approach, because the model moves through the text making a sequence of decisions.

```
text:      2      tbsp     ghee
vectors:   [..]   [..]     [..]       <- from tok2vec, with neighbour info mixed in
decision:  START  START    START      <- ner chooses an action for each
           QUANTITY UNIT   INGREDIENT
```

### What is a "neural network"?

Just a long chain of simple calculations (multiply, add, compare), with thousands of adjustable dials (called **weights** or **parameters**). Training sets the dials. Nothing more mysterious than that. The dials for this project take up about 6 MB in `models/model-best`.

---

## Lesson 10 — Training (`src/train.py`)

### The loop in plain steps

Each round, spaCy does this:

1. **Forward pass:** feed a **batch** (a few training lines) through the model to get its guesses.
2. **Loss:** compare the guesses with the answer key. The **loss** is one number measuring "how wrong". Lower is better. Ours started near 70 and fell to single digits.
3. **Backpropagation:** work out, for each dial, "if I nudged you up a little, would the loss go up or down?".
4. **Optimizer step:** nudge every dial a little in the helpful direction. We use an optimizer called **Adam** with a starting **learning rate** of 0.001 (the nudge size).
5. Repeat for the next batch.

One pass through all training lines = **one epoch**. We train for **30 epochs** (this is `max_epochs = 30` in `config.cfg`).

### Settings you can control: `configs/config.cfg`

This is a plain text file, with sections in `[square brackets]`:

| Setting | Meaning | Our value |
|---|---|---|
| `max_epochs` | Passes over the training data | 30 |
| `eval_frequency` | Check the dev score every N steps | 20 |
| `dropout` | Fraction of the network randomly switched off during training, to prevent memorising | 0.1 |
| `learn_rate` | Size of each nudge | 0.001 |
| `patience` | Stop early if no improvement (0 = never) | 0 |

### The danger: overfitting

A model with enough dials can **memorise** the training questions instead of learning patterns. Then it aces practice and fails the real exam. Defences:

- **Dropout** (above).
- **Watching the dev score.** We check on the unseen dev pile every 20 steps. If the dev score stops improving while training loss keeps dropping, that's overfitting.
- **Keeping the best checkpoint.** spaCy saves the version with the best dev score as `model-best`, and the last one as `model-last`.

### Run it

```powershell
python src/train.py
```

It prints a table like this (it's also saved in `report/train_log.txt`):

```
E    #       LOSS TOK2VEC  LOSS NER  ENTS_F  ENTS_P  ENTS_R  SCORE
20   380     2.98          3.01      97.73   97.36   98.10   0.98
```

| Column | Meaning |
|---|---|
| **E** | Epoch number |
| **#** | Step number (batches processed) |
| **LOSS ...** | How wrong the model is on training data (goes down) |
| **ENTS_F / P / R** | F1, precision, recall **on the dev pile** (goes up; ×100) |
| **SCORE** | The overall number spaCy uses to pick `model-best` |

Our best was **F = 97.73 at epoch 20**. After that it wobbles between about 96 and 98, which is normal with a small dataset, because one line more or less moves the score.

### Experiments (try these)

1. Set `max_epochs = 3`, retrain, and look at the scores. This is **underfitting**: not enough practice.
2. Set `dropout = 0.0`. Does the gap between training loss and dev score change?
3. Change `window_size` to 2. Does anything improve?

**After each experiment, restore the original values** or note the changes, and re-run `python src/evaluate.py`.

---

## Lesson 11 — Evaluation (`src/evaluate.py`)

### The three counts

For each label on the test pile, count:

- **TP (true positive):** the model predicted it **and** it was right.
- **FP (false positive):** the model predicted it but it was wrong (a false alarm).
- **FN (false negative):** it was really there but the model missed it.

### The three scores

```
Precision = TP / (TP + FP)    "when the model says PREP, how often is it right?"
Recall    = TP / (TP + FN)    "of all the real PREPs, how many did it find?"
F1        = 2 * P * R / (P + R)   the balance of the two
```

**Analogy:** a smoke detector that screams all day has perfect recall and awful precision. One that never goes off has the opposite. F1 is low if either is bad.

### Worked example with our real numbers

The test set has **29 real PREP spans** (from the `convert.py` table). The model scored precision 0.800 and recall 0.828 for PREP. That works out as:

- Recall 0.828 = TP / 29 → TP = **24** (it found 24 of the 29)
- Precision 0.800 = 24 / predicted → it predicted **30** PREP spans (6 were wrong)
- F1 = 2 × 0.800 × 0.828 / (0.800 + 0.828) = **0.814** ✓ (matches `results.md`)

Now you can recompute any row of the results table.

### "Exact match" is strict

A prediction counts only if **start, end and label are all identical** to the answer key. If the answer is `green chilli` and the model says `chilli`, that's a miss **and** a false alarm. This is the standard way to score NER, and it's why scores look lower than "almost right" would suggest.

### Micro-average

The OVERALL row pools every entity together (called *micro*-averaging), instead of averaging the four labels' scores. Labels with more entities weigh more.

### Run it

```powershell
python src/evaluate.py
```

It writes `report/metrics.json` (also read by your web app), `report/results.md` and `report/f1_chart.png`.

### Reading the result

| Label | Rules | Model | Why |
|---|---|---|---|
| QUANTITY | 0.99 | **1.00** | Numbers have a regular shape |
| UNIT | **0.99** | 0.96 | A small fixed list suits rules |
| INGREDIENT | 0.81 | **0.95** | Open vocabulary and context suit learning |
| PREP | 0.78 | **0.81** | Few examples, many wordings |

### Be honest about the numbers

- 82 test lines is **small**: a single mistake shifts F1 by about 0.4 points. A 0.03 difference is only a handful of spans.
- One person (me) labelled everything, so we can't measure how much labellers disagree.

---

## Lesson 12 — Error analysis (`src/error_analysis.py`)

Scores tell you *how well*. Error analysis tells you *what to do next*.

```powershell
python src/error_analysis.py
```

Open `report/error_analysis.md`. Each error is classed as:

| Type | Meaning | Example |
|---|---|---|
| **wrong label** | Right words, wrong category | `20 cubes paneer`: `cubes` as PREP instead of UNIT |
| **boundary** | Overlaps the answer but starts/ends differently | `small` instead of `small sized` |
| **missed** | A real entity the model didn't find | |
| **spurious** | The model invented one | `colour` from a bracket note |

and tagged with a possible cause (unseen ingredient, prep after the ingredient, inside brackets...).

### What to do with the findings

This is the loop that real ML work lives in:

1. Look at the errors and find a **pattern** (e.g. "size words get tagged as UNIT").
2. Form a hypothesis ("too few size-word examples; they sit where units usually do").
3. Fix the cause: **add targeted data**, **correct inconsistent labels**, or **change the guidelines**.
4. Retrain and re-evaluate. Repeat.

> **Careful:** do this loop using the **dev** pile, not the test pile. If you keep tuning against the test results, it stops being an independent exam. In a real project, you'd keep a fresh test set aside for the very end.

> **Do it:** pick two mistakes in `error_analysis.md`. For each, write one sentence on why you think the model failed, then decide whether the fix is "more data", "fix a label", or "accept it".

---

## Lesson 13 — The web app

### The client-server idea

- The **client** is your browser (what you see).
- The **server** is a program that waits for requests and sends answers (`app/server.py`, built with **FastAPI**, run by **uvicorn**).
- They talk using **HTTP requests**, over `http://localhost:8000`. "localhost" just means "this same laptop".

### What happens when you click "Sort into the dabba"

```
1. app.js reads the text box
2. app.js sends  POST /predict  and  POST /baseline  with {"text": "..."}
3. server.py splits the text into lines
4. for each line: predict.py runs the model, baseline.py runs the rules
5. server replies with JSON, e.g.
      {"start":0,"end":1,"label":"QUANTITY","text":"2"}, ...
6. app.js builds coloured pills / the thali / the table from those numbers
```

**JSON** is a text format for structured data, readable by both Python and JavaScript. The browser never runs the model. It only paints boxes at the positions the server returns, which is why `start` and `end` are in every reply.

### The four endpoints

| Endpoint | Does |
|---|---|
| `POST /predict` | Tags lines with the trained model |
| `POST /baseline` | Tags lines with the regex rules |
| `GET /metrics` | Returns `report/metrics.json` for the Metrics tab |
| `GET /` | Serves the web page itself |

### Run it

```powershell
uvicorn app.server:app --reload
```

Open `http://localhost:8000`. `--reload` restarts the server when you edit code. FastAPI also generates a test page at `http://localhost:8000/docs`, where you can send requests by clicking, with no frontend at all. Try that to see the raw JSON.

You can also test it straight from the terminal:

```powershell
curl.exe -X POST localhost:8000/predict -H "Content-Type: application/json" -d "{\"text\":\"2 tbsp ghee\"}"
```

(Type `curl.exe`, not `curl`. In PowerShell, plain `curl` is a different built-in command.)

### The three frontend files

- `index.html`: the structure (headings, buttons, text box)
- `style.css`: how it looks (colours, fonts, the thali circle)
- `app.js`: the behaviour (sending requests, building the highlight view)

### Demo shortcuts

Open `http://localhost:8000/#dish=sambar&mode=compare` to land straight on the side-by-side view.

> **Do it:** open `/docs`, click `POST /predict`, press *Try it out*, type a line, and press *Execute*. Compare the JSON with what the page shows.

---

## Lesson 14 — Redo it all from scratch

Imagine you deleted everything except the scripts and the labels. Here's the full rebuild, in order, with what you should see after each step.

```powershell
# 0. Environment
cd "C:\Users\Asus\Desktop\NLP MINIPROJ\indian-recipe-ner"
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt                      # expect: "Successfully installed ..."

# 1. Collect data
python src/scrape.py                                 # expect: "Wrote 486 unique lines"

# 2. (Optional) pre-annotation file for Label Studio
python src/prelabel.py                               # expect: "827 QUANTITY/UNIT spans pre-filled"

# 3. Gold labels  ->  Label Studio format (checks every line)
python src/markup_to_ls.py                           # expect: "All 538 lines verified"

# 4. Convert + split
python src/convert.py data/annotated/gold_export.json
                                                     # expect: table train 376 / dev 80 / test 82

# 5. Baseline score
python src/baseline.py --eval                        # expect: F1 around 0.90

# 6. Train
python src/train.py                                  # expect: models/model-best created

# 7. Evaluate + study errors
python src/evaluate.py                               # expect: model overall F1 around 0.95
python src/error_analysis.py                         # expect: about 11 errors

# 8. Run the app
uvicorn app.server:app --reload                      # open http://localhost:8000
```

**Small differences are normal:** retraining gives slightly different numbers each time (it starts from random dials). Don't be alarmed if F1 comes out as 0.94 or 0.96.

**If something fails:**

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named spacy` | venv not active | Run `.\venv\Scripts\Activate.ps1` |
| `Can't find model models/model-best` | Haven't trained yet | Run `python src/train.py` |
| `ModuleNotFoundError: baseline` | Running from the wrong folder | `cd` into `indian-recipe-ner` |
| Weird `�` characters in PowerShell | Display issue only, the file is fine | Run `$env:PYTHONIOENCODING='utf-8'` first |
| Server says "Address already in use" | Old server still running | Close the other terminal, or use `--port 8001` |

---

## Lesson 15 — A recipe for any NLP project

You can reuse this for your next idea (extracting skills from résumés, medicines from prescriptions, and so on):

1. **Define the task** precisely: what labels, and what counts as each.
2. **Collect** realistic text, including messy cases.
3. **Write guidelines** before labelling, and update them as you hit edge cases.
4. **Label** (more than one person if possible), and keep labels consistent.
5. **Split** into train / dev / test with a fixed seed. Never peek at test.
6. **Build a baseline** with simple rules or a simple method.
7. **Train** the model; watch the loss and the dev score.
8. **Evaluate** once on the test set, with metrics that fit the task (P/R/F1).
9. **Analyse errors**, and fix the *cause* (data or guidelines), not just the symptom.
10. **Ship** something people can try (an app or an API) and **write down the limits** honestly.

**A useful trick we used:** before the real labels existed, I tested the whole pipeline (convert → train → score) on throwaway data to prove the plumbing worked, then deleted it. Test your pipeline with fake data before you spend hours on real data.

---

## Lesson 16 — Glossary and viva Q&A

### Glossary

| Term | One-line meaning |
|---|---|
| **Annotation** | Adding labels to data by hand |
| **Baseline** | A simple method to compare the real model against |
| **Batch** | A small group of examples processed together |
| **Checkpoint** | A saved copy of the model at some moment |
| **Dev set** | Data used during training to monitor and choose the best version |
| **Dropout** | Randomly switching off parts of the network to stop memorising |
| **Embedding / vector** | A word as a list of numbers |
| **Epoch** | One full pass through the training data |
| **F1** | Balance of precision and recall |
| **Gold labels** | The trusted answer key |
| **Inference** | Using a trained model on new text |
| **Learning rate** | How big each adjustment to the dials is |
| **Loss** | How wrong the model currently is |
| **NER** | Finding and labelling entities in text |
| **Overfitting** | Memorising the training data and failing on new data |
| **Pipeline (spaCy)** | The chain of steps text goes through |
| **Precision** | Of what the model flagged, how much was right |
| **Recall** | Of what was really there, how much was found |
| **Regex** | A text pattern language |
| **Seed** | A number that makes randomness repeatable |
| **Span** | A stretch of text with a start and end |
| **Token** | One word or punctuation piece |
| **Train / test split** | Separating learning data from exam data |

### Questions an examiner might ask (and short answers)

1. **Why a regex baseline?** To prove the learned model adds value over simple rules. Without a comparison, a score is just a number.
2. **Why is PREP the worst label?** The fewest examples (189), the most varied phrasing, and its position changes (before or after the ingredient).
3. **Why does the regex win on UNIT?** Units are a small closed list, so rules are nearly perfect. The model sometimes confuses a unit-like word in a unit-like position (e.g. `medium` after a number).
4. **What is overfitting and how did you handle it?** Memorising the training set. We used dropout 0.1, monitored a separate dev set, and kept the best checkpoint rather than the last.
5. **Why three splits instead of two?** Dev guides decisions during training; test gives one final unbiased score. If you tune on test, it stops being unbiased.
6. **What does exact-match scoring mean?** Start, end and label must all match, so a near miss counts as one miss and one false alarm.
7. **Who labelled the data, and is that a problem?** An LLM (me, Claude) did, with no human review. It limits how far you can trust the absolute scores, so the labels can be re-checked in Label Studio.
8. **Why spaCy rather than a large language model?** It's small (6 MB), fast on CPU, runs offline, and gives exact character positions. Those are what the UI needs.
9. **How would you improve it?** More data (especially size words and prep after the ingredient), more than one labeller with an agreement score, and a bigger, fresher test set.
10. **What does the model do with a word it never saw?** It uses the word's prefix, suffix and shape plus its neighbours to make a best guess. That should help with spelling variants, but we haven't measured it, and it did fail on `tomatos`.

---

### Where to go next

- Read `README.md` for the results write-up.
- Do the "Do it" boxes in order. They add up to about two hours of hands-on work.
- Ask me to walk through any lesson live, or to quiz you viva-style.
