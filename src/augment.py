"""Training-time changes for Phase 3 (17_augment.ipynb). Only TRAIN essays are ever touched; val/test/held-out text never is.

Variant A, spelling/typo augmentation (build_augmented_train)
    Notebook 14 found that the detector uses misspellings as evidence for "human" (flagged students have almost none). So in half of
    the human training essays the spelling is repaired (src/spelling.py), and in half of the AI training essays typos are injected
    (src.paraphraser.inject_typos) at a rate drawn from the real distribution of human misspelling rates. Afterwards, misspellings no
    longer tell the two classes apart. The essays are changed in place, so the training set keeps its size and the training time.

Variant B, predictability-matched weights (predictability_weights)
    The other finding of 16b: flagged students write more *predictable* text (low GPT-2 perplexity). AI essays are predictable too, so
    perplexity is a shortcut. Each training essay gets a loss weight such that, within every predictability bin, human and AI essays carry
    the same total weight, so predictability alone stops being a useful cue.
"""
import numpy as np

from .paraphraser import inject_typos


def _augment_one(args):
    row_id, text, label, rate_pool, p, seed, corrector = args
    rng = np.random.default_rng([seed, int(row_id)])
    if rng.random() >= p:
        return row_id, 'none', 0, text
    if label == 0:                                              # a human essay: repair its spelling
        new, n, _ = corrector.correct_text(text)
        return row_id, 'spell_fixed', n, new
    rate = float(rng.choice(rate_pool))                         # an AI essay: add typos at a human-like rate
    new = inject_typos(text, rate, seed=int(rng.integers(0, 2**31 - 1))) if rate > 0 else text
    return row_id, 'typos', int(round(rate * max(1, len(text.split())))), new


def build_augmented_train(train, corrector, human_misspell_rates, share=0.5, rate_factor=1.0, seed=42, workers=10):
    """Returns a DataFrame indexed by row_id with columns kind ('none' | 'spell_fixed' | 'typos'), n_changed, text_aug.

    train: DataFrame with text and label. human_misspell_rates: array of per-essay misspelling rates (fractions) of the human training
    essays; each augmented AI essay draws its typo rate from it (times rate_factor, which converts "share of tokens missing from the
    vocabulary" into "share of words edited", because some edits make another real word).
    Every essay's randomness comes from (seed, row_id), so the result does not depend on the order or on the fold.
    """
    import multiprocessing as mp
    pool_rates = np.asarray(human_misspell_rates) * rate_factor
    jobs = [(i, t, l, pool_rates, share, seed, corrector) for i, t, l in zip(train.index, train['text'], train['label'])]
    ctx = mp.get_context('fork')                                # the corrector (big) is shared with the workers, not copied
    with ctx.Pool(workers) as pool:
        out = pool.map(_augment_one, jobs, chunksize=200)
    import pandas as pd
    return pd.DataFrame(out, columns=['row_id', 'kind', 'n_changed', 'text_aug']).set_index('row_id')


def predictability_weights(log_ppl, label, n_bins=10, max_weight=10.0):
    """Per-essay loss weights that equalise the human and AI distributions over predictability bins.

    Bins are quantiles of the given log-perplexities. In bin b with n_h human and n_a AI essays, and pooled share p_b, the ideal weights
    are N_h*p_b/n_h for humans and N_a*p_b/n_a for AI, which give both classes exactly the pooled bin distribution while keeping each
    class's total weight. Those can be extreme where one class is nearly absent (7 humans in the most predictable decile), so weights
    are clipped to [1/max_weight, max_weight] and each class is rescaled to keep its total weight (mean weight 1 per class).
    Returns (weights, bin index per essay).
    """
    log_ppl, label = np.asarray(log_ppl, dtype=float), np.asarray(label)
    edges = np.quantile(log_ppl, np.linspace(0, 1, n_bins + 1)[1:-1])
    b = np.digitize(log_ppl, edges)
    w = np.ones(len(label))
    for cls in (0, 1):
        m = label == cls
        N = m.sum()
        for k in range(n_bins):
            n_k = (m & (b == k)).sum()
            p_k = (b == k).mean()
            if n_k:
                w[m & (b == k)] = N * p_k / n_k
        w[m] = np.clip(w[m], 1 / max_weight, max_weight)
        w[m] *= N / w[m].sum()
    return w, b


def bin_distribution_gap(w, b, label, n_bins=10):
    """Total-variation distance between the human and AI distributions over the bins (0 = identical, 1 = disjoint), weighted by w."""
    d = {}
    for cls in (0, 1):
        m = np.asarray(label) == cls
        d[cls] = np.bincount(b[m], weights=w[m], minlength=n_bins) / w[m].sum()
    return 0.5 * np.abs(d[0] - d[1]).sum()
