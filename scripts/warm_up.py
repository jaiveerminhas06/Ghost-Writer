"""Loads every model once, so the first click in a demo is as quick as the tenth.

    python scripts/warm_up.py http://localhost:8000

The server loads each model the first time it is needed (the detector, the explainer, the attribution model, the T5 paraphraser).
This asks for each of them once with a built-in example and prints how long it took. A failure is a warning, not an error: the
demo still works, only that first click will be slow.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
text = next(iter(json.loads((Path(__file__).resolve().parent.parent / "demo" / "samples.json").read_text()).values()))


def post(path, body, seconds=180):
    req = urllib.request.Request(base + "/api" + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=seconds).read())


meta = json.loads(urllib.request.urlopen(base + "/api/meta", timeout=30).read())
steps = [("detector", "/score", {"text": text}), ("highlights", "/explain", {"text": text}), ("which-AI guess", "/attribution", {"text": text}),
         ("typos", "/rewrite", {"text": text, "method": "typos5"})]
if meta.get("t5_available") is not False:
    steps.append(("T5 paraphrase", "/rewrite", {"text": text, "method": "t5"}))
for name, path, body in steps:
    t0 = time.time()
    try:
        post(path, body)
        print(f"  warmed {name:16} {time.time() - t0:5.1f} s")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  WARNING: could not warm {name}: {e}")
