"""The pre-registered paired comparison of a training variant against the original recipe (17_augment.ipynb, section 2).

For each leave-one-prompt-out fold both models scored the same essays (results/16b_lopo = original recipe, results/17_variants/<V> = variant).
Per fold, each model's threshold is the score that flags 1% of the val humans of the other 12 prompts. Then:

  PRIMARY    mean over the folds of the left-out-prompt human false-flag rate, variant minus baseline (percentage points)
  secondary  the worst prompt's rate; the rate among the most predictable quarter of humans (GPT-2 log-perplexity below CUTOFF)
  guardrail  mean over the folds of val AI caught at the 1% threshold, variant minus baseline (must not fall below -0.5 points)
  WINS       the primary 95% interval lies below zero AND the guardrail holds

Intervals: paired bootstrap, 1,000 resamples, seed 42. In each fold one resample of the val humans gives BOTH models' thresholds, and one
resample of the left-out humans (whole dup_cluster groups) is scored by BOTH models, so the noise in the thresholds is inside the interval.
"""
import numpy as np
import pandas as pd

from .evaluate import ClusterSampler, threshold_for_fpr, wilson_interval

CUTOFF = 3.0473            # 25th percentile of the HUMAN TRAIN essays' GPT-2 log-perplexity (17_augment.ipynb, section 4)
GUARDRAIL = -0.5           # points of val AI caught


def _fold_arrays(path):
    s = pd.read_csv(path, index_col='row_id').sort_index()
    vh = s[(s['role'] == 'other_val') & (s['label'] == 0)]
    va = s[(s['role'] == 'other_val') & (s['label'] == 1)]
    lh = s[(s['role'] == 'left_out') & (s['label'] == 0)]
    return vh['logit'], va['logit'], lh['logit']


def load_pair(variant, fold, base_dir, var_dir):
    b = _fold_arrays(f'{base_dir}/scores_fold{fold:02d}_seed42.csv')
    v = _fold_arrays(f'{var_dir}/{variant}/scores_fold{fold:02d}_seed42.csv')
    for x, y in zip(b, v):
        assert x.index.equals(y.index), 'baseline and variant scored different essays'
    return b, v


def analyse(variant, folds, data, log_ppl, base_dir='../results/16b_lopo', var_dir='../results/17_variants', n_boot=1000, seed=42):
    """data: the full essay table (needs prompt_name and dup_cluster); log_ppl: Series of GPT-2 log-perplexity by row_id."""
    pairs = {f: load_pair(variant, f, base_dir, var_dir) for f in folds}
    prompts = {f: data.loc[pairs[f][0][2].index[0], 'prompt_name'] for f in folds}
    dup = data['dup_cluster']
    rows, pm = [], []
    for f in folds:
        (bvh, bva, blh), (vvh, vva, vlh) = pairs[f]
        tb, tv = threshold_for_fpr(bvh, 0.01), threshold_for_fpr(vvh, 0.01)
        kb, kv = int((blh >= tb).sum()), int((vlh >= tv).sum())
        n = len(blh)
        lb, ub = wilson_interval(kb, n)
        lv, uv = wilson_interval(kv, n)
        rows.append({'fold': f, 'prompt': prompts[f], 'n humans': n, 'baseline flagged': kb, 'variant flagged': kv,
                     'baseline %': 100 * kb / n, 'baseline Wilson': f'[{100 * lb:.2f}, {100 * ub:.2f}]',
                     'variant %': 100 * kv / n, 'variant Wilson': f'[{100 * lv:.2f}, {100 * uv:.2f}]', 'difference (pts)': 100 * (kv - kb) / n,
                     'val AI caught, baseline %': 100 * float((bva >= tb).mean()), 'val AI caught, variant %': 100 * float((vva >= tv).mean())})
        m = (log_ppl.loc[blh.index] < CUTOFF).to_numpy()
        pm.append((int(((blh.to_numpy() >= tb) & m).sum()), int(((vlh.to_numpy() >= tv) & m).sum()), int(m.sum())))
    per = pd.DataFrame(rows).set_index('prompt')
    pm = np.array(pm).sum(axis=0)

    rng = np.random.default_rng(seed)
    samp = {f: dict(val=ClusterSampler(dup.loc[pairs[f][0][0].index]), left=ClusterSampler(dup.loc[pairs[f][0][2].index]),
                    vai=ClusterSampler(dup.loc[pairs[f][0][1].index]), pred=(log_ppl.loc[pairs[f][0][2].index].to_numpy() < CUTOFF)) for f in folds}
    arr = {f: [x.to_numpy() for x in pairs[f][0]] + [x.to_numpy() for x in pairs[f][1]] for f in folds}    # bvh bva blh vvh vva vlh
    draws = {k: [] for k in ('primary', 'worst_diff', 'pred_diff', 'guard')}
    for _ in range(n_boot):
        rb, rv, g, pk = [], [], [], [0, 0, 0]
        for f in folds:
            bvh, bva, blh, vvh, vva, vlh = arr[f]
            vr, lr, ar = samp[f]['val'].draw(rng), samp[f]['left'].draw(rng), samp[f]['vai'].draw(rng)
            tb, tv = np.quantile(bvh[vr], 0.99), np.quantile(vvh[vr], 0.99)
            fb, fv = blh[lr] >= tb, vlh[lr] >= tv
            rb.append(fb.mean()); rv.append(fv.mean())
            g.append((vva[ar] >= tv).mean() - (bva[ar] >= tb).mean())
            m = samp[f]['pred'][lr]
            pk[0] += fb[m].sum(); pk[1] += fv[m].sum(); pk[2] += m.sum()
        rb, rv = np.array(rb), np.array(rv)
        draws['primary'].append(100 * (rv - rb).mean())
        draws['guard'].append(100 * np.mean(g))
        draws['worst_diff'].append(100 * (rv.max() - rb.max()))
        draws['pred_diff'].append(100 * (pk[1] - pk[0]) / pk[2])
    ci = lambda k: tuple(np.percentile(draws[k], [2.5, 97.5]))
    base_rate, var_rate = per['baseline flagged'] / per['n humans'], per['variant flagged'] / per['n humans']
    out = {'variant': variant, 'folds': len(folds),
           'primary': (100 * (var_rate - base_rate).mean(), *ci('primary')),
           'worst': (100 * base_rate.max(), 100 * var_rate.max(), 100 * (var_rate.max() - base_rate.max()), *ci('worst_diff')),
           'predictable quarter': (100 * pm[0] / pm[2], 100 * pm[1] / pm[2], 100 * (pm[1] - pm[0]) / pm[2], *ci('pred_diff'), int(pm[2])),
           'guardrail': (float(per['val AI caught, variant %'].mean() - per['val AI caught, baseline %'].mean()), *ci('guard'))}
    out['guardrail_ok'] = out['guardrail'][0] >= GUARDRAIL
    out['wins'] = bool(out['primary'][2] < 0 and out['guardrail_ok'])
    return per, out


def report(variant, folds, data, log_ppl, **kw):
    per, o = analyse(variant, folds, data, log_ppl, **kw)
    print(f"=== VARIANT {variant} against the original recipe, {o['folds']} folds, seed 42 ===")
    print(per[['n humans', 'baseline flagged', 'baseline %', 'baseline Wilson', 'variant flagged', 'variant %', 'variant Wilson', 'difference (pts)']].round(2).to_string())
    p, w, q, g = o['primary'], o['worst'], o['predictable quarter'], o['guardrail']
    print(f"\nPRIMARY   mean false-flag rate over the {o['folds']} prompts, variant minus baseline: {p[0]:+.3f} points  95% [{p[1]:+.3f}, {p[2]:+.3f}]")
    print(f"secondary worst-prompt rate: baseline {w[0]:.2f}% -> variant {w[1]:.2f}%  (difference {w[2]:+.2f} [{w[3]:+.2f}, {w[4]:+.2f}])")
    print(f"secondary most predictable quarter of humans (log-ppl < {CUTOFF}): baseline {q[0]:.2f}% -> variant {q[1]:.2f}%  (difference {q[2]:+.2f} [{q[3]:+.2f}, {q[4]:+.2f}], {q[5]} essays)")
    print(f"GUARDRAIL val AI caught at the 1% threshold, variant minus baseline (mean over folds): {g[0]:+.2f} points  95% [{g[1]:+.2f}, {g[2]:+.2f}]  -> {'holds' if o['guardrail_ok'] else 'FAILS'} (limit {GUARDRAIL})")
    print(f"DECISION  primary interval excludes zero on the negative side: {p[2] < 0} | guardrail holds: {o['guardrail_ok']}  =>  {'WINS' if o['wins'] else 'does not win'}")
    return per, o
