"""Prints the fold (0-12) whose left-out false-flag rate is closest to the median of the 13 seed-42 folds (for the seed-noise check)."""
import sys
from pathlib import Path

import pandas as pd

log = pd.read_csv(Path(__file__).resolve().parent.parent / 'results' / '16b_lopo' / 'log.csv')
log = log[log['seed'] == 42].drop_duplicates('fold')
if len(log) < 13:
    sys.exit(f'only {len(log)} of 13 folds are done')
med = log['fpr_pct'].median()
print(int(log.loc[(log['fpr_pct'] - med).abs().idxmin(), 'fold']))
