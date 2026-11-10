"""Precompute the jury's answers for the built-in example essays, for a server without a GPU (results/22_jury_examples.json).

    python scripts/jury_precompute_examples.py

Needs the GPU and the 20 serving copies. For each example in demo/samples.json it stores the whole stream /api/jury would send for an
untyped trial and for typo trials with the fixed seeds in api/settings.JURY_PRECOMPUTED_SEEDS. The file holds a hash of each essay, not
its text. It refuses to overwrite an existing file. It uses the same code as the live endpoint (src/jury.py, api/jury_api.py).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from api import jury_api, results, settings
from src import jury as core
from src.paraphraser import inject_typos, words_changed

if settings.JURY_PRECOMPUTED.exists():
    sys.exit(f"{settings.JURY_PRECOMPUTED} exists; refusing to overwrite")
jury, cal = core.Jury(), core.Calibration()
assert jury.live, "needs a GPU"
out = {"description": "Precomputed jury trials for the built-in examples (no essay text). Written by scripts/jury_precompute_examples.py.",
       "typo_seeds": settings.JURY_PRECOMPUTED_SEEDS, "typo_rate": settings.JURY_TYPO_RATE, "scale": cal.scale(), "examples": {}}
for ex in results.examples():
    text = ex["text"]
    read = jury_api.reading(text, jury.tokenizer)
    n = len(text.split())
    entry = {"name": ex["name"], "label": ex["label"], "untyped": {"start": jury_api.start_event(n, read, None, cal.scale()), "events": list(core.trial(jury, cal, text))}, "typos": {}}
    for seed in settings.JURY_PRECOMPUTED_SEEDS:
        edited = inject_typos(text, settings.JURY_TYPO_RATE, seed=seed)
        share = words_changed(text, edited)
        typos = {"rate": settings.JURY_TYPO_RATE, "seed": seed, "words_changed": round(share * n), "words_changed_share": share}
        entry["typos"][str(seed)] = {"start": jury_api.start_event(n, read, typos, cal.scale()), "events": list(core.trial(jury, cal, text, edited))}
    out["examples"][jury_api.digest(text)] = entry
    s = entry["untyped"]["events"][-1]
    print(ex["name"], "| flagged by", s["says_ai"], "of 20 | official:", s["official"]["zone"])
settings.JURY_PRECOMPUTED.write_text(json.dumps(out, separators=(",", ":")))
print("wrote", settings.JURY_PRECOMPUTED)
