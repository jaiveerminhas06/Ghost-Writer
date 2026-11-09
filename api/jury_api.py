"""The pieces of POST /api/jury that are not model code: the stream format, the reading information, and the precomputed answers a
machine without a GPU serves for the built-in example essays.

Format (application/x-ndjson, one JSON object per line):
  {"type":"start", ...}    essay facts (words, tokens read, typos applied) and the scale the marks are drawn on
  {"type":"juror", ...}    one per juror, in seed order: seed, p, position (-log10 p), zone, at_cap, ensemble_member (+ "before" if typos)
  {"type":"summary", ...}  counts per zone, the official verdict, and (with typos) how many jurors changed their mind
  {"type":"error", ...}    only if something goes wrong after the stream has begun (a refusal before it is an ordinary HTTP error)
Essay text is never in the stream and never logged.
"""
import hashlib
import json
from functools import lru_cache
from types import SimpleNamespace

from . import settings


def line(event):
    return json.dumps(event, separators=(",", ":"), allow_nan=False) + "\n"


def reading(text, tokenizer, max_len=512):
    """How much of the essay the jurors read: they truncate at max_len tokens (the same rule as /api/score)."""
    from src.explain import visible_chars
    tokens = len(tokenizer(text)["input_ids"])
    truncated = tokens > max_len
    return {"tokens": tokens, "tokens_read": min(tokens, max_len), "truncated": truncated,
            "read_chars": visible_chars(SimpleNamespace(tok=tokenizer, max_len=max_len), text) if truncated else len(text)}


def start_event(words, read, typos, scale, precomputed=False):
    return {"type": "start", "api": settings.JURY_API, "jurors": 20, "words": words, **read, "typos": typos, "scale": scale, "precomputed": precomputed}


def digest(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def precomputed():
    """results/22_jury_examples.json, written by scripts/jury_precompute_examples.py: for each built-in example, the full stream of an
    untyped trial and of trials with typos for a few fixed seeds. It holds a hash of each example, not its text."""
    path = settings.JURY_PRECOMPUTED
    if not path.exists():
        return None
    return json.loads(path.read_text())


def precomputed_run(text, typos, seed):
    """(start event, juror and summary events) for a built-in example, or None if `text` is not one of them. With typos, a seed that was
    not precomputed is replaced by one that was (the start event says which)."""
    data = precomputed()
    if not data:
        return None
    entry = data["examples"].get(digest(text))
    if entry is None:
        return None
    if not typos:
        run = entry["untyped"]
    else:
        seeds = data["typo_seeds"]
        used = seed if seed in seeds else seeds[seed % len(seeds)]
        run = entry["typos"][str(used)]
    start = {**run["start"], "precomputed": True}
    if typos:
        start["typos"] = {**start["typos"], "requested_seed": seed}
    return start, run["events"]
