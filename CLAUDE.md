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
3. Splits **stratify on label**, keeping the natural ratio. Do not force-balance. The full dataset is 61/39 human/AI, but train/val/test are 65/35 because the held-out generator slice removes only AI essays from the pool (see `03_split.ipynb`).
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
│   ├── 03_split.ipynb          leakage-safe split + held-out slices
│   ├── 04_baseline.ipynb       reference models + TF-IDF LogReg/SVM, leakage sanity checks
│   ├── 05_embeddings.ipynb     Word2Vec CBOW/Skip-gram vs GloVe, PCA/t-SNE, averaged-embedding classifier
│   ├── 06_topic_check.ipynb    on_topic flag for off-topic AI essays; Weeks 1–2 re-scored on the fair subset
│   └── 07_bilstm.ipynb         BiLSTM / BiGRU classifiers (CPU), Skip-gram vs random embedding init
├── data/
│   ├── raw/train.csv           DAIGT-V2, 44,868 rows — git-ignored
│   └── processed/
│       ├── train_deduped.csv   44,866 rows + n_words + dup_cluster — committed
│       ├── splits.csv          row_id → split (44,864 rows)
│       ├── on_topic.csv        row_id → topic_sim, on_topic (evaluation only)
│       └── DATA_CARD.md
├── results/                  04_baseline, 05_embeddings, 06_on_topic, 07_bilstm CSVs: metrics, one row per model
├── src/data.py               load_splits(): the one way to load data from 03 onward
├── src/evaluate.py           evaluate(): shared scoring for every model
├── models/                   trained vectors/weights — git-ignored
├── images/                   plots saved by the notebooks
├── README.md                 still the OLD readme with the 100% table
└── requirements.txt          (renamed from `requirements .txt` on 2026-10-04)
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

Weeks 1–3 are done (split, baseline, embeddings, off-topic flag, BiLSTM/BiGRU). Week 4 (BERT) is next and needs a GPU. The plan started on 2026-08-21, so the work is about five weeks behind it.

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
- 2026-10-03 — `04_baseline.ipynb` + `results/04_baseline.csv`:
  - TF-IDF (1–2 grams, fit on train only) + LinearSVM C=1: test F1 0.995 / AUC 1.000; held-out prompts F1 0.973 / AUC 0.997; held-out generators 90.9% detected, paired AUC 1.000. LogReg C=10 slightly behind.
  - References: always-human acc 0.654 / F1 0; length-only AUC 0.72; prompt-only AUC 0.76 (0.5 on unseen prompts).
  - The ~1.0 was checked and is not leakage: no echo or character shortcut explains it, and 2,000 training essays already give val AUC 0.997. DAIGT-V2 is really "student vs LLM" and easy in-distribution.
  - Real weakness is threshold calibration under shift: unseen Claude ranks perfectly but only ~85% clear 0.5; "Summer projects" humans are flagged 4.8% vs 0.1% on test.
  - Topic words (venus, nasa, car) are top human features.
  - Found a 3rd echo-mislabel (row 38107, train); documented, not dropped.
- 2026-10-04 — `05_embeddings.ipynb` + `src/evaluate.py` + `results/05_embeddings.csv` + 3 plots in `images/`:
  - Word2Vec CBOW and Skip-gram (100-d, train only, saved to git-ignored `models/`) vs GloVe-100 (in `~/gensim-data`).
  - Averaged embeddings + LogReg are worse than TF-IDF: test AUC 0.986–0.995; held-out prompts AUC Skip-gram 0.95, CBOW 0.88, GloVe 0.61. Averages mostly encode topic.
  - Held-out-prompt numbers vary run to run (multithreaded Word2Vec).
  - **Found: 43% of AI essays (7,570) are off-topic for their `prompt_name`**: generated from other prompts and filed under the nearest Persuade prompt. Topic is a big label shortcut. Recorded in the data card; how to handle it is still open.
  - `src/evaluate.py` holds the shared `evaluate()` (same logic as inline in `04`); use it from now on.
- 2026-10-04 — decision: off-topic AI essays are **flagged, not dropped**; splits unchanged; every model is also scored on on-topic essays.
- 2026-10-04 — `06_topic_check.ipynb` + `data/processed/on_topic.csv` + `results/06_on_topic.csv`:
  - `topic_sim` = content-word TF-IDF cosine to the prompt's human-essay centre ÷ that prompt's human median; `on_topic` = `topic_sim >= 0.5` (valley of a two-peaked AI distribution; robust at 0.4/0.6).
  - 50.0% of AI essays (8,747) are off-topic vs 0.9% of human. Six sources cause it (chat_gpt_moth 18% on-topic, mistral v1/v2, llama2_chat, ~half of falcon/llama_70b).
  - On-topic only: TF-IDF SVM unchanged (test AUC 0.9996, held-out prompts 0.997), so it learns style. Averaged GloVe falls to chance on held-out prompts (AUC 0.48); CBOW 0.84; Skip-gram 0.94.
  - On-topic `test` has only 473 AI essays: small differences there are noise.
- 2026-10-04 — `07_bilstm.ipynb` + `results/07_bilstm.csv` (both `all` and `on_topic` rows) + weights in `models/` (git-ignored):
  - BiLSTM/BiGRU (100-d embeddings, 64 units each way, max-pool, 384 tokens, 3 epochs, CPU). Masking instead of packing: packing was 12× slower on CPU; padding is 0.10% with bucketing.
  - On-topic held-out prompts AUC: TF-IDF 0.997 > BiLSTM random-init 0.957 ≈ BiLSTM Skip-gram 0.953 > BiGRU 0.934. On-topic held-out generator detection: BiGRU 95.5% > BiLSTM 90.8% > TF-IDF 88.0%.
  - Skip-gram init gave no head start over random init. GRU was ~2.6× slower than LSTM on CPU. Val AUC still rising at epoch 3.
  - Shared failure cases: formal human essays flagged as AI (fairness point); a few student-like `mistral7binstruct_v2` essays missed by every model (likely label noise).

**Not done**

- Everything in Weeks 3–10. There is still no neural network anywhere in the repo.

## Next up

### `Notebooks/08_bert.ipynb` — Week 4, syllabus unit V (the core model)

Fine-tune BERT/RoBERTa (HuggingFace `transformers`; add it to requirements). **Needs a GPU:** the laptop has an RTX 3050 Mobile (4 GB), but on 2026-10-04 no NVIDIA driver was loaded (kernel 7.0), so `torch.cuda.is_available()` is False. Options: Jaiveer fixes the driver (`sudo ubuntu-drivers install`, reboot, check `nvidia-smi`), or run this one notebook on Kaggle/Colab. With 4 GB VRAM, use DistilRoBERTa/DistilBERT or a base model with 256–512 tokens, small batches + gradient accumulation, fp16.

- Load with `from src.data import load_splits` (after `sys.path.append('..')`); never read the CSVs directly, or the whitespace shortcut comes back.
- Every model from here on will score ~1.0 on `test`. Compare models on the held-out slices and on fixed-threshold numbers (detection rate, false-positive rate), using `src/evaluate.py`.
- Report every model twice: `evaluate()` (all essays) and `evaluate_on_topic()`. The on-topic held-out-prompt score is the headline honest number.
- Planned robustness check for later weeks: typo injection (Kaggle's hidden test used character noise), plus the Week 6 paraphrase attack.

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
- `requirements.txt` will need `transformers` for Week 4. (Renamed and given `datasketch` + `torch` on 2026-10-04.)
- `data/processed/train_deduped.csv` is about 98 MB and is committed to the public repo. Only `data/raw/` is git-ignored. GitHub rejects files over 100 MB, so any larger processed file will fail to push.
- `data/raw/.ipynb_checkpoints/train-checkpoint.csv` is a stray 100 MB copy of the raw data (ignored by git, but wasting disk).
- `01_eda_baseline.ipynb` contains no baseline; consider renaming it to `01_eda.ipynb`.

## Conventions used so far

- Notebooks are numbered in order (`01_`, `02_`, …), one topic each.
- Each notebook opens with a goal, has a markdown cell explaining every step, and ends with a "Key takeaways" list for the next notebook.
- Sanity-check on a small case before running on the full data (notebook 02 tested on 2,000 rows first).
- Read real examples, not only summary numbers.
- Commit messages: a one-line summary, then bullets saying what was done and what was found.
