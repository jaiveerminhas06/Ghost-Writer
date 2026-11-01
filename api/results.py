"""Everything the page quotes, read from the project's results files, never typed in by hand.

meta() is what GET /api/meta returns. The files are read once; a missing or reshaped file stops the server at the first
request with a clear message, rather than showing a wrong number.
"""
import json
from functools import lru_cache

import pandas as pd

from . import demo, settings

# Built-in examples: display names (the artboard's wording) in the order of demo/samples.json. Labels come from each
# essay's title in that file, which starts "AI essay" or "Human essay".
EXAMPLE_NAMES = ["AI essay by Claude", "Student essay", "Student essay it wrongly flags"]


@lru_cache(maxsize=1)
def thresholds():
    """Logit thresholds chosen in notebook 09: {'strict': 7.80, 'standard': 4.67}."""
    t = pd.read_csv(settings.RESULTS / "09_thresholds.csv", index_col=0)["roberta"]
    return {name: float(t[f"{rate}"]) for name, rate in settings.FLAG_RATES.items()}


@lru_cache(maxsize=1)
def _humans_flagged_on_unseen_topics():
    """% of human essays flagged on the two held-out topics, per setting, from notebook 09's rate table (3 header rows)."""
    raw = pd.read_csv(settings.RESULTS / "09_threshold_rates.csv", header=None)
    col = next(i for i in range(raw.shape[1]) if raw.iloc[1, i] == "heldout_prompt" and "humans flagged" in str(raw.iloc[0, i]))
    rows = raw[(raw[0] == "DistilRoBERTa")].set_index(1)
    return {"strict": float(rows.loc["FPR 0.5%", col]), "standard": float(rows.loc["FPR 1.0%", col])}


@lru_cache(maxsize=1)
def _worst_topic():
    """The single unseen topic with the highest human false-flag rate at each threshold, from notebook 14's error table."""
    e = pd.read_csv(settings.RESULTS / "14_errors.csv")
    h = e[(e.label == 0) & (e.split == "heldout_prompt")]
    out = {}
    for name, thr in thresholds().items():
        rate = (h.logit >= thr).groupby(h.prompt_name).mean().sort_values(ascending=False)
        out[name] = {"topic": str(rate.index[0]), "percent": round(float(rate.iloc[0]) * 100, 1)}
    return out


@lru_cache(maxsize=1)
def rates():
    avg = _humans_flagged_on_unseen_topics()
    worst = _worst_topic()
    return {name: {"unseen_topics_percent": round(avg[name], 1), "worst_topic": worst[name],
                   "familiar_topics_percent": settings.FLAG_RATES[name] * 100} for name in settings.FLAG_RATES}


# The rewrites the page offers, and the row of results/13_attack.csv that measured each.
ATTACK_ROWS = {"typos5": "typos 5%", "typos10": "typos 10%", "t5": "T5 paraphrase (T=1.0)", "t5_heavy": "T5 paraphrase (T=1.5)"}


@lru_cache(maxsize=1)
def attacks():
    """What notebook 13 measured, at the standard 1% flag line: the share of AI essays still caught after each rewrite (and before
    any: "original"), the share of student essays flagged, and how many words each rewrite changed in the AI essays."""
    a = pd.read_csv(settings.RESULTS / "13_attack.csv", index_col=0)
    caught, humans, changed = "DistilRoBERTa: % AI caught (test)", "DistilRoBERTa: % humans flagged", "% words changed (AI essays)"
    return {
        "threshold": "standard",
        "caught_after": {"original": float(a.loc["original", caught]), **{m: float(a.loc[row, caught]) for m, row in ATTACK_ROWS.items()}},
        "humans_flagged": {"original": float(a.loc["original", humans]), **{m: float(a.loc[row, humans]) for m, row in ATTACK_ROWS.items()}},
        "words_changed_percent": {m: float(a.loc[row, changed]) for m, row in ATTACK_ROWS.items()},
    }


@lru_cache(maxsize=1)
def trained_on():
    return int((pd.read_csv(settings.SPLITS_CSV)["split"] == "train").sum())


@lru_cache(maxsize=1)
def examples():
    raw = json.loads(settings.SAMPLES_JSON.read_text())
    out = []
    for i, (title, text) in enumerate(raw.items()):
        label = "ai" if title.lower().startswith("ai") else "human"
        out.append({"id": i, "name": EXAMPLE_NAMES[i] if i < len(EXAMPLE_NAMES) else title, "label": label,
                    "words": len(text.split()), "text": text})
    return out


def t5_available():
    """True if the T5 paraphraser is in the local Hugging Face cache (the server never downloads at request time)."""
    from huggingface_hub import try_to_load_from_cache
    from src.paraphraser import T5Paraphraser
    return isinstance(try_to_load_from_cache(T5Paraphraser.NAME, "config.json"), str)


def meta():
    return {
        "api_version": settings.API_VERSION,
        "thresholds": thresholds(),
        "rates": rates(),
        "attacks": attacks(),
        "trained_on": trained_on(),
        "limits": {"min_words": settings.MIN_WORDS, "max_chars": settings.MAX_CHARS, "max_tokens": 512,
                   "max_files": settings.MAX_FILES_PER_REQUEST, "max_file_bytes": settings.MAX_FILE_BYTES, "file_types": [".docx", ".pdf", ".txt"]},
        "t5_available": t5_available(),
        "examples": examples(),
        "demo_class": demo.counts(),
    }
