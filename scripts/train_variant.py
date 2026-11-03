"""Phase 3 training (notebook 17_augment.ipynb): the notebook 08 recipe with one of three changes. Two modes.

    python scripts/train_variant.py --variant A --fold 11 --seed 42        # one leave-one-prompt-out fold (like scripts/lopo_fold.py)
    python scripts/train_variant.py --variant B --full --seed 43           # train on the whole training set and SAVE the model

Variants
    baseline   no change (only used with --full, to train extra seeds of the original recipe if no variant wins)
    A          spelling/typo augmentation: the training text of an essay is replaced by its augmented version from
               data/external/17_augmented_train.csv (src/augment.py explains what was changed)
    B          predictability-matched loss weights (src.augment.predictability_weights), computed on the essays of this run
    C          A and B together

Fold mode writes results/17_variants/<variant>/scores_foldKK_seedSS.csv (the same three groups as lopo_fold.py: left_out, other_val,
other_test) and one line in log.csv; the weights are not kept; a finished fold is skipped.
Full mode trains on every train-split essay, keeps the best epoch by val AUC, saves the model to models/distilroberta_<tag>_s<seed>/
(never overwrites) and writes val and test scores to results/17_final/. It does NOT score the held-out prompts or generators:
those are checked once, at the end of Phase 5.
Everything about training (2 epochs, lr 2e-5, 6% warm-up, 512 tokens, fp16, batch 16, AdamW, clip 1.0) is identical to notebook 08.
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

from src.augment import predictability_weights
from src.data import load_splits
from src.evaluate import threshold_for_fpr, wilson_interval

transformers.logging.set_verbosity_error()
MODEL_NAME, MAX_LEN, EPOCHS, LR, BATCH = 'distilroberta-base', 512, 2, 2e-5, 16
TAGS = {'baseline': 'orig', 'A': 'aug', 'B': 'predw', 'C': 'augpredw'}


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    print(f'[{now()}] {msg}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=list(TAGS), required=True)
    ap.add_argument('--fold', type=int, help='left-out prompt index 0-12 (sorted by name); omit with --full')
    ap.add_argument('--full', action='store_true', help='train on the whole training set and save the model')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--smoke', action='store_true', help='tiny run to test the pipeline; writes to /tmp')
    a = ap.parse_args()
    assert a.full != (a.fold is not None), 'give exactly one of --fold K or --full'
    use_aug, use_w = a.variant in ('A', 'C'), a.variant in ('B', 'C')

    if a.full:
        out_dir = Path('/tmp/phase3_smoke') if a.smoke else ROOT / 'results' / '17_final'
        model_dir = Path('/tmp/phase3_smoke/model') if a.smoke else ROOT / 'models' / f'distilroberta_{TAGS[a.variant]}_s{a.seed}'
        done_path = out_dir / f'{TAGS[a.variant]}_s{a.seed}_scores.csv'
        if model_dir.exists() or done_path.exists():
            log(f'{model_dir.name} already exists, skipping (never overwritten)')
            return
    else:
        out_dir = Path('/tmp/phase3_smoke') if a.smoke else ROOT / 'results' / '17_variants' / a.variant
        done_path = out_dir / f'scores_fold{a.fold:02d}_seed{a.seed}.csv'
        if done_path.exists():
            log(f'variant {a.variant} fold {a.fold} seed {a.seed}: {done_path.name} exists, skipping')
            return
    out_dir.mkdir(parents=True, exist_ok=True)

    data = load_splits('train', 'val', 'test')
    gpt2 = pd.read_csv(ROOT / 'results' / '10_gpt2_features.csv', index_col='row_id')
    data = data.join(gpt2[['log_ppl']])
    prompts = sorted(data['prompt_name'].unique())
    assert len(prompts) == 13, prompts
    if a.full:
        prompt = None
        train = data[data['split'] == 'train']
        val_other = data[data['split'] == 'val']                         # epoch selection, as in 08
        left = data.iloc[:0]
        test_other = data[data['split'] == 'test']
    else:
        prompt = prompts[a.fold]
        train = data[(data['split'] == 'train') & (data['prompt_name'] != prompt)]
        val_other = data[(data['split'] == 'val') & (data['prompt_name'] != prompt)]
        test_other = data[(data['split'] == 'test') & (data['prompt_name'] != prompt)]
        left = data[data['prompt_name'] == prompt]
        assert not set(train['prompt_name']) & {prompt} and not set(train.index) & set(left.index)
    epochs = EPOCHS
    if a.smoke:
        train, val_other, test_other = (d.sample(min(len(d), n), random_state=0) for d, n in [(train, 320), (val_other, 160), (test_other, 100)])
        left = left.sample(min(len(left), 100), random_state=0) if len(left) else left
        epochs = 1
    t_start, start_str = time.time(), now()
    log(f'variant {a.variant} | {"full training set" if a.full else f"fold {a.fold}, left-out prompt {prompt!r}"} | seed {a.seed}')
    log(f'train {len(train):,} ({train["label"].mean():.1%} AI) | val {len(val_other):,} | left-out {len(left):,} | test {len(test_other):,}')

    text = train['text']
    if use_aug:                                                          # variant A / C: the augmented training text
        aug = pd.read_csv(ROOT / 'data' / 'external' / '17_augmented_train.csv', index_col='row_id')
        text = aug.loc[train.index, 'text_aug']
        log(f'augmented text: {(aug.loc[train.index, "kind"] != "none").mean():.1%} of the training essays changed')
    weights = np.ones(len(train))
    if use_w:                                                            # variant B / C: predictability-matched loss weights
        weights, _ = predictability_weights(train['log_ppl'].to_numpy(), train['label'].to_numpy(), n_bins=10, max_weight=10.0)
        log(f'weights: human {weights[train["label"].to_numpy() == 0].min():.2f}-{weights[train["label"].to_numpy() == 0].max():.2f}, '
            f'AI {weights[train["label"].to_numpy() == 1].min():.2f}-{weights[train["label"].to_numpy() == 1].max():.2f}')

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    pad = tokenizer.pad_token_id
    ids = lambda texts: tokenizer(list(texts), truncation=True, max_length=MAX_LEN)['input_ids']
    train = train.assign(ids=ids(text), w=weights)
    val_other, test_other = (d.assign(ids=ids(d['text']), w=1.0) for d in (val_other, test_other))
    if len(left):
        left = left.assign(ids=ids(left['text']), w=1.0)
    device = torch.device('cuda')

    def batches(df, batch_size, shuffle=False, seed=0):
        tok, labels, ws = df['ids'].tolist(), df['label'].to_numpy(), df['w'].to_numpy()
        order = np.argsort([len(x) for x in tok], kind='stable')
        chunks = [order[i:i + batch_size] for i in range(0, len(order), batch_size)]
        if shuffle:
            np.random.default_rng(seed).shuffle(chunks)
        for chunk in chunks:
            x = torch.full((len(chunk), max(len(tok[i]) for i in chunk)), pad, dtype=torch.long)
            for r, i in enumerate(chunk):
                x[r, :len(tok[i])] = torch.tensor(tok[i])
            yield x, (x != pad).long(), torch.tensor(labels[chunk], dtype=torch.float32), torch.tensor(ws[chunk], dtype=torch.float32), chunk

    @torch.no_grad()
    def logits_of(model, df, batch_size=64):
        model.eval()
        out = np.empty(len(df), dtype=np.float32)
        with torch.autocast('cuda', dtype=torch.float16):
            for x, mask, _, _, chunk in batches(df, batch_size):
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
        for x, mask, y, w, _ in batches(train, BATCH, shuffle=True, seed=a.seed + epoch):
            with torch.autocast('cuda', dtype=torch.float16):
                logits = model(input_ids=x.to(device), attention_mask=mask.to(device)).logits.squeeze(1)
            per_essay = torch.nn.functional.binary_cross_entropy_with_logits(logits.float(), y.to(device), reduction='none')
            wd = w.to(device)
            loss = (per_essay * wd).sum() / wd.sum()                     # weighted mean; with all weights 1 this is the plain mean of 08
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt); scaler.update(); sched.step()
            losses.append(loss.item())
            del logits, loss, per_essay
        val_auc = roc_auc_score(val_other['label'], logits_of(model, val_other))
        log(f'  epoch {epoch}: train loss {np.mean(losses):.4f} | val AUC {val_auc:.5f} | {(time.time() - t0) / 60:.1f} min | '
            f'peak GPU {torch.cuda.max_memory_allocated() / 1e9:.2f} GB')
        if val_auc > best_auc:
            best_auc, best_epoch = val_auc, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)

    parts = {'other_val': val_other, 'other_test': test_other}
    if len(left):
        parts = {'left_out': left, **parts}
    if a.full:                                                           # full mode: name the groups for what they are; never score held-out text
        parts = {'val': val_other, 'test': test_other}
    rows = []
    for role, d in parts.items():
        rows.append(pd.DataFrame({'row_id': d.index, 'split': d['split'].to_numpy(), 'label': d['label'].to_numpy(),
                                  'prompt_name': d['prompt_name'].to_numpy(), 'role': role, 'logit': logits_of(model, d)}))
    scores = pd.concat(rows, ignore_index=True)
    assert not set(scores['split']) & {'heldout_prompt', 'heldout_generator'}
    tmp = done_path.with_suffix('.tmp')
    scores.to_csv(tmp, index=False)
    if a.full:
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(model_dir)
        tokenizer.save_pretrained(model_dir)
        log(f'saved model to {model_dir}')
    tmp.rename(done_path)

    row = {'variant': a.variant, 'fold': a.fold if not a.full else -1, 'seed': a.seed, 'left_out_prompt': prompt or 'none (full)', 'start': start_str, 'end': now(),
           'minutes': round((time.time() - t_start) / 60, 1), 'best_epoch': best_epoch, 'val_auc': round(best_auc, 5),
           'peak_gpu_gb': round(torch.cuda.max_memory_allocated() / 1e9, 2)}
    if not a.full:
        vh = scores[(scores['role'] == 'other_val') & (scores['label'] == 0)]['logit']
        thr = threshold_for_fpr(vh, 0.01)
        lh = scores[(scores['role'] == 'left_out') & (scores['label'] == 0)]['logit']
        k, n = int((lh >= thr).sum()), len(lh)
        lo, hi = wilson_interval(k, n)
        va = scores[(scores['role'] == 'other_val') & (scores['label'] == 1)]['logit']
        row.update({'threshold_1pct': round(thr, 3), 'humans_n': n, 'humans_flagged': k, 'fpr_pct': round(100 * k / n, 2),
                    'fpr_lo': round(100 * lo, 2), 'fpr_hi': round(100 * hi, 2), 'val_ai_caught_pct': round(100 * float((va >= thr).mean()), 2)})
    log_path = out_dir / 'log.csv'
    pd.DataFrame([row]).to_csv(log_path, mode='a', header=not log_path.exists(), index=False)
    log(f'done: ' + (f'left-out humans flagged {row["humans_flagged"]}/{row["humans_n"]} = {row["fpr_pct"]}%, val AI caught {row["val_ai_caught_pct"]}%, ' if not a.full else '') +
        f'val AUC {best_auc:.5f}, {row["minutes"]} min')
    del model, opt, scaler, best_state
    gc.collect(); torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
