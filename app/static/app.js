// Masala Dabba — frontend logic (vanilla JS, no build step)

const LABELS = ["QUANTITY", "UNIT", "INGREDIENT", "PREP"];
const SPICE = { QUANTITY: "haldi", UNIT: "elaichi", INGREDIENT: "mirchi", PREP: "kesar" };
const SHORT = { QUANTITY: "QTY", UNIT: "UNIT", INGREDIENT: "ING", PREP: "PREP" };

// Quick-try dishes: typical ingredient lists, typed the way recipe sites write them.
const DISHES = {
  paneer: `2 tbsp butter
1 tsp jeera
1 bay leaf
2 medium onions, finely chopped
1 tbsp ginger garlic paste
3 tomatoes pureed
10 cashews soaked in hot water
1 tsp kashmiri red chilli powder
1/2 tsp garam masala
200 g paneer cubed
2 tbsp fresh cream
1 tsp kasuri methi crushed
salt to taste`,
  sambar: `1/2 cup toor dal
1 tbsp tamarind pulp
2 drumsticks cut into pieces
8 small shallots peeled
1 tomato chopped
2 tbsp sambar powder
1/4 tsp haldi
1 tsp mustard seeds
2 dry red chillies
few curry leaves
a pinch of hing
salt as required`,
  chole: `1 cup kabuli chana soaked overnight
2 tbsp oil
1 tsp jeera
2 onions finely chopped
1 inch ginger grated
2 green chillies slit
2 tomatoes pureed
2 tsp chole masala
1/2 tsp amchur
1 tea bag
salt to taste
2 tbsp chopped coriander`,
  biryani: `500 g chicken cut into pieces
2 cups basmati rice washed and soaked
1 cup thick curd
3 large onions thinly sliced
1 tbsp ginger garlic paste
2 tsp biryani masala
4 green cardamom
1 inch dalchini
few strands kesar soaked in milk
1/2 cup mint leaves chopped
3 tbsp ghee
salt as needed`,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const LABEL_HELP = {
  QUANTITY: "QUANTITY — how much (haldi)",
  UNIT: "UNIT — the measure (elaichi)",
  INGREDIENT: "INGREDIENT — the item (mirchi)",
  PREP: "PREP — what is done to it (kesar)",
};

const state = { mode: "model", view: "highlight", scale: 1, results: null, metricsLoaded: false };

// ---------- scaling a recipe ----------
// Only spans the tagger labelled QUANTITY are scaled. A wrong tag therefore causes a
// visible mistake (e.g. "soaked for 30 minutes" becoming "60 minutes").
const FRACS = { "½": 1 / 2, "¼": 1 / 4, "¾": 3 / 4, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 1 / 8, "⅜": 3 / 8, "⅝": 5 / 8, "⅞": 7 / 8 };
const FRAC_RE = new RegExp(`^(\\d+)?\\s*([${Object.keys(FRACS).join("")}])$`);

// "2", "1.5", "1/2", "2 1/2", "1-1/2", "1½", "½"  ->  number, or null if it is not a plain amount
function parseAmount(s) {
  s = s.trim();
  let m;
  if ((m = s.match(/^\d+(?:\.\d+)?$/))) return parseFloat(s);
  if ((m = s.match(/^(\d+)\/(\d+)$/))) return +m[2] ? +m[1] / +m[2] : null;
  if ((m = s.match(/^(\d+)(?:\s+|-)(\d+)\/(\d+)$/))) return +m[3] ? +m[1] + +m[2] / +m[3] : null;
  if ((m = s.match(FRAC_RE))) return (m[1] ? +m[1] : 0) + FRACS[m[2]];
  return null;
}

// a single amount, or a range such as "2-3" / "6 - 8" / "3 to 4"  ->  [low] or [low, high], else null
function parseQuantity(s) {
  const single = parseAmount(s);
  if (single !== null) return [single];
  const m = s.match(/^(.+?)\s*(?:-|–|to)\s*(.+)$/);
  if (m) {
    const a = parseAmount(m[1]), b = parseAmount(m[2]);
    if (a !== null && b !== null) return [a, b];
  }
  return null;
}

// 0.5 -> "½", 2.5 -> "2½", 3 -> "3", 0.17 -> "0.17"
function formatAmount(x) {
  const NICE = [[0, ""], [1 / 8, "⅛"], [1 / 4, "¼"], [1 / 3, "⅓"], [3 / 8, "⅜"], [1 / 2, "½"],
                [5 / 8, "⅝"], [2 / 3, "⅔"], [3 / 4, "¾"], [7 / 8, "⅞"], [1, null]];
  const whole = Math.floor(x + 1e-9);
  const frac = x - whole;
  for (const [v, ch] of NICE) {
    if (Math.abs(frac - v) < 0.02) {
      if (ch === null) return String(whole + 1);
      return ch === "" ? String(whole) : (whole ? `${whole}${ch}` : ch);
    }
  }
  return String(Math.round(x * 100) / 100);
}

// rebuild a line with its QUANTITY spans multiplied by k, keeping every span's offsets correct
function scaleLine(line, k) {
  if (k === 1) return line;
  const ents = [...line.entities].sort((a, b) => a.start - b.start);
  let text = "", pos = 0;
  const out = [];
  for (const e of ents) {
    text += line.text.slice(pos, e.start);
    let shown = e.text, was = null;
    if (e.label === "QUANTITY") {
      const q = parseQuantity(e.text);
      if (q && q.every((v) => v < 10000)) { shown = q.map((v) => formatAmount(v * k)).join("-"); was = e.text; }
    }
    out.push({ ...e, start: text.length, end: text.length + shown.length, text: shown, was });
    text += shown;
    pos = e.end;
  }
  return { ...line, text: text + line.text.slice(pos), entities: out };
}
const scaled = (result) => ({ ...result, lines: result.lines.map((l) => scaleLine(l, state.scale)) });

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------- API ----------
async function tag(endpoint, text) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`${endpoint} returned ${res.status}`);
  return res.json();
}

// ---------- status messages ----------
function showStatus(el, html) { el.innerHTML = html; el.hidden = false; }
const LOADING = `Tempering the model…<span class="tadka" aria-hidden="true"><i></i><i></i><i></i><i></i></span>`;
const EMPTY = `Kuch nahi mila — try another line<small>No quantities, units, ingredients or prep found.</small>`;

// ---------- run ----------
async function run() {
  const text = $("#input").value.trim() || $("#input").placeholder;
  if (!$("#input").value.trim()) $("#input").value = text;

  const btn = $("#run");
  btn.disabled = true;
  $("#results").hidden = true;
  showStatus($("#status"), LOADING);

  try {
    // always fetch both so switching modes is instant
    const [model, base] = await Promise.all([tag("/predict", text), tag("/baseline", text)]);
    state.results = { model, baseline: base };
    const found = model.lines.some((l) => l.entities.length) || base.lines.some((l) => l.entities.length);
    if (!found) { showStatus($("#status"), EMPTY); return; }
    $("#status").hidden = true;
    render();
  } catch (err) {
    showStatus($("#status"), `Kuch nahi mila — try another line<small>${esc(err.message)}. Is the server running?</small>`);
  } finally {
    btn.disabled = false;
  }
}

// the result shown in thali + table: baseline in baseline mode, otherwise the model (with the chosen scale applied)
const primary = () => scaled(state.mode === "baseline" ? state.results.baseline : state.results.model);

function render() {
  if (!state.results) return;
  $("#results").hidden = false;
  renderHighlight();
  renderTokens();
  renderThali();
  renderTable();
  $("#highlight-view").hidden = state.view !== "highlight";
  $("#tokens-view").hidden = state.view !== "tokens";
  $("#thali-view").hidden = state.view !== "thali";
  $("#scale-row").hidden = state.view === "tokens";   // tokens are shown for the original text
}

// ---------- view 1: highlight ----------
function highlightLine(line) {
  const ents = [...line.entities].sort((a, b) => a.start - b.start);
  if (!ents.length) return `${esc(line.text)} <span class="hl-empty">— nothing found</span>`;
  let html = "", pos = 0;
  ents.forEach((e, i) => {
    html += esc(line.text.slice(pos, e.start));
    const tip = LABEL_HELP[e.label] + (e.was ? ` · scaled from ${e.was}` : "");
    html += `<span class="ent ${e.label}${e.was ? " scaled" : ""}" style="--i:${i}" title="${esc(tip)}"><span class="tag">${SHORT[e.label]}</span><span class="pill">${esc(e.text)}</span></span>`;
    pos = e.end;
  });
  return html + esc(line.text.slice(pos));
}

const sameEntities = (a, b) =>
  a.length === b.length && a.every((e, i) => e.start === b[i].start && e.end === b[i].end && e.label === b[i].label);

function renderHighlight() {
  const view = $("#highlight-view");
  if (state.mode !== "compare") {
    view.innerHTML = primary().lines.map((l, i) =>
      `<div class="hl-line"><span class="hl-num">${i + 1}</span><span class="hl-text">${highlightLine(l)}</span></div>`).join("");
    return;
  }
  // side by side: baseline | model, one row per line, rows that differ are tinted
  const { model, baseline } = state.results;
  const shownModel = scaled(model), shownBaseline = scaled(baseline);
  const sorted = (l) => [...l.entities].sort((a, b) => a.start - b.start);
  let diffs = 0;
  const rows = model.lines.map((m, i) => {
    // "differ" is judged on the original tags, so the count does not change with the scale
    const differs = !sameEntities(sorted(m), sorted(baseline.lines[i]));
    if (differs) diffs++;
    return `<div class="cmp-line ${differs ? "diff" : ""}">
      <span class="hl-num">${i + 1}${differs ? '<span class="diff-dot" title="The two taggers disagree"></span>' : ""}</span>
      <div><span class="col-label">Regex baseline</span><span class="hl-text">${highlightLine(shownBaseline.lines[i])}</span></div>
      <div><span class="col-label">spaCy model</span><span class="hl-text">${highlightLine(shownModel.lines[i])}</span></div>
    </div>`;
  }).join("");
  view.innerHTML = `<div class="cmp-head"><span></span><span>Regex baseline</span>
      <span>spaCy model <span class="sum">${diffs} of ${model.lines.length} lines differ</span></span></div>${rows}`;
}

// ---------- view: tokens ----------
// spaCy's tokenizer chops each line into tokens, and the NER makes one decision per token.
// B-/I-/O tags are derived from the entity spans here, just for display.
function renderTokens() {
  const result = state.mode === "baseline" ? state.results.baseline : state.results.model;   // original text, never scaled
  const who = state.mode === "baseline" ? "regex baseline" : "spaCy model";
  const overlaps = (t, e) => t.start < e.end && e.start < t.end;
  const lines = result.lines.map((line, i) => {
    const cols = line.tokens.map((t) => {
      const ent = line.entities.find((e) => overlaps(t, e));
      let tag = "O", cls = "";
      if (ent) {
        const first = line.tokens.find((u) => overlaps(u, ent));
        tag = (first === t ? "B-" : "I-") + SHORT[ent.label];
        cls = ent.label;
      }
      const c = cls ? ` ${cls}` : "";   // no class at all for "O" tokens
      return `<div class="tokcol"><span class="tokbox${c}">${esc(t.text)}</span><span class="toktag${c}">${tag}</span></div>`;
    }).join("");
    return `<div class="tok-line"><span class="hl-num">${i + 1}</span><div class="tok-flow">${cols}</div></div>`;
  }).join("");
  $("#tokens-view").innerHTML = `${lines}<p class="note tok-note">Tokens from spaCy's tokenizer, tagged by the <b>${who}</b>.
    B = begins an entity, I = inside it, O = outside. The labels are stored as spans; the B/I/O view is derived for display
    (spaCy's NER uses a BILUO-style scheme internally and decides token by token).</p>`;
}

// ---------- view 2: thali ----------
function renderThali() {
  // group entity texts per label; repeated values ("tsp") are shown once with a count
  const groups = Object.fromEntries(LABELS.map((l) => [l, new Map()]));
  primary().lines.forEach((line) => line.entities.forEach((e) => {
    const key = e.text.toLowerCase();
    const g = groups[e.label];
    g.set(key, { text: e.text, n: (g.get(key)?.n || 0) + 1 });
  }));

  // vector from each bowl's centre to the plate centre, so items appear to fly out of the middle
  const origin = { QUANTITY: [1, 1], UNIT: [-1, 1], INGREDIENT: [1, -1], PREP: [-1, -1] };
  // short values fit more per bowl than long ingredient names
  const small = window.innerWidth < 640;
  const MAX_ITEMS = small ? { QUANTITY: 6, UNIT: 5, INGREDIENT: 3, PREP: 3 }
                          : { QUANTITY: 8, UNIT: 8, INGREDIENT: 4, PREP: 4 };
  const bowls = LABELS.map((label) => {
    const items = [...groups[label].values()];
    const MAX = MAX_ITEMS[label];
    const [sx, sy] = origin[label];
    const chips = items.slice(0, MAX).map((it, i) =>
      `<span class="item" style="--i:${i};--dx:${sx * 90}%;--dy:${sy * 160}%">${esc(it.text)}${it.n > 1 ? `<b>×${it.n}</b>` : ""}</span>`).join("");
    const more = items.length > MAX ? `<span class="more">+${items.length - MAX} more</span>` : "";
    return `<div class="katori ${label}">
      <h3>${label}<small>${SPICE[label]} · ${items.length}</small></h3>
      <div class="items">${chips || '<span class="more">empty</span>'}</div>${more}
    </div>`;
  }).join("");

  const who = state.mode === "baseline" ? "regex baseline" : "spaCy model";
  $("#thali-view").innerHTML = `<div class="thali" role="img" aria-label="Entities sorted into four bowls">
    ${bowls}<div class="thali-center"><svg><use href="#rangoli"/></svg>Sorted by the ${who}</div></div>`;
}

// ---------- table ----------
function renderTable() {
  const result = primary();
  $("#table-source").textContent = state.mode === "baseline" ? "· regex baseline" : "· spaCy model";
  $("#entity-table tbody").innerHTML = result.lines.map((line, i) => {
    const cell = (label) => {
      const vals = line.entities.filter((e) => e.label === label).map((e) => esc(e.text));
      return vals.length ? vals.join("<br>") : '<span class="dash">—</span>';
    };
    return `<tr><td>${i + 1}</td><td class="line-cell">${esc(line.text)}</td>${LABELS.map((l) => `<td>${cell(l)}</td>`).join("")}</tr>`;
  }).join("");
}

async function copyJSON() {
  const data = primary().lines.map((l) => ({
    line: l.text,
    entities: l.entities.map(({ text, label, start, end }) => ({ text, label, start, end })),
  }));
  const json = JSON.stringify(data, null, 2);
  const btn = $("#copy");
  try {
    await navigator.clipboard.writeText(json);
  } catch {
    // fallback for http:// pages where the clipboard API is blocked
    const ta = Object.assign(document.createElement("textarea"), { value: json });
    document.body.append(ta); ta.select(); document.execCommand("copy"); ta.remove();
  }
  btn.textContent = "Copied ✓";
  setTimeout(() => (btn.textContent = "Copy JSON"), 1400);
}

// ---------- metrics tab ----------
async function loadMetrics() {
  if (state.metricsLoaded) return;
  const status = $("#metrics-status");
  showStatus(status, LOADING);
  try {
    const res = await fetch("/metrics");
    if (!res.ok) throw new Error("metrics.json not found — run python src/evaluate.py");
    renderMetrics(await res.json());
    status.hidden = true;
    state.metricsLoaded = true;
  } catch (err) {
    showStatus(status, `Kuch nahi mila<small>${esc(err.message)}</small>`);
  }
}

function renderMetrics(m) {
  const d = m.dataset;
  const f = (x) => x.toFixed(3);
  const gain = m.model.overall.f - m.baseline.overall.f;

  const barRow = (name, model, base) => `
    <div class="bar-row" title="${name}: model ${f(model)} · baseline ${f(base)}">
      <span class="m">${name}</span>
      <div class="track"><div class="fill" style="width:${model * 100}%"></div><div class="tick" style="left:calc(${base * 100}% - 1px)"></div></div>
      <span class="val"><b>${f(model)}</b><span>baseline ${f(base)}</span></span>
    </div>`;

  const card = (label, mod, base, extra = "") => `
    <div class="metric-card ${label}">
      <h3>${label === "OVERALL" ? "Overall (micro)" : label[0] + label.slice(1).toLowerCase()} <small>${extra}</small></h3>
      ${barRow("P", mod.p, base.p)}${barRow("R", mod.r, base.r)}${barRow("F1", mod.f, base.f)}
    </div>`;

  $("#metrics").innerHTML = `
    <div class="headline">
      <div class="stat hero"><div class="k">Model F1 · test</div><div class="v">${f(m.model.overall.f)}</div>
        <div class="s">${gain >= 0 ? "+" : ""}${f(gain)} vs regex baseline (${f(m.baseline.overall.f)})</div></div>
      <div class="stat"><div class="k">Annotated lines</div><div class="v">${d.lines}</div>
        <div class="s">train ${d.splits.train} · dev ${d.splits.dev} · test ${d.splits.test}</div></div>
      <div class="stat"><div class="k">Hinglish lines</div><div class="v">${d.hinglish_pct}%</div>
        <div class="s">contain a Roman-script Hindi / regional word</div></div>
      <div class="stat"><div class="k">Hand-written messy</div><div class="v">${d.manual_lines}</div>
        <div class="s">typos, ranges, "to taste"</div></div>
    </div>

    <div class="section-title"><h2>Entities per label</h2></div>
    <div class="counts">${LABELS.map((l) => `<span class="count-pill" style="--c:var(--${l.toLowerCase()})"><i></i>${l} <b>${d.entities[l]}</b></span>`).join("")}</div>

    <div class="section-title"><h2>Precision · Recall · F1 on the test set</h2>
      <span class="note">${m.test_lines} held-out lines · exact span + label match</span></div>
    <div class="metric-key"><span><i class="k1"></i>spaCy model (bar)</span><span><i class="k2"></i>regex baseline (marker)</span></div>
    <div class="metric-grid">
      ${LABELS.map((l) => card(l, m.model.per_label[l], m.baseline.per_label[l], SPICE[l])).join("")}
      ${card("OVERALL", m.model.overall, m.baseline.overall, "all labels")}
    </div>`;
}

// ---------- wiring ----------
function selectRadio(group, attr, value) {
  $$(`${group} [${attr}]`).forEach((b) => b.setAttribute("aria-checked", String(b.getAttribute(attr) === value)));
}

$$("[data-mode]").forEach((b) => b.addEventListener("click", () => {
  state.mode = b.dataset.mode;
  selectRadio(".mode-row", "data-mode", state.mode);
  render();
}));
$$("[data-view]").forEach((b) => b.addEventListener("click", () => {
  state.view = b.dataset.view;
  selectRadio(".results-head", "data-view", state.view);
  if (state.view === "tokens" && state.scale !== 1) {   // tokens describe the original text
    state.scale = 1;
    selectRadio(".tools-row", "data-scale", "1");
  }
  render();
}));
$$("[data-scale]").forEach((b) => b.addEventListener("click", () => {
  state.scale = parseFloat(b.dataset.scale);
  selectRadio(".tools-row", "data-scale", b.dataset.scale);
  render();
}));
$$("[data-dish]").forEach((b) => b.addEventListener("click", () => {
  $("#input").value = DISHES[b.dataset.dish];
  run();
}));
$$("[data-tab]").forEach((b) => b.addEventListener("click", () => {
  const tab = b.dataset.tab;
  $$("[data-tab]").forEach((t) => t.setAttribute("aria-selected", String(t === b)));
  $("#panel-extract").hidden = tab !== "extract";
  $("#panel-metrics").hidden = tab !== "metrics";
  $("#panel-about").hidden = tab !== "about";
  if (tab === "metrics") loadMetrics();
  if (tab === "about") fillRecipeCard();
}));

// ---------- The Recipe tab ----------
// The numbers on the card are read from report/metrics.json, so they can never drift from the real results.
let recipeCardFilled = false;
async function fillRecipeCard() {
  if (recipeCardFilled) return;
  try {
    const res = await fetch("/metrics");
    if (!res.ok) return;                  // keep the static fallback numbers
    const m = await res.json();
    const d = m.dataset;
    const f2 = (x) => x.toFixed(2);
    const set = (name, val) => { const el = $(`[data-fact="${name}"]`); if (el) el.textContent = val; };
    set("model-f1", f2(m.model.overall.f));
    set("lines", d.lines);
    set("manual", d.manual_lines);
    set("scraped", d.lines - d.manual_lines);
    set("entities", Object.values(d.entities).reduce((a, b) => a + b, 0).toLocaleString("en-IN"));
    set("hinglish", Math.round(d.hinglish_pct) + "%");
    set("overall", `${f2(m.model.overall.f)} vs ${f2(m.baseline.overall.f)}`);
    LABELS.forEach((l) => {
      const el = $(`[data-note="${l}"]`);
      if (el) el.textContent = `${f2(m.model.per_label[l].f)} vs ${f2(m.baseline.per_label[l].f)}`;
    });
    recipeCardFilled = true;
  } catch { /* offline or metrics missing: the static numbers stay */ }
}

// example cards on the recipe tab: run the line in the Extract tab
$$("[data-try]").forEach((b) => b.addEventListener("click", () => {
  $("#input").value = b.dataset.try;
  $('[data-tab="extract"]').click();
  run();
  window.scrollTo({ top: 0, behavior: "smooth" });
}));
$("#run").addEventListener("click", run);
$("#copy").addEventListener("click", copyJSON);
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
});

// Deep links for the demo, e.g.  /#dish=sambar&mode=compare&view=thali  or  /#tab=metrics
//   also: &view=tokens   &scale=2   &text=2 cups rice soaked for 30 minutes
const params = new URLSearchParams(location.hash.slice(1));
if (params.get("mode")) $(`[data-mode="${params.get("mode")}"]`)?.click();
if (params.get("view")) $(`[data-view="${params.get("view")}"]`)?.click();
if (params.get("scale")) $(`[data-scale="${params.get("scale")}"]`)?.click();
if (params.get("tab")) $(`[data-tab="${params.get("tab")}"]`)?.click();
if (DISHES[params.get("dish")]) $(`[data-dish="${params.get("dish")}"]`).click();
else if (params.get("text")) { $("#input").value = params.get("text"); run(); }
