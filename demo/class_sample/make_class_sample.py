"""Builds the demo class for the "Check a class" page: 30 essays with known authors, picked without looking at the detector.

Run from the repo root:   python demo/class_sample/make_class_sample.py
It writes essay_01.txt ... essay_30.txt and labels.json next to this file. The choice is random with a fixed seed, so running it
again gives the same class.

How the 30 are chosen (and why):
  1. Only essays the model never trained on or tuned on: the split is "heldout_prompt" (a whole topic kept out of training and
     validation, see notebook 03). The topic is "Does the electoral college work?". A class writes on ONE topic, and an unseen
     topic is the situation the page's false-flag figures (2.3% / 3.9%) describe.
  2. Student essays: every human essay on that topic. AI essays: only those that are really about that topic (on_topic, notebook 06;
     half the dataset's AI essays are off-topic for their label), and not from the `train_essays` source, which holds the dataset's
     known mislabelled rows (notebook 04).
  3. The mix follows the real ratio in that split (62.6% student, 37.4% AI): 30 x 0.626 = 18.8, so 19 student and 11 AI.
  4. Random draw (seed 42) inside each group. No filter on length or on the detector's score.
  5. The order is shuffled (same seed) and the files get neutral names, so the file names and the order say nothing about the author.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from src.data import load_splits  # noqa: E402

SEED, SIZE, SPLIT, PROMPT = 42, 30, "heldout_prompt", "Does the electoral college work?"

split = load_splits(SPLIT)
ratio = (split["label"] == 0).mean()                         # the share of student essays in the whole held-out-prompt split
n_human = round(SIZE * ratio)
n_ai = SIZE - n_human

topic = split[split["prompt_name"] == PROMPT]
humans = topic[topic["label"] == 0]
ai = topic[(topic["label"] == 1) & topic["on_topic"] & (topic["source"] != "train_essays")]

rng = np.random.default_rng(SEED)
pick = lambda frame, n: frame.loc[rng.choice(frame.index.to_numpy(), size=n, replace=False)]
chosen = __import__("pandas").concat([pick(humans, n_human), pick(ai, n_ai)])
chosen = chosen.loc[rng.permutation(chosen.index.to_numpy())]

labels = []
for k, (row_id, row) in enumerate(chosen.iterrows(), start=1):
    name = f"essay_{k:02d}.txt"
    (HERE / name).write_text(row["text"])
    labels.append({"file": name, "label": "human" if row["label"] == 0 else "ai", "row_id": int(row_id), "split": row["split"],
                   "source": row["source"], "prompt": row["prompt_name"], "words": int(row["n_words"])})
(HERE / "labels.json").write_text(json.dumps(
    {"seed": SEED, "split": SPLIT, "prompt": PROMPT, "student_share_in_split": round(float(ratio), 4), "essays": labels}, indent=1))
print(f"{n_human} student + {n_ai} AI essays from {len(humans)} student / {len(ai)} AI candidates on '{PROMPT}' ({SPLIT})")
