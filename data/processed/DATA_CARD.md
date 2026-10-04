# Data card — DAIGT-V2 as used in Ghost Writer

Produced by `Notebooks/01_eda_baseline.ipynb`, `02_dedup.ipynb` and `03_split.ipynb`.
Load the data with `from src.data import load_splits`; don't read the CSVs directly.

## Source

DAIGT-V2 (Kaggle, "LLM - Detect AI Generated Text" competition community dataset).
Student essays written for 15 prompts, labelled `0` = human, `1` = AI.

- **Human:** `persuade_corpus` (Persuade 2.0, grades 6–12) and `train_essays` (the competition's own
  training file, itself drawn from Persuade).
- **AI:** 15 generator sources covering GPT-3.5, GPT-4, Claude, PaLM, Cohere, Llama 2 (7B, 70B),
  Mistral 7B and Falcon-180B.

## Files

| File | Rows | Contents |
|---|---|---|
| `data/raw/train.csv` (git-ignored) | 44,868 | original download |
| `data/processed/train_deduped.csv` | 44,866 | adds `n_words`, `dup_cluster` |
| `data/processed/splits.csv` | 44,864 | `row_id` → `split`; `row_id` is the row number in `train_deduped.csv` |

## Cleaning, in order

1. **Dropped 2 essays under 20 words** (`01`): broken AI generations.
2. **Near-duplicate clustering** (`02`): 5-word shingles → MinHash (128 perms) → LSH at Jaccard 0.7 →
   union-find. Near-duplicates are **kept**; `dup_cluster` groups them (43,780 clusters, 1,077 with
   more than one essay). 1,067 of the multi-essay clusters are the same human essay in both
   `persuade_corpus` and `train_essays`. No cluster spans two prompts.
3. **Dropped 2 mislabelled "AI" essays** (`03`, row_ids 33338 and 36311, `mistral7binstruct_v2`): each
   is a word-for-word prefix of a human Persuade essay, truncated mid-sentence. They contain no AI text.
   **Known residual noise:** `04_baseline` found one more echo of this kind (row_id 38107,
   99.8% copied from human row 23962), missed by MinHash because the copy is only 62% of the
   human essay. Both are in `train`, so nothing crosses a split; left in as 1 noisy label in ~9,700.
   13 other AI essays share only their first sentence with a human essay (~7% of the text).
4. **Stripped leading/trailing whitespace** (`03`, applied by `src/data.py` at load time). Raw text
   leaks the label: 0% of human essays start with whitespace, while 100% of four AI sources do;
   50% of human essays end with whitespace vs 0.8% of AI ones.

## Splits

| Split | Essays | Human | AI | AI share | Purpose |
|---|---|---|---|---|---|
| `train` | 28,006 | 18,325 | 9,681 | 34.6% | fitting |
| `val` | 3,501 | 2,291 | 1,210 | 34.6% | tuning, model selection |
| `test` | 3,501 | 2,291 | 1,210 | 34.6% | in-distribution score, touched once |
| `heldout_prompt` | 7,135 | 4,464 | 2,671 | 37.4% | unseen topics |
| `heldout_generator` | 2,721 | 0 | 2,721 | 100% | unseen model families |

- **Held-out prompts:** "Does the electoral college work?" and "Summer projects" (all essays, both labels).
- **Held-out generators:** `darragh_claude_v6`, `darragh_claude_v7`, `falcon_180b_v1`, on the
  remaining 13 prompts. These are whole families: no Claude or Falcon text is in train/val/test.
  The slice is AI-only, so score it by detection rate, or by AUC when paired with `test`'s human essays.
- **Method:** the two slices are removed first; the remaining 35,008 essays are split with
  `StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)`, groups = `dup_cluster`,
  stratify = `label`; fold 0 → test, fold 1 → val, folds 2–9 → train.
- **Guarantees (asserted in `03`):** no `dup_cluster` in two splits; no held-out prompt or generator
  in train/val/test. Every source and prompt is spread ≈ 80/10/10 across train/val/test.
- **Why 34.6% and not the dataset's 39% AI:** the generator slice removes 2,721 essays from the
  pool, all of them AI. We kept that natural ratio instead of discarding human essays to force 39%.
  Accuracy alone is misleading at 65/35 (always guessing "human" gives 65%). Report precision,
  recall, F1 and ROC-AUC.

## Known biases and surface signals

A detector can score well by exploiting these instead of learning anything about AI writing.
Later notebooks should test against them (e.g. a length-only or prompt-only baseline).

- **Length:** AI essays are shorter and far more uniform (train: human mean 403 words, std 184;
  AI 326, std 95). Held-out-prompt essays are longer than average (human mean 501), and Claude/Falcon
  essays are especially uniform (mean 304, std 51).
- **Topic:** AI share per prompt ranges from 14% ("Exploring Venus") to 70% ("Seeking multiple
  opinions"), so the topic alone partly predicts the label.
- **Whitespace:** neutralised by stripping (see above). Other formatting habits remain per generator,
  e.g. letter openings ("Dear …") and title lines are more common for some sources. Those are
  arguably part of the generator's style, so they were left in.
- **Anonymisation placeholders:** 12% of `persuade_corpus` essays contain tokens such as
  `Generic_Name`, against 0–4% for every AI source. Their presence leans "human". Left in, but
  a token-importance check in Week 7 should confirm the model isn't relying on them.

## Scope and limitations

- English argumentative essays by US students in grades 6–12, responding to a fixed set of 15
  prompts. Results do not transfer to other genres, languages or writer populations without testing.
- Human essays come from a small number of sources, so "human" means "student essay from Persuade".
  Fluent adult writing was never seen as human and may be flagged as AI.
- Generators are 2023-era models with the competition's prompting styles. Newer models are unseen.
- False positives have real costs (accusing a student of using AI). This is a course project and
  must not be used to make decisions about real students.
