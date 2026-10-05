"""
Masala Dabba backend.

  POST /predict   {"text": "..."} -> entities from the trained spaCy model
  POST /baseline  {"text": "..."} -> entities from the regex baseline
  GET  /metrics                   -> report/metrics.json
  GET  /                          -> the static frontend (app/static)

The input can hold many ingredient lines (one per row), because the model
was trained on single ingredient lines. Each line is tagged separately.

Run from the project root:
  uvicorn app.server:app --reload
"""

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent

# the tagger code lives in src/, so make it importable from here
sys.path.insert(0, str(ROOT / "src"))
import baseline
import predict

STATIC = Path(__file__).resolve().parent / "static"
MAX_LINES = 60

@asynccontextmanager
async def lifespan(app):
    predict.load_model()   # load once at start so the first request is fast
    yield


app = FastAPI(title="Masala Dabba", lifespan=lifespan)


@app.middleware("http")
async def no_stale_files(request, call_next):
    """Make the browser re-check files on every load (cheap: unchanged files answer 304).
    Without this, a browser can keep running an old app.js after we edit it."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


class TextIn(BaseModel):
    text: str


def split_lines(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(400, "Empty input")
    return lines[:MAX_LINES]


def tokens(line):
    """spaCy's tokens for a line (with character offsets), for the Tokens view in the UI.
    Both taggers share this tokenizer, so the same tokens are shown for either."""
    return [{"text": t.text, "start": t.idx, "end": t.idx + len(t.text)}
            for t in predict.load_model().make_doc(line) if not t.is_space]


@app.post("/predict")
def predict_route(body: TextIn):
    return {"source": "model",
            "lines": [{"text": l, "entities": predict.tag(l), "tokens": tokens(l)}
                      for l in split_lines(body.text)]}


@app.post("/baseline")
def baseline_route(body: TextIn):
    return {"source": "baseline",
            "lines": [{"text": l, "entities": baseline.extract(l), "tokens": tokens(l)}
                      for l in split_lines(body.text)]}


@app.get("/metrics")
def metrics_route():
    path = ROOT / "report" / "metrics.json"
    if not path.exists():
        raise HTTPException(404, "Run python src/evaluate.py first")
    return json.loads(path.read_text(encoding="utf-8"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
