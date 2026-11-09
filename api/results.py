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
EXAMPLE_NAMES = ["AI essay by Claude", "Student essay", "Student essay the earlier detector flagged"]
EXAMPLE_NOTES = [None, None, "A student essay the earlier single-model detector flagged."]


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
    """The built-in essays. The first three come from demo/samples.json; two more (a real student essay the final system still flags, and
    an AI essay that splits the jury) from demo/jury_samples.json, chosen by rules recorded in notebook 22. `note` says what is special."""
    raw = json.loads(settings.SAMPLES_JSON.read_text())
    out = []
    for i, (title, text) in enumerate(raw.items()):
        label = "ai" if title.lower().startswith("ai") else "human"
        out.append({"id": i, "name": EXAMPLE_NAMES[i] if i < len(EXAMPLE_NAMES) else title, "label": label, "kind": "example",
                    "note": EXAMPLE_NOTES[i] if i < len(EXAMPLE_NOTES) else None, "words": len(text.split()), "text": text})
    for e in json.loads(settings.JURY_SAMPLES_JSON.read_text()):
        out.append({"id": len(out), "name": e["name"], "label": e["label"], "kind": e["kind"], "note": e["note"], "words": len(e["text"].split()), "text": e["text"]})
    return out


# ---------- the jury and the final system (notebooks 20, 22, 22b) ----------
def _frac(percent):
    """A percentage as a fraction, rounded to 6 places so 0.70 is 0.007 and not 0.006999999999999999."""
    return round(float(percent) / 100, 6)


def _cell(text):
    """'0.70 [0.48, 0.95]' (a percentage, the way notebook 20 saved it) -> {'value': 0.0070, 'lo': 0.0048, 'hi': 0.0095}, fractions."""
    import re
    m = re.fullmatch(r"\s*([\d.]+) \[([\d.]+), ([\d.]+)\]\s*", str(text))
    if not m:
        raise ValueError(f"unexpected cell in results/20_heldout_tables.csv: {text!r}")
    return {"value": _frac(m[1]), "lo": _frac(m[2]), "hi": _frac(m[3])}       # saved as percentages; the API speaks fractions


@lru_cache(maxsize=1)
def official():
    """The official verdict's own figures from notebook 20 (held out, scored once): operating point A (flag line tau(1%)), on-topic essays."""
    t = pd.read_csv(settings.RESULTS / "20_heldout_tables.csv")
    a = t[(t["block"] == "on-topic only") & (t["operating point"] == "A")]
    def row(table, name):
        r = a[(a["table"] == table) & (a["rows"] == name)]
        assert len(r) == 1, (table, name)
        return r.iloc[0]
    pooled = "POOLED (bootstrap interval)"
    h1, h2, h3 = row("H1", pooled), row("H2", pooled), row("H3", pooled)
    h6 = t[t["table"] == "H6"]
    p_ai = {}
    for _, r in h6.iterrows():
        p_ai.setdefault(r["AI share"], {})[{"cannot tell": "above_usual"}.get(r["zone"], r["zone"].replace(" ", "_"))] = _cell(r["P(AI | zone) %"])
    return {
        "model": "three-seed ensemble (seeds 42-44), p scale, rule (d)",
        "tau": {"flag": 0.00235, "above_usual": 0.01032},
        "students_unseen_topics": {"n": int(h1["n"]), "flagged": _cell(h1["% flagged"]), "above_usual": _cell(h1["% cannot tell"]),
                                   "by_topic": {name: {"n": int(row("H1", name)["n"]), "flagged": _cell(row("H1", name)["% flagged"])}
                                                for name in ("Electoral college", "Summer projects")}},
        "ai_unseen_prompts": {"n": int(h2["n"]), "flagged": _cell(h2["% flagged"])},
        "ai_unseen_generators": {"n": int(h3["n"]), "flagged": _cell(h3["% flagged"]), "above_usual": _cell(h3["% cannot tell"])},
        "p_ai_given_zone": p_ai,
        "source": "results/20_heldout_tables.csv (on-topic essays, scored once)",
    }


ATTACK_IDS = {"original": "original", "typos 2%": "typos2", "typos 5%": "typos5", "typos 10%": "typos10", "T5 paraphrase (T=1.0)": "t5",
              "T5 paraphrase (T=1.5)": "t5_heavy", "T5 (T=1.0) + typos 5%": "t5_typos"}
GROUP_IDS = {"AI, test": "ai_test", "AI, held-out generators": "ai_unseen_generators", "Students, test": "students_test",
             "Students, held-out prompts": "students_unseen_prompts"}


@lru_cache(maxsize=1)
def attacks_final():
    """Notebook 22b: the official verdict under attack, per group and attack, as fractions (0-1). Held-out groups are descriptive. 'above_usual'
    is the share who land in 'above usual' (flagged-or-above minus flagged); for students the page must quote it wherever it says edited AI
    essays land there."""
    r = pd.read_csv(settings.RESULTS / "22b_attack_final.csv")
    out = {}
    for _, x in r.iterrows():
        g = out.setdefault(GROUP_IDS[x["group"]], {"n": int(x["n"]), "descriptive": "held-out" in x["group"], "attacks": {}})
        g["attacks"][ATTACK_IDS[x["attack"]]] = {
            "flagged": _frac(x["flagged_pct"]), "flagged_lo": _frac(x["flagged_lo"]), "flagged_hi": _frac(x["flagged_hi"]),
            "flagged_or_above": _frac(x["flag_or_above_pct"]), "flagged_or_above_lo": _frac(x["flag_or_above_lo"]), "flagged_or_above_hi": _frac(x["flag_or_above_hi"]),
            "above_usual": round((int(x["flag_or_above_k"]) - int(x["flagged_k"])) / int(x["n"]), 6),
            "flip": _frac(x["flip_pct"]), "flip_lo": _frac(x["flip_lo"]), "flip_hi": _frac(x["flip_hi"]),
            "flip_k": int(x["flip_k"]), "flip_of": int(x["flip_denominator"]),
            "jurors_flagging_before": float(x["mean_jurors_flagging_before"]), "jurors_flagging_after": float(x["mean_jurors_flagging_after"]),
            "words_changed": _frac(x["words_changed_pct"])}
    return out


def _num(v):
    return None if pd.isna(v) else float(v)


@lru_cache(maxsize=1)
def jury_statistics():
    """Notebook 22's statistics, straight from results/22_jury_summary.csv: stat -> population -> group -> metric -> value/lo/hi/n.
    S1 (the whole distribution of how many jurors flag) is kept for the all-twenty group only."""
    s = pd.read_csv(settings.RESULTS / "22_jury_summary.csv")
    s = s[~((s["stat"] == "S1") & (s["group"] != "all20"))]
    out = {}
    for _, r in s.iterrows():
        out.setdefault(r["stat"], {}).setdefault(r["population"], {}).setdefault(str(r["group"]), {})[r["metric"]] = {
            "value": _num(r["value"]), "lo": _num(r["lo"]), "hi": _num(r["hi"]), "n": _num(r["n"])}
    return out


@lru_cache(maxsize=1)
def jurors():
    """One row per juror: validation AUC, flag line, detection and false-flag rates at its own line, and the gap to its score ceiling."""
    t = pd.read_csv(settings.RESULTS / "22_jurors.csv").set_index("seed")
    p = pd.read_csv(settings.RESULTS / "22_jury_per_juror.csv").set_index("seed")
    return [{"seed": int(s), "ensemble_member": bool(t.loc[s, "is_ensemble_member"]), "val_auc": float(t.loc[s, "val_auc_fp16_rescored"]),
             "flag_line_logit": float(t.loc[s, "flag_logit_cutoff_tau1pct"]), "ceiling_logit": float(p.loc[s, "ceiling"]), "gap": float(p.loc[s, "gap"]),
             "detect_test_ai": float(p.loc[s, "test_AI"]), "detect_unseen_prompt_ai": float(p.loc[s, "heldout_prompt_AI"]),
             "detect_unseen_generator_ai": float(p.loc[s, "heldout_generator_AI"]),
             "flag_test_students": float(p.loc[s, "test_humans"]), "flag_unseen_prompt_students": float(p.loc[s, "heldout_prompt_humans"])}
            for s in t.index]


def jury_meta(live):
    from src import jury as core
    return {"api": settings.JURY_API, "live": bool(live), "jurors": len(core.SEEDS), "ensemble_seeds": list(core.ENSEMBLE_SEEDS),
            "typo_rate": settings.JURY_TYPO_RATE, "scale": core.Calibration().scale(), "statistics": jury_statistics(), "per_juror": jurors(),
            "attacks_final": attacks_final(), "source": "results/22_*.csv, results/22b_*.csv",
            "units": "every share and rate in this block and in `official` is a fraction between 0 and 1; gaps and ceilings are logits; *_k, *_of, *_count and jurors_flagging_* are counts"}


def t5_available():
    """True if the T5 paraphraser is in the local Hugging Face cache (the server never downloads at request time)."""
    from huggingface_hub import try_to_load_from_cache
    from src.paraphraser import T5Paraphraser
    return isinstance(try_to_load_from_cache(T5Paraphraser.NAME, "config.json"), str)


def meta(jury_live=False):
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
        "demo_classes": demo.listing(),
        "official": official(),
        "jury": jury_meta(jury_live),
    }
