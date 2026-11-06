"""Shared scoring, so every model (Week 1 baseline onward) is reported the same way.

Same logic as the evaluate() defined inline in 04_baseline.ipynb.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

COLUMNS = ['test_acc', 'test_precision', 'test_recall', 'test_f1', 'test_auc',
           'heldout_prompt_f1', 'heldout_prompt_auc', 'heldout_gen_detection', 'heldout_gen_auc']


def metrics(y, score, threshold):
    pred = (np.asarray(score) >= threshold).astype(int)
    return {'acc': accuracy_score(y, pred),
            'precision': precision_score(y, pred, zero_division=0),
            'recall': recall_score(y, pred),
            'f1': f1_score(y, pred),
            'auc': roc_auc_score(y, score)}


def evaluate(score_fn, threshold, name, test, heldout_prompt, heldout_generator):
    """Score a fitted model on the three final sets and return one results row.

    score_fn(df) -> 1-D array, higher = more likely AI; `threshold` turns scores into labels.
    The held-out generator slice is AI-only, so it gets a detection rate at `threshold`
    plus an AUC computed against the human essays of `test`.
    """
    row = {}
    for split_name, d in [('test', test), ('heldout_prompt', heldout_prompt)]:
        row.update({f'{split_name}_{k}': v for k, v in metrics(d['label'], score_fn(d), threshold).items()})
    gen_score = np.asarray(score_fn(heldout_generator))
    test_humans = test[test['label'] == 0]
    paired_y = np.r_[np.zeros(len(test_humans)), np.ones(len(heldout_generator))]
    paired_score = np.r_[score_fn(test_humans), gen_score]
    row['heldout_gen_detection'] = (gen_score >= threshold).mean()
    row['heldout_gen_auc'] = roc_auc_score(paired_y, paired_score)
    return pd.Series(row, name=name)[COLUMNS]


def evaluate_on_topic(score_fn, threshold, name, test, heldout_prompt, heldout_generator):
    """Same as evaluate(), but only on essays flagged on-topic (06_topic_check.ipynb).

    Off-topic AI essays can be caught by their subject alone, so this is the fairer score:
    human vs AI essays written about the same prompt.
    """
    keep = lambda d: d[d['on_topic']]
    return evaluate(score_fn, threshold, name, keep(test), keep(heldout_prompt), keep(heldout_generator))


# ---------------------------------------------------------------------------------------------------------------
# Error bars (added for 15_uncertainty.ipynb). Nothing above this line changed.
# ---------------------------------------------------------------------------------------------------------------

def wilson_interval(k, n, z=1.96):
    """95% Wilson score interval for a rate k/n, returned as (low, high) fractions in [0, 1].

    Why not the textbook "p +/- 1.96 * sqrt(p(1-p)/n)"? That formula puts the uncertainty around the observed rate,
    so for a small rate it breaks: with 0 flagged out of 300 it gives a zero-width interval ("exactly 0%, no
    uncertainty"), and with 2 of 300 it can dip below 0. The Wilson interval instead asks "which true rates would
    produce this count without being surprising?". It never leaves [0, 1], is not zero-width at k = 0, and is
    accurate down to a handful of events, which is where most of this project's rates (false flags) live.
    """
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def percent_with_interval(k, n, digits=2):
    """'2.31% [1.8, 2.9]' for k flagged out of n, in percent (Wilson)."""
    lo, hi = wilson_interval(k, n)
    return f"{100 * k / n:.{digits}f}% [{100 * lo:.{digits - 1}f}, {100 * hi:.{digits - 1}f}]"


class ClusterSampler:
    """Draws bootstrap resamples that keep near-duplicate essays together (groups = dup_cluster ids).

    Near-duplicate essays are not independent observations, so resampling single essays would make an interval too
    narrow. Instead we draw whole clusters with replacement and take all their essays. Most clusters hold one essay,
    so this changes little, but it is the honest way. The grouping is computed once so a draw is fast.
    """

    def __init__(self, groups):
        codes, uniques = pd.factorize(np.asarray(groups))
        self.order = np.argsort(codes, kind='stable')                       # row positions sorted by cluster
        self.counts = np.bincount(codes, minlength=len(uniques))
        self.starts = np.r_[0, np.cumsum(self.counts)[:-1]]
        self.n_groups = len(uniques)

    def draw(self, rng):
        picked = rng.integers(0, self.n_groups, self.n_groups)
        lens = self.counts[picked]
        # for each picked cluster, the run of positions starts[c] ... starts[c] + len - 1 in the sorted order
        offsets = np.repeat(self.starts[picked] - (np.cumsum(lens) - lens), lens) + np.arange(lens.sum())
        return self.order[offsets]


def cluster_resample(groups, rng):
    """One-off cluster resample (see ClusterSampler, which is faster when you draw many times)."""
    return ClusterSampler(groups).draw(rng)


def bootstrap_interval(stat_fn, n_rows, groups=None, n_boot=1000, seed=42):
    """95% percentile bootstrap interval of stat_fn(rows) over `n_boot` resamples of the row positions 0..n_rows-1.

    stat_fn gets an integer array of row positions (with repeats) and returns a number (or nan, which is skipped,
    e.g. an AUC on a resample that happened to contain one class only). Returns (point, low, high); the point
    estimate is stat_fn on all rows. groups = per-row cluster ids for a cluster bootstrap (see cluster_resample).
    """
    rng = np.random.default_rng(seed)
    sampler = ClusterSampler(groups) if groups is not None else None
    point = stat_fn(np.arange(n_rows))
    draws = []
    for _ in range(n_boot):
        rows = sampler.draw(rng) if sampler is not None else rng.integers(0, n_rows, n_rows)
        draws.append(stat_fn(rows))
    draws = np.array(draws, dtype=float)
    draws = draws[~np.isnan(draws)]
    return point, *np.percentile(draws, [2.5, 97.5])


def auc_with_interval(y, score, groups=None, n_boot=1000, seed=42):
    """(AUC, low, high); the bootstrap redraws essays, so both classes stay in each resample on average."""
    y, score = np.asarray(y), np.asarray(score)

    def stat(rows):
        yy = y[rows]
        return roc_auc_score(yy, score[rows]) if 0 < yy.sum() < len(yy) else np.nan
    return bootstrap_interval(stat, len(y), groups, n_boot, seed)


def rate_with_bootstrap(flagged, groups=None, n_boot=1000, seed=42):
    """(rate, low, high) of a boolean array, by bootstrap. Use for false-flag rate (humans only) or detection rate (AI only)."""
    flagged = np.asarray(flagged, dtype=float)
    return bootstrap_interval(lambda rows: flagged[rows].mean() if len(rows) else np.nan, len(flagged), groups, n_boot, seed)


def threshold_for_fpr(human_scores, target):
    """The score such that `target` of these human essays score at or above it (09_threshold.ipynb uses the same quantile)."""
    return float(np.quantile(np.asarray(human_scores), 1 - target))
