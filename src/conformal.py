"""A common score scale and threshold rules that are judged on topics they were not set on (18_robust_threshold.ipynb).

Common scale: the val-human tail probability (a conformal p-value)
    p(x) = (1 + #{val human essays scoring >= x}) / (1 + #val humans)          computed separately for each trained model
p is small when an essay scores higher than almost all val humans. If a new human essay is exchangeable with the val humans, then
P(p <= a) <= a for every a, so "flag when p <= 0.01" flags at most 1% of such humans, whatever the model. Because p only uses the rank of
a score among that model's own val humans, it does not change under any monotone rescaling of the logits: two seeds whose 1% thresholds are
+4.57 and -0.13 logits both map the same fraction of val humans to p <= 0.01. The guarantee is about the val distribution; for essays on a
NEW topic it fails (that is what the phase measures), and the rules below choose a flag threshold tau on the p scale, "flag if p <= tau".

Rules, given the p-values of the human essays of the topics used to set the threshold (each topic is one left-out prompt, scored by the
model that never saw it) and a target false-flag rate:
    a  pooled val           tau = target                                      (what the project did so far, on the p scale)
    b  pooled LOPO          tau = the target-quantile of all those humans' p-values pooled
    c  worst topic          tau = the smallest per-topic tau (the topic hardest to keep under the target decides)
    d  topic quantile       tau = the 20th percentile of the per-topic taus (80% of topics can be held at the target)
with per-topic tau_t = the target-quantile of topic t's human p-values (the largest tau that keeps that topic at the target).
Evaluation is leave-one-topic-out: set tau from 12 topics, apply it to the 13th, repeat for all 13.
"""
import numpy as np
import pandas as pd

from .evaluate import ClusterSampler

RULES = ('a', 'b', 'c', 'd')


def tail_p(scores, val_human_scores):
    """p(x) = (1 + #{val humans with score >= x}) / (1 + n_val_humans); small = more AI-like than almost every val human."""
    v = np.sort(np.asarray(val_human_scores))
    ge = len(v) - np.searchsorted(v, np.asarray(scores), side='left')       # val humans scoring >= x
    return (1 + ge) / (1 + len(v))


def topic_tau(p_humans, target):
    """The largest tau such that at most `target` of this topic's humans have p <= tau."""
    return float(np.quantile(p_humans, target, method='lower'))


def set_tau(rule, train_p_humans, target):
    """tau for a rule from the human p-values of the training topics (a list of arrays, one per topic)."""
    if rule == 'a':
        return float(target)
    if rule == 'b':
        return float(np.quantile(np.concatenate(train_p_humans), target, method='lower'))
    taus = np.array([topic_tau(p, target) for p in train_p_humans])
    if rule == 'c':
        return float(taus.min())
    if rule == 'd':
        return float(np.quantile(taus, 0.2, method='lower'))
    raise ValueError(rule)


def load_topics(fold_dir, folds, data):
    """The saved score files of a leave-one-prompt-out run -> one dict per left-out topic.

    Each dict: name, val_h (val-human scores of the other prompts: the reference for p), left_h / left_a (scores of the left-out prompt's
    human / AI essays), and the dup_cluster ids of each, for cluster bootstraps.
    """
    topics = []
    for k in folds:
        s = pd.read_csv(f'{fold_dir}/scores_fold{k:02d}_seed42.csv', index_col='row_id')
        vh = s[(s['role'] == 'other_val') & (s['label'] == 0)]
        lh = s[(s['role'] == 'left_out') & (s['label'] == 0)]
        la = s[(s['role'] == 'left_out') & (s['label'] == 1)]
        topics.append(dict(fold=k, name=lh['prompt_name'].iloc[0], val_h=vh['logit'].to_numpy(), val_c=data.loc[vh.index, 'dup_cluster'].to_numpy(),
                           left_h=lh['logit'].to_numpy(), left_hc=data.loc[lh.index, 'dup_cluster'].to_numpy(),
                           left_a=la['logit'].to_numpy(), left_ac=data.loc[la.index, 'dup_cluster'].to_numpy()))
    return topics


def _p_arrays(topics, resample=None):
    """p-values of each topic's left-out humans and AI essays; with `resample` (a numpy Generator) every part is cluster-resampled."""
    out = []
    for t in topics:
        if resample is None:
            vh, lh, la = t['val_h'], t['left_h'], t['left_a']
        else:
            vh = t['val_h'][ClusterSampler(t['val_c']).draw(resample)]
            lh = t['left_h'][ClusterSampler(t['left_hc']).draw(resample)]
            la = t['left_a'][ClusterSampler(t['left_ac']).draw(resample)]
        out.append((tail_p(lh, vh), tail_p(la, vh)))
    return out


def loto(p_arrays, rule, target, band_target=None):
    """Leave-one-topic-out: per topic the false-flag rate, AI caught, and (if band_target) the cannot-tell band shares.

    Returns a DataFrame with one row per left-out topic. A topic is 'over target' when its false-flag rate is above `target`.
    The flag boundary is tau (from `target`); the band is tau < p <= tau_b, tau_b from the same rule at `band_target`.
    """
    rows = []
    ph_all = [p[0] for p in p_arrays]
    for u, (ph, pa) in enumerate(p_arrays):
        train = [x for i, x in enumerate(ph_all) if i != u]
        tau = set_tau(rule, train, target)
        row = {'tau': tau, 'fpr': float((ph <= tau).mean()), 'ai_caught': float((pa <= tau).mean())}
        if band_target is not None:
            tau_b = max(set_tau(rule, train, band_target), tau)
            row.update({'tau_band': tau_b, 'human_in_band': float(((ph > tau) & (ph <= tau_b)).mean()), 'ai_in_band': float(((pa > tau) & (pa <= tau_b)).mean()),
                        'human_not_flagged': float((ph > tau_b).mean()), 'ai_missed': float((pa > tau_b).mean())})
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(per_topic, target):
    """The four statistics of the pre-declared rule comparison for one (rule, target)."""
    return {'mean_fpr': 100 * per_topic['fpr'].mean(), 'worst_fpr': 100 * per_topic['fpr'].max(),
            'share_over_target': 100 * float((per_topic['fpr'] > target).mean()), 'mean_ai_caught': 100 * per_topic['ai_caught'].mean()}


def compare_rules(topics, targets=(0.01, 0.005), rules=RULES, n_boot=1000, seed=42):
    """Point estimates and 95% bootstrap intervals of the four statistics, for every (rule, target).

    The bootstrap redraws, inside every fold, the val humans (so the p-values move), the left-out humans and the left-out AI essays (whole
    dup_cluster groups), then repeats the whole leave-one-topic-out procedure.
    """
    point_p = _p_arrays(topics)
    rng = np.random.default_rng(seed)
    draws = {(r, t): [] for r in rules for t in targets}
    for _ in range(n_boot):
        pb = _p_arrays(topics, rng)
        for r in rules:
            for t in targets:
                draws[(r, t)].append(summarise(loto(pb, r, t), t))
    rows = []
    for r in rules:
        for t in targets:
            pt = summarise(loto(point_p, r, t), t)
            dd = pd.DataFrame(draws[(r, t)])
            row = {'rule': r, 'target': t}
            for k, v in pt.items():
                lo, hi = np.percentile(dd[k], [2.5, 97.5])
                row.update({k: v, k + '_lo': lo, k + '_hi': hi})
            rows.append(row)
    return pd.DataFrame(rows)


def band_report(topics, rule, flag_target, band_target, n_boot=1000, seed=42):
    """The cannot-tell band for one rule: shares of human and AI essays in each of the three zones, leave-one-topic-out, with intervals."""
    def stat(per):
        return {'human flagged %': 100 * per['fpr'].mean(), 'human in band %': 100 * per['human_in_band'].mean(), 'human not flagged %': 100 * per['human_not_flagged'].mean(),
                'AI flagged %': 100 * per['ai_caught'].mean(), 'AI in band %': 100 * per['ai_in_band'].mean(), 'AI missed %': 100 * per['ai_missed'].mean(),
                'topics over target (flagged)': 100 * float((per['fpr'] > flag_target).mean())}
    point = stat(loto(_p_arrays(topics), rule, flag_target, band_target))
    rng = np.random.default_rng(seed)
    dd = pd.DataFrame([stat(loto(_p_arrays(topics, rng), rule, flag_target, band_target)) for _ in range(n_boot)])
    return pd.DataFrame({'estimate': point, 'lo': dd.quantile(0.025), 'hi': dd.quantile(0.975)})
