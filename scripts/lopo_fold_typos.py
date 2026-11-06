"""One fold of leave-one-prompt-out training for the Phase 5 stability tests (notebook 19_ensemble_stability.ipynb).

Identical to scripts/lopo_fold.py (notebook 08 recipe, original recipe, same three groups of scores) with two differences: the output goes to
results/19_phase5/lopo/ (so nothing in results/16b_lopo is touched), and the left-out essays are ALSO scored after 5% typos (two independent
typo copies, columns logit_typo1 and logit_typo2), because the fold model is not kept and the flip-rate test needs it.

Original docstring of lopo_fold.py follows.

One fold of leave-one-prompt-out training (Phase 2b, notebook 16b_topic_lopo.ipynb).

    python scripts/lopo_fold.py --fold 0 --seed 42        # fold k = the k-th of the 13 non-held-out prompts, sorted by name

What one fold does, in plain words:
  1. Take one of the 13 ordinary prompts (not the two held-out ones) and call it the LEFT-OUT prompt.
  2. Fine-tune DistilRoBERTa with exactly the recipe of notebook 08 (2 epochs, lr 2e-5, 6% warm-up, 512 tokens, fp16, batch 16)
     on the train essays of the OTHER 12 prompts. The model never sees the left-out prompt.
  3. Keep the epoch with the best AUC on the val essays of the other 12 prompts (as 08 does).
  4. Score three groups of essays and write the scores to results/16b_lopo/scores_foldKK_seedSS.csv:
       left_out    every essay (train + val + test, both labels) of the left-out prompt: the model has never seen this topic
       other_val   val essays of the other 12 prompts (the 1%-false-flag threshold is chosen on their humans)
       other_test  test essays of the other 12 prompts
  5. Append one line to results/16b_lopo/log.csv (fold, times, val AUC, the left-out prompt's false-flag rate).
The model weights are NOT saved (disk); only the scores are. If the scores file already exists the fold is skipped, so the whole
run can be restarted at any time (scripts/lopo_run.sh).
The two held-out prompts (Electoral college, Summer projects) and the held-out generators are never touched here.
"""
import argparse
import gc
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')
os.environ.setdefault('HF_HUB_OFFLINE', '1')

import numpy as np
import pandas as pd
import torch
import transformers
from sklearn.metrics import roc_auc_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from src.data import load_splits
from src.evaluate import threshold_for_fpr, wilson_interval
from src.paraphraser import inject_typos

transformers.logging.set_verbosity_error()
MODEL_NAME, MAX_LEN, EPOCHS, LR, BATCH = 'distilroberta-base', 512, 2, 2e-5, 16
OUT = ROOT / 'results' / '19_phase5' / 'lopo'


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    print(f'[{now()}] {msg}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fold', type=int, required=True)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--smoke', action='store_true', help='tiny run to test the pipeline; writes to /tmp, not results/')
    a = ap.parse_args()

    out_dir = Path('/tmp/lopo_smoke') if a.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    scores_path = out_dir / f'scores_fold{a.fold:02d}_seed{a.seed}.csv'
    if scores_path.exists():
        log(f'fold {a.fold} seed {a.seed}: {scores_path.name} exists, skipping')
        return

    data = load_splits('train', 'val', 'test')
    prompts = sorted(data['prompt_name'].unique())
    assert len(prompts) == 13, prompts
    prompt = prompts[a.fold]
    train = data[(data['split'] == 'train') & (data['prompt_name'] != prompt)]
    val_other = data[(data['split'] == 'val') & (data['prompt_name'] != prompt)]
    test_other = data[(data['split'] == 'test') & (data['prompt_name'] != prompt)]
    left = data[data['prompt_name'] == prompt]
    epochs = EPOCHS
    if a.smoke:
        train, val_other, test_other, left = (d.sample(min(len(d), n), random_state=0) for d, n in
                                              [(train, 320), (val_other, 160), (test_other, 100), (left, 100)])
        epochs = 1
    t_start = time.time()
    start_str = now()
    log(f'fold {a.fold} seed {a.seed}: left-out prompt = {prompt!r}')
    log(f'train {len(train):,} ({train["label"].mean():.1%} AI) | val_other {len(val_other):,} | left-out {len(left):,} '
        f'({(left["label"] == 0).sum()} human) | test_other {len(test_other):,}')
    assert not set(train['prompt_name']) & {prompt}, 'left-out prompt leaked into training'
    assert set(data['prompt_name']) == set(prompts) and not set(train.index) & set(left.index)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    pad = tokenizer.pad_token_id
    ids = lambda d: tokenizer(d['text'].tolist(), truncation=True, max_length=MAX_LEN)['input_ids']
    train, val_other, test_other, left = (d.assign(ids=ids(d)) for d in (train, val_other, test_other, left))
    device = torch.device('cuda')

    def batches(df, batch_size, shuffle=False, seed=0):
        tok, labels = df['ids'].tolist(), df['label'].to_numpy()
        order = np.argsort([len(x) for x in tok], kind='stable')                 # bucket by length, as in 08
        chunks = [order[i:i + batch_size] for i in range(0, len(order), batch_size)]
        if shuffle:
            np.random.default_rng(seed).shuffle(chunks)
        for chunk in chunks:
            x = torch.full((len(chunk), max(len(tok[i]) for i in chunk)), pad, dtype=torch.long)
            for r, i in enumerate(chunk):
                x[r, :len(tok[i])] = torch.tensor(tok[i])
            yield x, (x != pad).long(), torch.tensor(labels[chunk], dtype=torch.float32), chunk

    @torch.no_grad()
    def logits_of(model, df, batch_size=64):
        model.eval()
        out = np.empty(len(df), dtype=np.float32)
        with torch.autocast('cuda', dtype=torch.float16):
            for x, mask, _, chunk in batches(df, batch_size):
                out[chunk] = model(input_ids=x.to(device), attention_mask=mask.to(device)).logits.squeeze(1).float().cpu().numpy()
        return out

    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=1).to(device)
    params = list(model.parameters())
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    steps = epochs * int(np.ceil(len(train) / BATCH))
    sched = get_linear_schedule_with_warmup(opt, num_warmup_steps=int(0.06 * steps), num_training_steps=steps)
    scaler = torch.amp.GradScaler()
    best_auc, best_state, best_epoch = -1, None, 0
    for epoch in range(1, epochs + 1):
        model.train()
        t0, losses = time.time(), []
        for x, mask, y, _ in batches(train, BATCH, shuffle=True, seed=a.seed + epoch):
            with torch.autocast('cuda', dtype=torch.float16):
                logits = model(input_ids=x.to(device), attention_mask=mask.to(device)).logits.squeeze(1)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits.float(), y.to(device))
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt); scaler.update(); sched.step()
            losses.append(loss.item())
            del logits, loss
        val_auc = roc_auc_score(val_other['label'], logits_of(model, val_other))
        log(f'  epoch {epoch}: train loss {np.mean(losses):.4f} | val AUC {val_auc:.5f} | {(time.time() - t0) / 60:.1f} min | '
            f'peak GPU {torch.cuda.max_memory_allocated() / 1e9:.2f} GB')
        if val_auc > best_auc:
            best_auc, best_epoch = val_auc, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)

    parts = {'left_out': left, 'other_val': val_other, 'other_test': test_other}
    rows = []
    for role, d in parts.items():
        s = logits_of(model, d)
        frame = pd.DataFrame({'row_id': d.index, 'split': d['split'].to_numpy(), 'label': d['label'].to_numpy(),
                              'prompt_name': d['prompt_name'].to_numpy(), 'role': role, 'logit': s})
        if role == 'left_out':                                              # the same essays after 5% typos, two independent copies
            for copy in (1, 2):
                typo_text = [inject_typos(t, 0.05, seed=copy * 1_000_003 + int(i)) for i, t in zip(d.index, d['text'])]
                typo = d.assign(ids=tokenizer(typo_text, truncation=True, max_length=MAX_LEN)['input_ids'])
                frame[f'logit_typo{copy}'] = logits_of(model, typo)
        rows.append(frame)
    scores = pd.concat(rows, ignore_index=True)
    tmp = scores_path.with_suffix('.tmp')
    scores.to_csv(tmp, index=False)
    tmp.rename(scores_path)                                                     # appears only once complete

    vh = scores[(scores['role'] == 'other_val') & (scores['label'] == 0)]['logit']
    thr = threshold_for_fpr(vh, 0.01)
    lh = scores[(scores['role'] == 'left_out') & (scores['label'] == 0)]['logit']
    la = scores[(scores['role'] == 'left_out') & (scores['label'] == 1)]['logit']
    k, n = int((lh >= thr).sum()), len(lh)
    lo, hi = wilson_interval(k, n)
    row = {'fold': a.fold, 'seed': a.seed, 'left_out_prompt': prompt, 'start': start_str, 'end': now(),
           'minutes': round((time.time() - t_start) / 60, 1), 'best_epoch': best_epoch, 'val_auc': round(best_auc, 5),
           'threshold_1pct': round(thr, 3), 'humans_n': n, 'humans_flagged': k, 'fpr_pct': round(100 * k / n, 2),
           'fpr_lo': round(100 * lo, 2), 'fpr_hi': round(100 * hi, 2),
           'ai_n': len(la), 'ai_caught_pct': round(100 * float((la >= thr).mean()), 2) if len(la) else np.nan,
           'peak_gpu_gb': round(torch.cuda.max_memory_allocated() / 1e9, 2)}
    log_path = out_dir / 'log.csv'
    pd.DataFrame([row]).to_csv(log_path, mode='a', header=not log_path.exists(), index=False)
    log(f'fold {a.fold} done: left-out humans flagged {k}/{n} = {row["fpr_pct"]}% [{row["fpr_lo"]}, {row["fpr_hi"]}], '
        f'val AUC {best_auc:.5f}, {row["minutes"]} min')
    del model, opt, scaler, best_state
    gc.collect(); torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
