"""Ghost Writer web API: a thin layer that exposes the existing models over HTTP so a web page can use them.

Run from the repo root:   uvicorn api.main:app --port 8000
It only calls code in src/ (detector, explain, attribution, paraphraser); no model logic lives here.
Do not run it at the same time as the Streamlit demo: both load the models onto the 4 GB GPU.

Hosting: if frontend/dist exists (npm run build) this server also serves the web page, so one process and one URL
is enough. Settings come from environment variables: GW_MODEL_REPO (Hub repo holding models/), GW_ORIGINS
(extra allowed web origins), GW_RATE_LIMIT (requests per minute per visitor). Essay text is never logged or stored.
"""
import json
import os
import sys
import threading
import time
from collections import defaultdict, deque
from functools import lru_cache, wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if not os.environ.get("GW_MODEL_REPO"):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")    # developing locally: models are cached, never wait on the network

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Ghost Writer API")
# The React dev server runs on another port, so the browser needs permission to call us.
ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] + [o for o in os.environ.get("GW_ORIGINS", "").split(",") if o]
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])

# A public demo needs two guards. (1) Each visitor gets a limited number of requests per minute.
# (2) Only one model call runs at a time, so a few visitors cannot exhaust the CPU or memory.
RATE_LIMIT = int(os.environ.get("GW_RATE_LIMIT", "20"))
recent = defaultdict(deque)           # visitor -> times of their recent requests
model_lock = threading.Lock()


def one_at_a_time(fn):
    """Run the endpoint only while holding model_lock (queued visitors wait their turn)."""
    @wraps(fn)
    def run(*args, **kwargs):
        with model_lock:
            return fn(*args, **kwargs)
    return run


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST":
        # behind the host's proxy the real visitor address is the first entry of X-Forwarded-For
        who = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
        now, q = time.time(), recent[who]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
        q.append(now)
    return await call_next(request)

STRICTNESS = {"strict": 0.005, "standard": 0.01}     # target false-positive rates chosen in 09
SATURATED = 0.5          # occlusion changes below this on every sentence = flat (see 14), so use integrated gradients
MAX_SENTENCES = 80
# 128 steps are needed for the completeness check (14); the hosted CPU build uses fewer because the highlights only need the
# sentence ranking, which matched the 128-step ranking on 3 sample essays at 32 steps (Spearman 1.0). Set GW_IG_STEPS=32 there.
IG_STEPS = int(os.environ.get("GW_IG_STEPS", "128"))
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
@one_at_a_time
def score(essay: Essay):
    return verdict(essay.text, checked(essay))


@app.post("/api/explain")
@one_at_a_time
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
        method, scores = "integrated_gradients", integrated_gradients(det, text, steps=IG_STEPS)[1]
    shown = min(len(spans), MAX_SENTENCES)
    return {"method": method, "truncated": len(spans) > shown,
            "sentences": [{"start": int(s), "end": int(e), "text": text[s:e],
                           "contribution": None if np.isnan(c) else float(c)}     # None = beyond the 512 tokens read
                          for (s, e), c in zip(spans[:shown], scores[:shown])]}


@app.post("/api/attribution")
@one_at_a_time
def attribution_panel(essay: Essay):
    from src import attribution
    checked(essay)
    return {"families": [{"family": f, "probability": p}
                         for f, p in attribution.most_similar(attribution_model(), essay.text, k=3)],
            "heldout_accuracy": attribution.HELDOUT_SOURCE_ACCURACY}


class Rewrite(Essay):
    attack: str


@app.post("/api/rewrite")
@one_at_a_time
def rewrite(req: Rewrite):
    from src.paraphraser import inject_typos, words_changed
    threshold = checked(req)
    if req.attack not in ATTACKS:
        raise HTTPException(422, f"attack must be one of {list(ATTACKS)}")
    kind, param = ATTACKS[req.attack]
    edited = (inject_typos(req.text, param, seed=0) if kind == "typos"
              else t5().paraphrase_essays([req.text], temperature=param, seed=0)[0])
    return {"edited": edited, "words_changed": words_changed(req.text, edited), **verdict(edited, threshold)}


# The built web page (npm run build in frontend/). Mounted last so it never shadows /api.
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
