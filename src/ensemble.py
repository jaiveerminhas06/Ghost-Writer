"""An ensemble on the p scale, and the stability measures of 19_ensemble_stability.ipynb (declared in that notebook, sections 2-4).

Per-seed p: p_s(x) = (1 + #{reference humans scoring >= x}) / (1 + n), the val-human tail probability of notebook 18 (small = AI-like).
Ensemble: e(x) = mean or median of the seeds' p-values; it is not a p-value, so it is re-calibrated the same way against the reference humans'
own e-values: p_ens(x) = (1 + #{reference humans with e <= x's e}) / (1 + n). A reference human's own p is computed leave-one-out (it is not
allowed to count itself), so reference essays and new essays are treated alike; this matters at the tail, where tau is only a few grid steps wide.
"""
import numpy as np
import pandas as pd

from .conformal import tail_p
from .evaluate import ClusterSampler, wilson_interval


def combine(P, how):
    """P: (n essays, n seeds) of p-values -> one score per essay (smaller = more AI-like)."""
    return np.median(P, axis=1) if how == 'median' else np.asarray(P).mean(axis=1)


class PEnsemble:
    """Calibrated on the reference humans' scores (an (n_ref, n_seeds) array, one column per seed). Use p_seeds / p_ens on any essays."""

    def __init__(self, ref_scores, how='mean'):
        self.how = how
        self.ref = np.sort(np.asarray(ref_scores, dtype=float), axis=0)
        self.n = len(self.ref)
        raw = np.asarray(ref_scores, dtype=float)
        # leave-one-out p of each reference human, per seed: ge counts itself once, so remove it: (1 + (ge - 1)) / n = ge / n
        ge = np.stack([self.n - np.searchsorted(self.ref[:, s], raw[:, s], side='left') for s in range(raw.shape[1])], axis=1)
        self.e_ref = np.sort(combine(ge / self.n, how))

    def p_seeds(self, X):
        X = np.asarray(X, dtype=float)
        return np.stack([tail_p(X[:, s], self.ref[:, s]) for s in range(X.shape[1])], axis=1)

    def e(self, X):
        return combine(self.p_seeds(X), self.how)

    def p_ens(self, X):
        return (1 + np.searchsorted(self.e_ref, self.e(X), side='right')) / (1 + self.n)


def wilson_pct(k, n):
    lo, hi = wilson_interval(int(k), int(n))
    return f'{100 * k / n:.2f} [{100 * lo:.2f}, {100 * hi:.2f}]'


def inflation_fold(val_h, left_h, taus=(0.01, 0.005), how='mean', val_clusters=None, left_clusters=None, n_boot=1000, seed=42):
    """False-flag rates of the left-out humans at p <= tau, per seed and for the ensemble, and their paired difference.

    val_h: (n_val, S) scores of the reference (other-prompt val) humans, one column per seed; left_h: (n_left, S) scores of the left-out humans.
    Returns one row per tau: single-seed rates (a list), their mean, the ensemble rate, and ensemble minus the mean of the singles with a 95%
    cluster-bootstrap interval that redraws the reference humans (both the seeds' and the ensemble's calibration move together) and the left-out
    humans.
    """
    val_h, left_h = np.asarray(val_h, float), np.asarray(left_h, float)
    S = val_h.shape[1]

    def rates(vh, lh):
        ens = PEnsemble(vh, how)
        ps, pe = ens.p_seeds(lh), ens.p_ens(lh)
        return {tau: (np.array([(ps[:, s] <= tau).mean() for s in range(S)]), float((pe <= tau).mean())) for tau in taus}
    point = rates(val_h, left_h)
    rng = np.random.default_rng(seed)
    vs = ClusterSampler(val_clusters if val_clusters is not None else np.arange(len(val_h)))
    ls = ClusterSampler(left_clusters if left_clusters is not None else np.arange(len(left_h)))
    diffs = {tau: [] for tau in taus}
    for _ in range(n_boot):
        r = rates(val_h[vs.draw(rng)], left_h[ls.draw(rng)])
        for tau in taus:
            diffs[tau].append(r[tau][1] - r[tau][0].mean())
    rows = []
    for tau in taus:
        singles, ens_rate = point[tau]
        lo, hi = np.percentile(diffs[tau], [2.5, 97.5])
        k_s = [int(round(x * len(left_h))) for x in singles]
        rows.append({'tau': tau, 'single seeds %': [round(100 * x, 2) for x in singles], 'mean of singles %': 100 * singles.mean(),
                     'ensemble %': 100 * ens_rate, 'inflation, singles (x nominal)': singles.mean() / tau, 'inflation, ensemble (x nominal)': ens_rate / tau,
                     'ensemble minus singles (pts)': 100 * (ens_rate - singles.mean()), 'lo': 100 * lo, 'hi': 100 * hi,
                     'k singles': k_s, 'k ensemble': int(round(ens_rate * len(left_h))), 'n': len(left_h)})
    return pd.DataFrame(rows)


def agreement(flags):
    """flags: (n essays, k models) booleans. Among essays flagged by at least one model, the share flagged by all; mean pairwise Cohen's kappa."""
    f = np.asarray(flags, dtype=bool)
    any_, all_ = f.any(axis=1), f.all(axis=1)
    kappas = []
    for i in range(f.shape[1]):
        for j in range(i + 1, f.shape[1]):
            a, b = f[:, i], f[:, j]
            po = (a == b).mean()
            pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
            kappas.append((po - pe) / (1 - pe) if pe < 1 else np.nan)
    return {'flagged by at least one': int(any_.sum()), 'flagged by all': int(all_.sum()), 'share flagged by all %': 100 * all_.sum() / max(1, any_.sum()),
            'mean pairwise kappa': float(np.nanmean(kappas))}


def flips(p_orig, p_typos, tau, factor=3.0):
    """Verdict flips under typos. p_orig: (n,) p of the essays; p_typos: list of (n,) arrays (one per typo copy), same reference.

    Near the threshold: tau/factor <= p_orig <= tau*factor. Returns per-essay flip counts across copies, the near-threshold mask, and the
    rates: flip rate among near-threshold essays (averaged over copies) and among all essays.
    """
    p_orig = np.asarray(p_orig)
    base = p_orig <= tau
    flip = np.mean([(np.asarray(pt) <= tau) != base for pt in p_typos], axis=0)      # per essay, share of copies whose verdict changed
    near = (p_orig >= tau / factor) & (p_orig <= tau * factor)
    return flip, near
