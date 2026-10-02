# Ghost Writer — handoff for Claude Code

Written 2026-10-02 from the state of this folder and its git history. Update the **Status** and **Next up** sections as work lands, so this file stays true.

## What this project is

An AI-generated-text detector: given an essay, decide whether a human or an LLM wrote it, and show why.

- **Owner:** Jaiveer Singh Minhas (student). It is his course project for **CSE472: Deep Learning for NLP**, and is also meant to go on his resume.
- **There is a viva.** Jaiveer has to explain every step himself, so explain what each step does and why before or while writing it. Don't hand over large blocks of unexplained code.
- **Remote:** `https://github.com/jaiveerminhas06/Ghost-Writer` (public), branch `main`.

## Background: why the project was rebuilt

The original version (now in `Archive/`) reported 100% accuracy. That number was not real:

- Human essays came from Kaggle's `train_essays.csv`; the AI essays were 141 essays from one self-generated batch.
- With 282 samples and a 57-essay test set, TF-IDF + Logistic Regression/SVM learned that one batch's style, not AI writing in general.
- It also had no deep learning at all, which the course requires.

The rebuild keeps the same repo and topic, replaces the data with DAIGT-V2, and adds one syllabus unit at a time.

## Decisions already made (don't reopen without a reason)

1. Keep this repo and theme; do not start a new project. The old work stays in `Archive/` as the "before" for the viva.
2. Dataset is **DAIGT-V2**.
3. Splits **stratify on label at about 61/39**. Do not force-balance to 50/50.
4. Near-duplicates are **kept, not dropped**. Each essay carries a `dup_cluster` id, and no cluster may be divided across train/val/test.
5. The two essays under 20 words are dropped (both are broken AI generations).
6. The final demo shows more than a yes/no label:
   - sentence-level highlighting of suspicious sentences,
   - generator attribution (which model family wrote it),
   - a live "try to fool it" button that paraphrases the text and re-scores it.
7. Paragraph-level mixed-authorship detection is **out of scope**.
8. The BiLSTM-NER (CoNLL) practical from the syllabus was left out on purpose. Still to confirm with the professor whether every listed practical must appear in the project.

## Folder layout

```
Ghost_Writer/
├── Archive/                  old flawed version: baseline_flawed.ipynb, old data, report, plots
├── Notebooks/
│   ├── 01_eda_baseline.ipynb   EDA of DAIGT-V2 (no model in it, despite the name)
│   ├── 02_dedup.ipynb          near-duplicate detection (MinHash + LSH)
│   └── 03_split.ipynb          leakage-safe split + held-out slices
├── data/
│   ├── raw/train.csv           DAIGT-V2, 44,868 rows — git-ignored
│   └── processed/
│       ├── train_deduped.csv   44,866 rows + n_words + dup_cluster — committed
│       ├── splits.csv          row_id → split (44,864 rows)
│       └── DATA_CARD.md
├── src/data.py               load_splits(): the one way to load data from 03 onward
├── images/                   empty
├── README.md                 still the OLD readme with the 100% table
└── requirements .txt         note the space in the filename
```

Notebooks are run from inside `Notebooks/`, so they use paths like `../data/raw/train.csv`.

## The data

`data/raw/train.csv` columns: `text`, `label` (0 = human, 1 = AI), `prompt_name`, `source`, `RDizzl3_seven`.

- 44,868 essays: 27,371 human, 17,497 AI (61/39).
- **17 sources:** `persuade_corpus` (25,996 human essays), `train_essays` (1,378 rows from the original Kaggle file), and 15 AI generators covering GPT-3.5, GPT-4, Claude, PaLM, Cohere, Llama 2, Mistral 7B and Falcon-180B.
- Every source has a single label except `train_essays`, which has 3 AI-labelled rows among its 1,378.
- **15 prompts**, 1,583 to 5,554 essays each. `RDizzl3_seven` is a per-prompt flag: True for the seven prompts used in the original Kaggle test set.
- No missing values and no exact duplicate rows.
- AI essays are shorter and more uniform: mean 329 words (std 94) against 418 (std 189) for human. This is a known surface signal; note it in the data card rather than hiding it.

`data/processed/train_deduped.csv` is the file later notebooks should load. It adds:

- `n_words` — word count,
- `dup_cluster` — near-duplicate group id.

## Status

Week 1 of 10: split done, baseline next. Last commit was 2026-09-09. The plan started on 2026-08-21, so the work is about five weeks behind it.

**Done**

- 2026-08-21 — repo restructured, old work archived, raw data untracked.
- 2026-08-27 — `01_eda_baseline.ipynb`: the dataset facts listed above.
- 2026-09-09 — `02_dedup.ipynb`:
  - 5-word shingles → MinHash (128 permutations) → LSH at threshold 0.7 → Union-Find to merge chained matches.
  - 44,866 essays fall into 43,780 clusters.
  - 1,077 clusters hold more than one essay: 1,075 pairs, one triple, one group of 10.
  - 1,069 clusters span more than one source.
  - 2 clusters contain both a human and an AI essay.
  - The full MinHash build took about 4.5 minutes; don't re-run it, load the saved CSV.
- 2026-10-02 — `03_split.ipynb` + `src/data.py` + `data/processed/DATA_CARD.md`:
  - All 15 prompts have both labels, but AI share per prompt ranges from 14% to 70% (a topic shortcut).
  - 1,067 of the cross-source clusters are the same human essay in `persuade_corpus` and `train_essays`; harmless.
  - The 2 mixed-label clusters held "AI" essays that are verbatim truncated prefixes of human essays; dropped (row_ids 33338, 36311).
  - Whitespace leaked the label (4 AI sources start every essay with a space; no human essay does). `src/data.py` strips it at load.
  - Held out: prompts "Does the electoral college work?" + "Summer projects"; generators Claude (v6, v7) + Falcon-180B.
  - Rest split 80/10/10 with StratifiedGroupKFold(10, seed 42) on `dup_cluster`: train 28,006 / val 3,501 / test 3,501, each 34.6% AI (65/35, not 61/39, because the generator slice is all AI). Held-out prompt 7,135; held-out generator 2,721.
  - Only `splits.csv` (row_id → split, 0.6 MB) is saved; no second copy of the text.

**Not done**

- Honest classical baseline.
- Everything in Weeks 2–10. There is still no neural network anywhere in the repo.

## Next up

### `Notebooks/04_baseline.ipynb` — honest classical baseline

TF-IDF + Logistic Regression/SVM on the new split, reported on the normal test set and on both held-out slices. This is the number that replaces the fake 100%.

- Load with `from src.data import load_splits` (after `sys.path.append('..')`); never read the CSVs directly, or the whitespace shortcut comes back.
- Tune on `val` only. Report precision/recall/F1/ROC-AUC, not just accuracy (always guessing "human" gets 65%).
- Held-out generator slice is AI-only: report detection rate, or AUC paired with `test`'s human essays.
- Compare against a length-only and a prompt-only model, to show how much of the score the surface signals in the data card explain.

## Roadmap after Week 1

| Week | Work | Syllabus unit |
|---|---|---|
| 2 | Word2Vec/GloVe, CBOW vs Skip-gram, PCA/t-SNE plots | II |
| 3 | BiLSTM/GRU classifier | III |
| 4 | Fine-tuned BERT/RoBERTa (HuggingFace) — the core model | V |
| 5 | GPT-2 perplexity detector, DetectGPT-lite, generator attribution | VI |
| 6 | Small seq2seq + attention paraphraser, used to attack the detector | IV |
| 7 | SHAP/attention explainability, sentence-level flags, error analysis, ethics and limitations | — |
| 8 | Interactive demo (highlighting, attribution, "try to fool it") and model card | — |
| 9 | README rewrite, short report, slides | — |
| 10 | Polish, git cleanup, viva rehearsal | — |

The plan can compress to 8 weeks. Full version with the demo mockup: https://claude.ai/code/artifact/395f73c0-8dd5-4bad-a622-fbeaecfeff73

## Housekeeping still open

- `README.md` still shows the old 100% results table. The full rewrite is planned for Week 9, but the table is misleading until then.
- `requirements .txt` is missing `datasketch` (used by notebook 02) and has a space in its name. It will also need `torch` and `transformers` from Week 3 onward.
- `data/processed/train_deduped.csv` is about 98 MB and is committed to the public repo. Only `data/raw/` is git-ignored. GitHub rejects files over 100 MB, so any larger processed file will fail to push.
- `data/raw/.ipynb_checkpoints/train-checkpoint.csv` is a stray 100 MB copy of the raw data (ignored by git, but wasting disk).
- `01_eda_baseline.ipynb` contains no baseline; consider renaming it to `01_eda.ipynb`.

## Conventions used so far

- Notebooks are numbered in order (`01_`, `02_`, …), one topic each.
- Each notebook opens with a goal, has a markdown cell explaining every step, and ends with a "Key takeaways" list for the next notebook.
- Sanity-check on a small case before running on the full data (notebook 02 tested on 2,000 rows first).
- Read real examples, not only summary numbers.
- Commit messages: a one-line summary, then bullets saying what was done and what was found.
