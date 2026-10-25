"""Ghost Writer web API: a thin layer that exposes the existing models over HTTP so a web page can use them.

Run from the repo root:   uvicorn api.main:app --port 8000
It only calls code in src/ (detector, explain, attribution, paraphraser); no model logic lives here.
Do not run it at the same time as the Streamlit demo: both load the models onto the 4 GB GPU.
"""
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")        # models are cached locally; never wait on the network

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Ghost Writer API")
# The React dev server runs on another port, so the browser needs permission to call us.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

STRICTNESS = {"strict": 0.005, "standard": 0.01}     # target false-positive rates chosen in 09
SATURATED = 0.5          # occlusion changes below this on every sentence = flat (see 14), so use integrated gradients
MAX_SENTENCES = 80
MIN_WORDS = 40
ATTACKS = {"typos_5": ("typos", 0.05), "typos_10": ("typos", 0.10),
           "paraphrase_light": ("t5", 1.0), "paraphrase_heavy": ("t5", 1.5)}


# Models load on first use, once, then stay in memory.
@lru_cache(maxsize=1)
def detector():
    import transformers
    transformers.logging.set_verbosity_error()
    from src.detector import Detector
    return Detector()


@lru_cache(maxsize=1)
def attribution_model():
    from src import attribution
    return attribution.load()


@lru_cache(maxsize=1)
def t5():
    import transformers
    transformers.logging.set_verbosity_error()
    from src.paraphraser import T5Paraphraser
    return T5Paraphraser()


class Essay(BaseModel):
    text: str = Field(max_length=30_000)
    strictness: str = "strict"


def checked(essay: Essay):
    if len(essay.text.split()) < MIN_WORDS:
        raise HTTPException(422, f"Enter at least {MIN_WORDS} words.")
    if essay.strictness not in STRICTNESS:
        raise HTTPException(422, "strictness must be 'strict' or 'standard'")
    return detector().thresholds[STRICTNESS[essay.strictness]]


def verdict(text, threshold):
    logit = float(detector().score([text])[0])
    n_tokens = len(detector().tok(text)["input_ids"])
    return {"score": logit, "threshold": threshold, "flagged": logit >= threshold,
            "tokens": n_tokens, "tokens_read": min(n_tokens, detector().max_len)}


@app.get("/api/samples")
def samples():
    return json.load(open(ROOT / "demo" / "samples.json"))


@app.post("/api/score")
def score(essay: Essay):
    return verdict(essay.text, checked(essay))


@app.post("/api/explain")
def explain(essay: Essay):
    """Per-sentence contributions. Same rule as the Streamlit demo: occlusion, or integrated gradients if occlusion is flat."""
    checked(essay)
    from src.explain import occlusion, integrated_gradients
    det, text = detector(), essay.text
    spans, occ, _ = occlusion(det, text)
    valid = ~np.isnan(occ)
    if valid.any() and np.abs(occ[valid]).max() >= SATURATED:
        method, scores = "occlusion", occ
    else:
        method, scores = "integrated_gradients", integrated_gradients(det, text)[1]
    shown = min(len(spans), MAX_SENTENCES)
    return {"method": method, "truncated": len(spans) > shown,
            "sentences": [{"start": int(s), "end": int(e), "text": text[s:e],
                           "contribution": None if np.isnan(c) else float(c)}     # None = beyond the 512 tokens read
                          for (s, e), c in zip(spans[:shown], scores[:shown])]}


@app.post("/api/attribution")
def attribution_panel(essay: Essay):
    from src import attribution
    checked(essay)
    return {"families": [{"family": f, "probability": p}
                         for f, p in attribution.most_similar(attribution_model(), essay.text, k=3)],
            "heldout_accuracy": attribution.HELDOUT_SOURCE_ACCURACY}


class Rewrite(Essay):
    attack: str


@app.post("/api/rewrite")
def rewrite(req: Rewrite):
    from src.paraphraser import inject_typos, words_changed
    threshold = checked(req)
    if req.attack not in ATTACKS:
        raise HTTPException(422, f"attack must be one of {list(ATTACKS)}")
    kind, param = ATTACKS[req.attack]
    edited = (inject_typos(req.text, param, seed=0) if kind == "typos"
              else t5().paraphrase_essays([req.text], temperature=param, seed=0)[0])
    return {"edited": edited, "words_changed": words_changed(req.text, edited), **verdict(edited, threshold)}
