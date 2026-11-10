"""Jury export (Phase 1): fp16 serving copies of the 20 jurors, their re-scored validation/test logits, and the juror table.

    python scripts/jury_export.py                # export + re-score every juror whose model exists (skips finished ones)
    python scripts/jury_export.py --combine      # write results/22_juror_scores.csv and results/22_jurors.csv from the per-juror files

Jurors: seed 42 = models/distilroberta_finetuned (notebook 08), every other seed s = models/distilroberta_orig_s<s>.
For each juror
  1. models/jury_fp16/s<seed>/   the weights converted to fp16 (never overwrites)
  2. check: on 200 fixed validation essays the logits of the fp16 copy (fp16 weights, no autocast: what the API will use) must stay within
     0.05 of the logits of the training path (fp32 weights, fp16 autocast, as in train_variant.py); the largest difference is recorded
  3. every validation and test essay is re-scored with the fp16 copy -> results/22_jurors/s<seed>.csv  (row_id, logit)
     so each juror's tail probability p is computed from exactly the scores the API will produce.
Nothing here reads a held-out essay.
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('HF_HUB_OFFLINE', '1')

import numpy as np
import pandas as pd
import torch
import transformers
from sklearn.metrics import roc_auc_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.conformal import tail_p
from src.data import load_splits
from src.evaluate import threshold_for_fpr

transformers.logging.set_verbosity_error()
SEEDS = list(range(42, 62))
TAU = {'flag': 0.00235, 'above_usual': 0.01032}          # tau(1%) and tau(5%), 18b rule (d); applied to single models (they came from single-seed folds)
QUALITY_AUC = 0.999
MAX_DIFF = 0.05
OUT = ROOT / 'results' / '22_jurors'
FP16 = ROOT / 'models' / 'jury_fp16'


def src_dir(seed):
    return ROOT / 'models' / ('distilroberta_finetuned' if seed == 42 else f'distilroberta_orig_s{seed}')


@torch.no_grad()
def logits(model, tok_ids, pad, autocast, batch_size=64):
    """Logits for tokenised essays, length-sorted batches (as in train_variant.py). Returns an array in the input order."""
    order = np.argsort([len(x) for x in tok_ids], kind='stable')
    out = np.empty(len(tok_ids), dtype=np.float32)
    for i in range(0, len(order), batch_size):
        chunk = order[i:i + batch_size]
        width = max(len(tok_ids[j]) for j in chunk)
        x = torch.full((len(chunk), width), pad, dtype=torch.long)
        for r, j in enumerate(chunk):
            x[r, :len(tok_ids[j])] = torch.tensor(tok_ids[j])
        x = x.cuda()
        with torch.autocast('cuda', dtype=torch.float16, enabled=autocast):
            out[chunk] = model(input_ids=x, attention_mask=(x != pad).long()).logits.squeeze(1).float().cpu().numpy()
    return out


def export_one(seed, data, tok_cache):
    done = OUT / f's{seed}.csv'
    if done.exists():
        print(f's{seed}: already exported, skipping', flush=True)
        return
    t0 = time.time()
    src = src_dir(seed)
    dst = FP16 / f's{seed}'
    tok = AutoTokenizer.from_pretrained(src)
    if 'ids' not in tok_cache:                                         # all jurors share the distilroberta-base tokenizer
        tok_cache['ids'] = tok(list(data['text']), truncation=True, max_length=512)['input_ids']
        tok_cache['pad'] = tok.pad_token_id
    ids, pad = tok_cache['ids'], tok_cache['pad']
    model32 = AutoModelForSequenceClassification.from_pretrained(src).cuda().eval()
    sample = data['split'].eq('val').to_numpy().nonzero()[0]
    sample = np.random.default_rng(0).choice(sample, 200, replace=False)
    sub = [ids[i] for i in sample]
    ref = logits(model32, sub, pad, autocast=True)                     # the training path
    del model32
    torch.cuda.empty_cache()
    if not dst.exists():
        m = AutoModelForSequenceClassification.from_pretrained(src).half()
        dst.parent.mkdir(parents=True, exist_ok=True)
        m.save_pretrained(dst)
        tok.save_pretrained(dst)
        del m
    model16 = AutoModelForSequenceClassification.from_pretrained(dst, torch_dtype=torch.float16).cuda().eval()
    assert next(model16.parameters()).dtype == torch.float16
    served = logits(model16, sub, pad, autocast=False)
    diff = float(np.abs(served - ref).max())
    print(f's{seed}: fp16 vs training-path logits on 200 val essays, largest difference {diff:.4f} ({"ok" if diff <= MAX_DIFF else "OVER THE LIMIT"})', flush=True)
    all_logits = logits(model16, ids, pad, autocast=False)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({'row_id': data.index, 'logit': all_logits, 'fp16_max_diff_200': diff}).to_csv(done.with_suffix('.tmp'), index=False)
    done.with_suffix('.tmp').rename(done)
    print(f's{seed}: exported and re-scored {len(data):,} essays in {time.time() - t0:.0f} s', flush=True)
    del model16
    torch.cuda.empty_cache()


def combine(data):
    cols, rows = {}, []
    log = pd.read_csv(ROOT / 'results' / '17_final' / 'log.csv')
    log = log[(log['variant'] == 'baseline') & (log['fold'] == -1)].set_index('seed')
    val_h = (data['split'] == 'val') & (data['label'] == 0)
    val = data['split'] == 'val'
    n = int(val_h.sum())
    for seed in SEEDS:
        f = OUT / f's{seed}.csv'
        if not f.exists():
            continue
        s = pd.read_csv(f)
        assert (s['row_id'].to_numpy() == data.index.to_numpy()).all()
        cols[f's{seed}'] = s['logit'].to_numpy()
        lg = s['logit']
        auc = roc_auc_score(data.loc[val, 'label'], lg[val.to_numpy()])
        vh = lg[val_h.to_numpy()].to_numpy()
        desc = np.sort(vh)[::-1]
        c_flag = float(desc[int(np.floor(TAU['flag'] * (1 + n))) - 1])      # flag if the logit is ABOVE this: at most (tau*(1+n) - 1) val humans score at least as high
        c_above = float(desc[int(np.floor(TAU['above_usual'] * (1 + n))) - 1])
        # sanity: the same cut-offs through tail_p
        assert tail_p(np.array([np.nextafter(c_flag, np.inf)]), vh)[0] <= TAU['flag'] < tail_p(np.array([c_flag]), vh)[0]
        assert tail_p(np.array([np.nextafter(c_above, np.inf)]), vh)[0] <= TAU['above_usual'] < tail_p(np.array([c_above]), vh)[0]
        train_auc = float(log.loc[seed, 'val_auc']) if seed in log.index else np.nan
        rule_auc = train_auc if not np.isnan(train_auc) else auc
        rows.append({'seed': seed, 'is_ensemble_member': seed in (42, 43, 44), 'val_auc_training_log': train_auc, 'val_auc_fp16_rescored': round(auc, 5),
                     'auc_used_for_rule': round(rule_auc, 5), 'excluded_by_rule': bool(rule_auc < QUALITY_AUC),
                     'val1pct_logit_cutoff': round(float(threshold_for_fpr(pd.Series(vh), 0.01)), 3),
                     'flag_logit_cutoff_tau1pct': round(c_flag, 3), 'above_usual_logit_cutoff_tau5pct': round(c_above, 3),
                     'fp16_max_diff_200': float(s['fp16_max_diff_200'].iloc[0]), 'train_minutes': float(log.loc[seed, 'minutes']) if seed in log.index else np.nan,
                     'peak_gpu_gb': float(log.loc[seed, 'peak_gpu_gb']) if seed in log.index else np.nan, 'val_humans': n})
    scores = pd.DataFrame({'row_id': data.index, 'split': data['split'].to_numpy(), 'label': data['label'].to_numpy(), **cols})
    for name, df in (('22_juror_scores.csv', scores), ('22_jurors.csv', pd.DataFrame(rows))):
        path = ROOT / 'results' / name
        if path.exists():
            sys.exit(f'{path} exists; not overwriting. Delete it by hand if you really want to rebuild.')
        df.to_csv(path, index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--combine', action='store_true')
    ap.add_argument('--seeds', nargs='*', type=int)
    a = ap.parse_args()
    data = load_splits('val', 'test')
    if a.combine:
        combine(data)
    else:
        cache = {}
        for seed in a.seeds or SEEDS:
            if src_dir(seed).exists():
                export_one(seed, data, cache)
            else:
                print(f's{seed}: model not trained yet, skipping', flush=True)
