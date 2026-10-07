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
│   ├── 07_bilstm.ipynb         BiLSTM / BiGRU classifiers (CPU), Skip-gram vs random embedding init
│   ├── 08_bert.ipynb           DistilRoBERTa fine-tuned vs frozen (GPU), curly-quote shortcut check
│   ├── 09_threshold.ipynb      decision thresholds chosen on val for a target false-positive rate
│   ├── 10_zero_shot.ipynb      GPT-2 perplexity / burstiness / log-rank, DetectGPT-lite, spelling confound
│   └── 11_attribution.ipynb    which model family wrote it: random split vs leave-one-source-out
├── data/
│   ├── raw/train.csv           DAIGT-V2, 44,868 rows — git-ignored
│   └── processed/
│       ├── train_deduped.csv   44,866 rows + n_words + dup_cluster — committed
│       ├── splits.csv          row_id → split (44,864 rows)
│       ├── on_topic.csv        row_id → topic_sim, on_topic (evaluation only)
│       └── DATA_CARD.md
├── results/                  04_baseline … 11_attribution CSVs: metrics per model, thresholds, GPT-2 features
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

Weeks 1–4 are done (split, baseline, embeddings, off-topic flag, BiLSTM/BiGRU, DistilRoBERTa, threshold choice). Week 5 is done (zero-shot GPT-2 detection, generator attribution). Open: how the demo's attribution panel should behave (see 2026-10-07 entry). Week 6 (paraphrase attack) is next. The plan started on 2026-08-21, so the work is about five weeks behind it.

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

- 2026-10-04 — GPU fixed: the 7.0 kernel had no NVIDIA module (driver meta-package was stuck on 6.17). Installed `linux-modules-nvidia-580-open-7.0.0-34-generic`, which upgraded the driver to 580.178.04 and brought kernel 7.0.0-38 with its module. RTX 3050 Laptop, 4 GB, compute 8.6; `torch.cuda.is_available()` True. Matmul ~19× faster than CPU in fp32, ~39× in fp16. If a future kernel update loses the GPU again, install `linux-modules-nvidia-580-open-$(uname -r)`.

- 2026-10-05 — `08_bert.ipynb` + `results/08_bert.csv` + `models/distilroberta_finetuned/` (git-ignored, 317 MB):
  - DistilRoBERTa fine-tuned 2 epochs on GPU (512 tokens, batch 16, fp16, AdamW 2e-5, 6% warm-up + linear decay); ~15 min. Peak 3.2 GB of 3.68 GB usable. The sanity-check cell must free `loss`/`logits` too, or ~700 MB leaks and training OOMs.
  - On-topic held-out prompts AUC 0.9998 (best); held-out generators 99.9% detected (best).
  - Over-flags humans at threshold 0.5: on-topic test precision 0.938, 1.4% of test Persuade flagged, 10.5% of held-out "Summer projects" humans flagged. Threshold calibration (choose on val for a target FPR) is the obvious follow-up.
  - Frozen encoder + head already gets AUC 0.999 / 99.8%; fine-tuning mostly improves F1/precision.
  - Curly-quote counterfactual: no systematic shortcut.

- 2026-10-05 — `09_threshold.ipynb` + `results/09_thresholds.csv` + `results/09_threshold_rates.csv` + `images/09_val_tradeoff.png`:
  - Thresholds chosen on val humans for target FPR 5% / 1% / 0.5% (quantiles of human val scores; DistilRoBERTa on the logit scale).
  - DistilRoBERTa @1% (logit 4.67): test FPR 0.92%, held-out-prompt FPR 3.85% (default 5.61%), unseen generators 99.8% caught. @0.5% (logit 7.80): test 0.40%, held-out prompts 2.31%, generators 99.2%. Best operating point so far; the 0.5% quantile rests on ~12 val essays.
  - A threshold set on val doesn't guarantee the FPR on new topics ("Summer projects" humans still 7.7% @1%).
  - TF-IDF: calibrating to 1% *lowers* its threshold and held-out-prompt FPR explodes 2.1% → 33.8%. Its human scores shift heavily on new topics.
  - Residual false positives are longer, polished human essays (median 489 vs 442 words): the fairness point.

- 2026-10-05 — `10_zero_shot.ipynb` + `results/10_zero_shot.csv` + `results/10_gpt2_features.csv` + `results/10_detectgpt_sample.csv` + `images/10_gpt2_signals.png`:
  - GPT-2 small scores every essay (first 512 tokens): log-perplexity, burstiness, mean log-rank. ~24 min for 44,864 essays.
  - Zero-shot perplexity: on-topic test AUC 0.978, held-out prompts 0.939, but held-out generators only 18% detected (paired AUC 0.65). Per-source perplexity: PaLM 5.5, Mistral 6.5 … GPT-4 23.5, Claude 26, human 29.
  - DetectGPT-lite (distilroberta-base fills 15% of tokens, original token excluded; 10 perturbations; 256 tokens; 800-essay sample): AUC 0.705, worse than plain perplexity (0.978). Generator ≠ scoring model.
  - Perplexity correlates with misspellings among humans (Spearman 0.58); best-spelled humans flagged 1.9% vs 0.8%.
  - Tooling: the first GPT-2 download hung on finalising (`hf_xet`); redownloaded with `HF_HUB_DISABLE_XET=1`. Run notebooks with `HF_HUB_OFFLINE=1` once models are cached.

- 2026-10-07 — `11_attribution.ipynb` + `results/11_attribution.csv` + `results/11_attribution_loso.csv` + `images/11_attribution_confusion.png`:
  - 8 families from 15 sources (`radek_500` assumed GPT-3.5 from its name, not verified); 17,490 AI essays; own 80/10/10 StratifiedGroupKFold split on `dup_cluster`, stratified by family.
  - Random split: TF-IDF + LinearSVM (C=3, balanced) macro-F1 0.976 (on-topic 0.981); DistilRoBERTa 8-way 0.943; GPT-2 features 0.41.
  - **Leave-one-source-out collapses:** unseen sources get the right family 0–28% of the time (TF-IDF), 0–25% (DistilRoBERTa), at or below chance (12.5%). The models learn the source/pipeline, not the family. `radek_500` → GPT-4 99% (same author as `radekgpt4`).
  - Confidence doesn't help: unseen-source essays with top prob ≥ 0.9 are only 10% correct.
  - Implication: the demo's "which model wrote it" panel (decision 6) would mislead; needs a decision.

**Not done**

- Decide how (or whether) the demo shows generator attribution.
- Weeks 6–10.

## Next up

### Week 6, syllabus unit IV — seq2seq + attention paraphraser to attack the detector

Build a small encoder–decoder with attention, train it to paraphrase, and use it (plus simple typo injection) to see how far the fine-tuned DistilRoBERTa's detection drops. Use thresholds from `results/09_thresholds.csv`. The saved detector is in `models/distilroberta_finetuned/`.

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
- `data/processed/train_deduped.csv` is about 98 MB and is committed to the public repo. Only `data/raw/` is git-ignored. GitHub rejects files over 100 MB, so any larger processed file will fail to push.
- `data/raw/.ipynb_checkpoints/train-checkpoint.csv` is a stray 100 MB copy of the raw data (ignored by git, but wasting disk).
- `01_eda_baseline.ipynb` contains no baseline; consider renaming it to `01_eda.ipynb`.

## Conventions used so far

- Notebooks are numbered in order (`01_`, `02_`, …), one topic each.
- Each notebook opens with a goal, has a markdown cell explaining every step, and ends with a "Key takeaways" list for the next notebook.
- Sanity-check on a small case before running on the full data (notebook 02 tested on 2,000 rows first).
- Read real examples, not only summary numbers.
- Commit messages: a one-line summary, then bullets saying what was done and what was found.
