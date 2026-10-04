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
