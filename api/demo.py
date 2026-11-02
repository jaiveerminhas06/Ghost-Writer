"""The demo classes: 30 essays each with known authors, from the two held-out topics, picked from essays the model never trained on
(demo/class_sample/make_class_sample.py says how). The page loads one through the same upload path as any class; the labels are used
only to compare the detector's flags with the truth, in one sentence."""
import json
from functools import lru_cache

from . import settings
from .errors import ApiError


def topics():
    """The folders under demo/class_sample/ that hold a class, in a fixed order."""
    return sorted(p.parent.name for p in settings.DEMO_CLASS.glob("*/labels.json"))


@lru_cache(maxsize=None)
def demo_class(slug):
    folder = settings.DEMO_CLASS / slug
    if slug not in topics():
        raise ApiError(404, "not_found", "There is no such demo class.")
    meta = json.loads((folder / "labels.json").read_text())
    essays = [{"name": e["file"], "text": (folder / e["file"]).read_text()} for e in meta["essays"]]
    labels = {e["file"]: e["label"] for e in meta["essays"]}
    return {"topic": slug, "prompt": meta["prompt"], "essays": essays, "labels": labels, "split": meta["split"]}


def listing():
    """For /api/meta: each class's name and size, so the page's buttons can say so without hard-coding them."""
    out = []
    for slug in topics():
        labels = list(demo_class(slug)["labels"].values())
        out.append({"id": slug, "name": demo_class(slug)["prompt"], "essays": len(labels), "human": labels.count("human"), "ai": labels.count("ai")})
    return out
