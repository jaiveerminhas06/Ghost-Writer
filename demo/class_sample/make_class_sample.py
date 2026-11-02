"""Builds the demo classes for the "Check a class" page: 30 essays each, with known authors, picked without looking at the detector.

Run from the repo root:   python demo/class_sample/make_class_sample.py            (builds every topic)
                          python demo/class_sample/make_class_sample.py summer_projects
Each topic gets its own folder with essay_NN-style files and a labels.json. The choice is random with a fixed seed, so running it
again gives the same classes. The two topics are built by exactly the same function: only the prompt differs.

How the 30 are chosen (and why):
  1. Only essays the model never trained on or tuned on: the split is "heldout_prompt" (a whole topic kept out of training and
     validation, see notebook 03). There are two such topics, and each has its own demo class. A class writes on ONE topic, and an
     unseen topic is the situation the page's false-flag figures (2.3% / 3.9%) describe.
  2. Student essays: every human essay on that topic. AI essays: only those that are really about that topic (on_topic, notebook 06;
     half the dataset's AI essays are off-topic for their label), and not from the `train_essays` source, which holds the dataset's
     known mislabelled rows (notebook 04).
  3. The mix follows the real ratio in the whole held-out-prompt split (62.6% student, 37.4% AI): 30 x 0.626 = 18.8, so 19 student
     and 11 AI, for both topics.
  4. Random draw (seed 42) inside each group. No filter on length or on the detector's score, and the score is never looked at.
  5. The order is shuffled (same seed) and the files get neutral names (the topic and a number), so the file names and the order say
     nothing about the author.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from src.data import load_splits  # noqa: E402

SEED, SIZE, SPLIT = 42, 30, "heldout_prompt"
TOPICS = {   # folder name -> (the dataset's prompt_name, the prefix of its file names)
    "electoral_college": ("Does the electoral college work?", "electoral"),
    "summer_projects": ("Summer projects", "summer"),
}


def build(slug, split=None):
    """Choose the class for one topic. Returns (student share of the split, chosen rows with their text and the file names)."""
    prompt, prefix = TOPICS[slug]
    split = load_splits(SPLIT) if split is None else split
    ratio = (split["label"] == 0).mean()                         # the share of student essays in the whole held-out-prompt split
    n_human = round(SIZE * ratio)
    n_ai = SIZE - n_human
    topic = split[split["prompt_name"] == prompt]
    humans = topic[topic["label"] == 0]
    ai = topic[(topic["label"] == 1) & topic["on_topic"] & (topic["source"] != "train_essays")]
    rng = np.random.default_rng(SEED)
    pick = lambda frame, n: frame.loc[rng.choice(frame.index.to_numpy(), size=n, replace=False)]
    chosen = pd.concat([pick(humans, n_human), pick(ai, n_ai)])
    chosen = chosen.loc[rng.permutation(chosen.index.to_numpy())]
    chosen = chosen.assign(file=[f"{prefix}_{k:02d}.txt" for k in range(1, len(chosen) + 1)])
    return float(ratio), chosen, (len(humans), len(ai))


def write(slug, split=None):
    prompt, _ = TOPICS[slug]
    ratio, chosen, (n_candidates_h, n_candidates_ai) = build(slug, split)
    out = HERE / slug
    out.mkdir(exist_ok=True)
    labels = []
    for row_id, row in chosen.iterrows():
        (out / row["file"]).write_text(row["text"])
        labels.append({"file": row["file"], "label": "human" if row["label"] == 0 else "ai", "row_id": int(row_id), "split": row["split"],
                       "source": row["source"], "prompt": row["prompt_name"], "words": int(row["n_words"])})
    (out / "labels.json").write_text(json.dumps(
        {"seed": SEED, "split": SPLIT, "prompt": prompt, "student_share_in_split": round(ratio, 4), "essays": labels}, indent=1))
    n_h = sum(e["label"] == "human" for e in labels)
    print(f"{slug}: {n_h} student + {len(labels) - n_h} AI essays from {n_candidates_h} student / {n_candidates_ai} AI candidates on '{prompt}' ({SPLIT})")


if __name__ == "__main__":
    split = load_splits(SPLIT)
    for slug in (sys.argv[1:] or TOPICS):
        write(slug, split)
