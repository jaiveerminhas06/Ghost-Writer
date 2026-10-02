"""Shared data loading for every notebook from 03_split onward.

The essays live once, in data/processed/train_deduped.csv. 03_split.ipynb writes
only a small data/processed/splits.csv (row_id -> split), and this module joins
the two, so every later notebook sees exactly the same text and the same splits.
"""
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

SPLITS = ["train", "val", "test", "heldout_prompt", "heldout_generator"]


def load_deduped():
    """Load the deduped essays with whitespace stripped.

    row_id is the essay's row number in train_deduped.csv; splits.csv refers to it.
    Leading/trailing whitespace is stripped because it leaks the label: several
    AI sources start every essay with a space, while no human essay does
    (see 03_split.ipynb).
    """
    df = pd.read_csv(PROCESSED / "train_deduped.csv")
    df.index.name = "row_id"
    df["text"] = df["text"].str.strip()
    return df


def load_splits(*splits):
    """Return the essays with a `split` column, optionally only the named splits.

    Rows dropped in 03_split (they have no entry in splits.csv) are excluded.
    Example: train = load_splits("train"); full = load_splits()
    """
    unknown = set(splits) - set(SPLITS)
    if unknown:
        raise ValueError(f"unknown split(s) {unknown}; choose from {SPLITS}")
    df = load_deduped()
    assignment = pd.read_csv(PROCESSED / "splits.csv", index_col="row_id")
    df = df.join(assignment, how="inner")
    if splits:
        df = df[df["split"].isin(splits)]
    return df
