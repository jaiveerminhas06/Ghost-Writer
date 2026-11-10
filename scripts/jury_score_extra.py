"""Jury Phase 2 scoring: everything the notebook 22_jury needs beyond the Phase 1 val/test scores.

    python scripts/jury_score_extra.py heldout     # 20 fp16 jurors on the held-out prompt + held-out generator essays
    python scripts/jury_score_extra.py fp32        # 20 jurors on the fp32 path (fp32 weights + fp16 autocast, as in training) on val + test
    python scripts/jury_score_extra.py typos       # 20 fp16 jurors on typo-injected copies of the essays picked by 22_jury (results/22_typo_set.csv)

Each writes one results/22_*.csv (row_id + one logit column per seed) and refuses to overwrite. No essay text is written.
The held-out essays are used only to describe the jury; nothing is chosen from them (they were already scored once in notebook 20).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('HF_HUB_OFFLINE', '1')

import numpy as np
import pandas as pd
import torch
import transformers
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from jury_export import FP16, SEEDS, logits, src_dir
from src.data import load_splits
from src.paraphraser import inject_typos

transformers.logging.set_verbosity_error()
TYPO_RATE = 0.05


def score_all(texts, row_ids, out_name, path_kind):
    out = ROOT / 'results' / out_name
    if out.exists():
        sys.exit(f'{out} exists; refusing to overwrite')
    tok = AutoTokenizer.from_pretrained(FP16 / 's42')
    ids = tok(list(texts), truncation=True, max_length=512)['input_ids']
    pad = tok.pad_token_id
    cols = {}
    for seed in SEEDS:
        if path_kind == 'fp16':
            m = AutoModelForSequenceClassification.from_pretrained(FP16 / f's{seed}', torch_dtype=torch.float16).cuda().eval()
            cols[f's{seed}'] = logits(m, ids, pad, autocast=False)
        else:
            m = AutoModelForSequenceClassification.from_pretrained(src_dir(seed)).cuda().eval()
            cols[f's{seed}'] = logits(m, ids, pad, autocast=True)
        del m
        torch.cuda.empty_cache()
        print(f's{seed} done', flush=True)
    pd.DataFrame({'row_id': row_ids, **cols}).to_csv(out, index=False)
    print('wrote', out)


if __name__ == '__main__':
    what = sys.argv[1]
    assert torch.cuda.is_available() and torch.cuda.memory_allocated() == 0
    if what == 'heldout':
        d = load_splits('heldout_prompt', 'heldout_generator')
        score_all(d['text'], d.index, '22_juror_scores_heldout.csv', 'fp16')
    elif what == 'fp32':
        d = load_splits('val', 'test')
        score_all(d['text'], d.index, '22_juror_scores_fp32path.csv', 'fp32')
    elif what == 'typos':
        sel = pd.read_csv(ROOT / 'results' / '22_typo_set.csv')
        d = load_splits().loc[sel['row_id']]
        texts = [inject_typos(t, TYPO_RATE, seed=int(r)) for t, r in zip(d['text'], d.index)]   # per-essay seed = row_id: reproducible
        score_all(texts, d.index, '22_juror_scores_typos5.csv', 'fp16')
