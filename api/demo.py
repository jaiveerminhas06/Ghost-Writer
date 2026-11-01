"""The demo class: 30 essays with known authors, picked from essays the model never trained on (demo/class_sample/README in
make_class_sample.py says how). The page loads them through the same upload path as any class; the labels are used only to compare
the detector's flags with the truth, in one sentence."""
import json
from functools import lru_cache

from . import settings


@lru_cache(maxsize=1)
def demo_class():
    meta = json.loads((settings.DEMO_CLASS / "labels.json").read_text())
    essays = [{"name": e["file"], "text": (settings.DEMO_CLASS / e["file"]).read_text()} for e in meta["essays"]]
    labels = {e["file"]: e["label"] for e in meta["essays"]}
    return {"essays": essays, "labels": labels, "prompt": meta["prompt"], "split": meta["split"]}


def counts():
    """For /api/meta: how many essays, so the page's button can say so without hard-coding it."""
    labels = demo_class()["labels"].values()
    return {"essays": len(labels), "human": sum(v == "human" for v in labels), "ai": sum(v == "ai" for v in labels)}
