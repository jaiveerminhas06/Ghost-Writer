"""Ghost Writer web API: a thin layer that exposes the existing models over HTTP so a web page can use them.

Run from the repo root:   uvicorn api.main:app --port 8000
It only calls code in src/ (detector, explain, attribution, paraphraser); no model logic lives here. The numbers the page
quotes come from the results files through api/results.py; every tunable number is in api/settings.py.
Do not run it at the same time as the Streamlit demo: both load the models onto the 4 GB GPU.

If frontend/dist exists (npm run build) this server also serves the web page, so one process and one URL is enough.
Essay text is never logged or stored.
"""
import math
import os
import sys
import threading
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if not os.environ.get("GW_MODEL_REPO"):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")    # developing locally: models are cached, never wait on the network

import numpy as np
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import demo, limiter, results, settings, uploads
from .errors import ApiError, api_error_handler, validation_handler
from .language import english_check
from .textfiles import extract_text

app = FastAPI(title="Ghost Writer API")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_handler)
app.add_middleware(uploads.BodyLimit)          # added before CORS so that a refusal also carries the CORS headers
# The React dev server runs on another port, so the browser needs permission to call us.
app.add_middleware(CORSMiddleware, allow_origins=settings.DEV_ORIGINS + settings.EXTRA_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Retry-After"])


# ---------- models: loaded on first use, once, then kept ----------
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


# Only one model call runs at a time (one small GPU). A request waits its turn; if the wait is too long it is told so.
_model_lock = threading.Lock()


@contextmanager
def model_turn():
    if not _model_lock.acquire(timeout=settings.LOCK_WAIT_SECONDS):
        raise ApiError(503, "busy", "The detector is busy with another request. Please try again in a moment.")
    try:
        yield
    finally:
        _model_lock.release()


# ---------- checks shared by the endpoints ----------
def checked(text):
    """Refuse text the detector should not score. Returns the word count. The text itself is never altered, because the page
    holds the same string and the highlight positions refer to it."""
    if len(text) > settings.MAX_CHARS:
        raise ApiError(413, "too_long", f"This essay is longer than {settings.MAX_CHARS:,} characters. Paste a shorter one.")
    n = len(text.split())
    if n < settings.MIN_WORDS:
        raise ApiError(422, "too_short", f"The detector needs {settings.MIN_WORDS} words to read. {settings.MIN_WORDS - n} more to go.")
    problem = english_check(text)
    if problem:
        raise ApiError(422, *problem)
    return n


def reading_info(text, det):
    """How much of the essay the detector reads: it truncates at max_len tokens."""
    from src.explain import visible_chars
    tokens = len(det.tok(text)["input_ids"])
    truncated = tokens > det.max_len
    return {"tokens": tokens, "tokens_read": min(tokens, det.max_len), "truncated": truncated,
            "read_chars": visible_chars(det, text) if truncated else len(text)}


def scored(text):
    det = detector()
    return {"logit": float(det.score([text])[0]), "words": len(text.split()), **reading_info(text, det)}


# ---------- endpoints ----------
class Essay(BaseModel):
    text: str = Field(max_length=settings.MAX_CHARS * 3)     # the real limit is checked() so it can answer in words


@app.get("/api/meta")
def meta():
    return results.meta()


@app.get("/api/demo-class")
def demo_class():
    """The demo class's essays and their true labels (see api/demo.py)."""
    return demo.demo_class()


@app.post("/api/score")
def score(essay: Essay, request: Request):
    limiter.charge(request)
    checked(essay.text)
    with model_turn():
        return scored(essay.text)


@app.post("/api/explain")
def explain(essay: Essay, request: Request):
    """Per-sentence contributions. Same rule as demo/app.py: occlusion, or integrated gradients if occlusion is flat."""
    limiter.charge(request)
    checked(essay.text)
    from src.explain import integrated_gradients, occlusion
    text = essay.text
    with model_turn():
        det = detector()
        spans, occ, _ = occlusion(det, text)
        valid = ~np.isnan(occ)
        if valid.any() and np.abs(occ[valid]).max() >= settings.SATURATED:
            method, values = "occlusion", occ
        else:
            method, values = "integrated_gradients", integrated_gradients(det, text, steps=settings.IG_STEPS)[1]
    shown = min(len(spans), settings.MAX_SENTENCES)
    return {"method": method, "list_truncated": len(spans) > shown,
            "sentences": [{"start": int(s), "end": int(e), "score": None if np.isnan(v) else float(v)}   # None = beyond the 512 tokens read
                          for (s, e), v in zip(spans[:shown], values[:shown])]}


@app.post("/api/attribution")
def attribution_panel(essay: Essay, request: Request):
    limiter.charge(request)
    checked(essay.text)
    from src import attribution
    with model_turn():
        top = attribution.most_similar(attribution_model(), essay.text, k=3)
    return {"families": [{"family": f, "share": float(p)} for f, p in top], "heldout_accuracy": attribution.HELDOUT_SOURCE_ACCURACY}


class Rewrite(Essay):
    method: str
    seed: int = settings.ATTACK_SEED


@app.post("/api/rewrite")
def rewrite(req: Rewrite, request: Request):
    limiter.charge(request)
    if req.method not in settings.ATTACKS:
        raise ApiError(422, "bad_request", f"method must be one of {', '.join(settings.ATTACKS)}.")
    n = checked(req.text)
    from src.paraphraser import inject_typos, words_changed
    kind, setting = settings.ATTACKS[req.method]
    if kind == "t5" and not results.t5_available():
        raise ApiError(503, "model_missing", "Paraphrasing needs the T5 model, which isn't loaded on this machine. Typos still work.")
    with model_turn():
        edited = (inject_typos(req.text, setting, seed=req.seed) if kind == "typos"
                  else t5().paraphrase_essays([req.text], temperature=setting, seed=req.seed)[0])
        share = words_changed(req.text, edited)
        return {"method": req.method, "edited": edited, "words_changed": round(share * n),
                "words_changed_share": share, **scored(edited)}


@app.post("/api/batch")
def batch(request: Request, files: list[UploadFile] = File(...)):
    """Score a set of files (a class). One result per file, in the order sent; a bad file never fails the others."""
    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise ApiError(413, "too_many_files", f"Send at most {settings.MAX_FILES_PER_REQUEST} files at a time.")
    limiter.charge(request, max(1, math.ceil(len(files) / settings.BATCH_FILES_PER_UNIT)))
    items = []
    for f in files:
        item = {"name": f.filename, "words": None, "logit": None, "text": None, "error": None}
        try:
            text = extract_text(f.filename or "", f.file.read(settings.MAX_FILE_BYTES + 1))
            item["words"] = len(text.split())
            checked(text)
            item["text"] = text            # kept only for scored essays: the page reopens them from here, the server stores nothing
        except ApiError as e:
            item["error"] = {"code": e.code, "message": e.detail}
        items.append(item)
    ready = [i for i in items if i["text"] is not None]
    if ready:
        with model_turn():
            for i, logit in zip(ready, detector().score([i["text"] for i in ready])):
                i["logit"] = float(logit)
    return {"results": items}


# ---------- the built web page (npm run build in frontend/) ----------
@app.get("/{path:path}", include_in_schema=False)
def web_page(path: str):
    """Serve frontend/dist. Any path that is not a file gets index.html, so a link straight to /fool or /class works."""
    if path.startswith("api/"):
        raise ApiError(404, "not_found", "There is no such endpoint.")
    dist = settings.DIST
    if not dist.exists():
        raise ApiError(404, "no_frontend", "The web page has not been built yet. Run npm run build in frontend/.")
    target = (dist / path).resolve()
    if path and target.is_file() and dist.resolve() in target.parents:
        return FileResponse(target)
    return FileResponse(dist / "index.html")
