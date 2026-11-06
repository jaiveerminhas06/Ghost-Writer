# Proposed edits after the model-improvement pass (APPLIED 2026-11-05, with changes)

**Status:** sections 1-4 were applied with these changes by the owner: the middle zone is named "above usual" and the label "cannot tell" is dropped, with the wording *"Higher than most student essays, but most essays that score here are written by students (about 7 in 10 at a one-third AI share, about 9 in 10 at 10%)"*; the fairness paragraph reports every attribute raw and prompt-adjusted (`21b`) instead of English learners only; the variant A mechanism numbers were added (Cowboy essays with >2% misspellings: 32 of 409 vs 3). Section 5 (demo switch) is approved in principle and deferred to the front-end work (CLAUDE.md, Next up). The text below is the original proposal and is kept as a record.

Branch `model-improvements`. Nothing in `README.md`, `MODEL_CARD.md` or `CLAUDE.md` has been changed; this file proposes the changes, with every number taken from a results file (named next to it). Apply on approval.

## 0 · The evidence in one table (final system = 3 seeds of the original recipe, mean of val-human tail probabilities, rule (d) thresholds)

| What | Number | Source |
|---|---|---|
| Thresholds on the p scale (tau 0.5% / 1% / 5%) | 0.00093 / 0.00235 / 0.01032 | `results/18b_final_thresholds_p_scale_original.csv` |
| Leave-one-topic-out, 13 topics, rule (d), 1% target: mean human false flags | 0.58% [0.44, 0.88] | `results/18b_rule_comparison_original.csv` |
| ... worst topic / topics over target / AI caught | 1.74% / 23% / 98.78% [97.74, 99.21] | same |
| Same, pooled-validation threshold (rule a, the old way) | 2.71% mean, 5.24% worst, 77% of topics over target | same |
| **Held-out check** (two unseen prompts, on-topic, point A): pooled human essays flagged | **0.70% [0.48, 0.95]** (31/4,420); Wilson [0.49, 0.99] | `results/20_heldout_tables.csv` |
| ... Electoral college / Summer projects | 0.11% [0.04, 0.33] / **1.60% [1.11, 2.31]** | same |
| ... old single-model "1%" threshold, same essays | 3.85% (170/4,420) | `results/09_threshold_rates.csv`, reproduced by H4 |
| AI essays on the held-out prompts, caught | 99.70% (on-topic, pooled) | `results/20_heldout_tables.csv` |
| **AI essays of unseen generators, caught** (Claude v6, v7, Falcon-180B; on-topic) | **94.92% [93.95, 95.80]** (1,944/2,048); old threshold 99.76% | same, H3 and H4 |
| ... by source | v6 94.83%, v7 92.92%, Falcon 98.82% | same |
| ... flagged **or** in the "above usual" zone | 98.97% | same |
| Cannot-tell band: humans / AI essays in it | 2.62% / 2.21% | same |
| P(AI \| above usual) at 34.6% / 10% / 5% AI share | 30.8% [24.9, 36.7] / 8.6% / 4.2% | same, H6 |
| P(AI \| flagged) at 34.6% / 10% / 5% | 98.7% / 93.9% / 88.0% | same, H6 |
| Val-chosen 1% logit threshold of the three seeds | +4.67 / +5.28 / +7.82 | `15_claims_audit.csv`, `19_ensemble_stability.ipynb` |
| Humans flagged by one seed that all three flag | 14% (fold 7), 16% (fold 11), 40% (held-out; 21 of 52) | `results/19_agreement.csv`, `15_claims_audit.csv` |
| Flip rate under 5% typos, essays near the line | 26% (test + val AI), 40% (fold 11), single models | `results/19_flip_rates.csv` |
| English-learner essays flagged | 0 of 340 (upper bound 1.12%); other students 33 of 6,120 (0.54%) | `results/21_fairness_by_group.csv` |
| Training change tested and rejected (variant A, spelling/typo augmentation) | 7-fold -0.86 [-1.50, -0.26]; **13-fold +0.57 [+0.19, +1.16]**; Cowboy 4.30% -> 17.42% | `results/17b_variantA_13fold.csv` |

## 1 · Stale statements to fix (apply when approved)

**README.md**
- line 123: `tests/ 46 API tests, including the privacy tests` -> `49 tests (46 API tests including the privacy tests, and 3 browser tests for the highlights)`.
- line 159 (Status): `the demo (now a web app, on the frontend branch)` -> `the demo (a web app, merged into main)`; the sentence "Still to come: the written report and slides, then final polish" stays true.
- the "in progress" badge (line 6) -> `modelling complete, report and slides pending` (or remove it).
- line 126: add `scripts/` rows: `lopo_run.sh`, `phase3_run.sh`, `phase5_run.sh`, `build_persuade_demographics.py`; add `src/` modules (see 2).
- line 100-101 area: the demo screenshot and description still describe a single-model verdict; see 5.

**CLAUDE.md**
- line 75: drop the trailing "`frontend` branch" from the `api/` row.
- line 78: `46 API tests incl. privacy tests` -> `49 tests (46 API incl. privacy, 3 browser)`.
- line 106 (Status): replace the sentence "The web front end (branch `frontend`, phases 1-8) is finished and waiting for the owner's review before it is merged into `main`" with "The web front end is merged into `main` (62a15df)".
- lines 215, 218, 222: past-tense entries; add "(merged 2026-11-05)" to the 2026-11-02 entry and delete "not merged into `main`; owner reviews the diff first".
- line 234 (Next up): delete "First review and merge the `frontend` branch."

## 2 · README.md: proposed new content

**Headline result** (replace the current table; keep the caveat sentence):

| Evaluation (on-topic essays; held-out prompts and generators scored once, at the end) | Result |
|---|---|
| Human essays wrongly flagged on two unseen prompts, final system at its "1%" operating point | **0.70%** [0.48, 0.95] pooled; 0.11% on one prompt and **1.60%** [1.11, 2.31] on the other |
| The same essays with the earlier single-model "1%" threshold | 3.85% |
| AI essays on those prompts caught | 99.70% |
| AI essays from three AI models never seen in training caught | **94.92%** [93.95, 95.80] (98.97% flagged or in the "above usual" band); 99.8% with the earlier threshold |

Add two sentences under it: *"The stricter threshold cuts false flags on new topics fivefold and costs about five points of detection on AI models it has never seen. The single-model threshold of earlier notebooks was set on familiar topics and flagged 3.85% of unseen-topic students."*

**New section "What the external review changed"** (short): error bars on every number (`15`), thresholds that do not transfer between seeds (`15`, `19`), a common probability scale and a threshold rule judged on topics it was not set on (`18`, `18b`), a three-seed ensemble (`19`), a documented negative result on training-data augmentation (`17`, `17b`, `17c`), a held-out check defined and committed before it was run (`20`).

**Notebook table:** add rows 15-21 (`15_uncertainty` error bars and claims audit; `16_long_essays` windowed scoring; `16b_topic_lopo` leave-one-prompt-out; `17_augment`/`17b`/`17c` augmentation, a negative result; `18_robust_threshold`/`18b` threshold rules; `19_ensemble_stability`; `20_final_heldout_check`; `21_fairness_persuade`).

**Limitations to add / rewrite** (each with its number):
- the false-flag rate varies by topic: 0.4% to 5.8% across 13 unseen topics with the old threshold (`16b`); one of two held-out prompts is above 1% even with the new one (1.60%);
- a flag is not a stable fact about an essay: only 14-40% of humans flagged by any seed are flagged by all three; essays near the line flip under 5% typos 26-40% of the time;
- the strict threshold loses detection on unseen AI generators (94.9%);
- only two held-out topics, not pristine (the single model was scored on them before);
- no evidence of a higher flag rate for English-learner students (0 of 340) but power is limited (an excess up to about twofold cannot be excluded); not a test of TOEFL-style non-native writers.

**Reproducing:** add `pip install -r requirements-lock.txt` as the exact-version option; add that notebooks 16b, 17, 19 need GPU time (about 15 minutes per fine-tune; 15 folds of 16b take 3 h 48 min; the Phase 5 jobs take about 75 minutes), and that Phase 6 needs the public PERSUADE 2.0 files (`scripts/build_persuade_demographics.py`).

## 3 · MODEL_CARD.md: proposed changes

- **Model table, "Decision rule":** replace the strict/standard logit thresholds with: *"A three-seed ensemble. Each seed's score is converted to its val-human tail probability p; the ensemble is the mean of the three p-values, re-calibrated on the validation humans. Flag if p <= 0.00235 ('1%' operating point); essays with 0.00235 < p <= 0.01032 are 'above usual' (not evidence of AI writing); the strict point flags at p <= 0.00093. The thresholds were chosen by a rule declared in advance and judged leave-one-topic-out over 13 topics (18b)."*
- **Evaluation table:** replace the two false-positive-rate rows with the held-out numbers of section 0 (including both prompts, the unseen-generator detection, and the band).
- **Known failure modes:** rewrite bullet 1 ("A threshold does not carry over to new topics") as *"A threshold in logits belongs to one trained model (three seeds: +4.67, +5.28, +7.82 at AUC 0.9998) and does not carry over to new topics; the p-scale rule narrows the topic spread but one of two held-out prompts is still above 1% (1.60%)."* Replace bullet 2 ("the wrongly flagged essays are the best writers ... longer") with *"False flags fall on more predictable, better-spelled, more formulaic essays within a topic (GPT-2 perplexity -0.95 SD, misspellings -0.43 SD; 16b); they are **not** longer within a topic (long essays are flagged less than short ones, -1.6 points prompt-adjusted)."* Add: unseen-generator detection 94.9%; seed instability (14-40%); near-threshold flips (26-40%); the band is mostly, not entirely, human (about 7 in 10 at one third AI).
- **Not tested -> Partly tested:** *"US school English learners: 0 of 340 flagged (upper bound 1.12%, about twice the other students' rate); no evidence of a higher rate; power limited; not a test of TOEFL-style non-native writers. Adults, other genres and languages, newer AI models and humanisers: not tested."*
- **New section "Training-data augmentation (rejected)":** spelling repair plus injected typos looked good on seven prompts chosen from the extremes (-0.86 points) and failed on all 13 (+0.57 [+0.19, +1.16]; Cowboy 4.30% to 17.42%); lesson: subset evaluation can miss topic-specific failures.
- **Ethical considerations (add):** "Only 14-40% of humans flagged by at least one of three seeds are flagged by all three, and an ensemble does not fix this (small samples: 7-52 essays). Whether a student is flagged partly depends on which training run produced the model." Keep the existing sentences about false accusation.

## 4 · CLAUDE.md: proposed content

- **Status:** "Weeks 1-8 and the model-improvement pass (notebooks 15-21) are done. Final system: three-seed ensemble of the original recipe on the p scale (rule (d) thresholds from 18b); the held-out check (20) was run once. Week 9 (report and slides) is next."
- **Done:** one entry per notebook 15-21, each three or four bullets copied from the notebook's key takeaways (numbers from the sources in section 0), plus the housekeeping facts: `scripts/lopo_*`, `phase3_run.sh`, `phase5_run.sh` are resumable and time-boxable (`HOURS=`); training on battery is ~40% slower; same-seed GPU reruns differ by up to ~0.7 points on a fold (fold 11: 5.80% vs 6.51%); `results/16b_lopo/`, `17_variants/`, `17_final/`, `19_phase5/` hold per-essay scores; model folders `models/distilroberta_aug_s*`, `distilroberta_orig_s43`, `_s44` are git-ignored.
- **Decisions (new):** 9. Final recipe is the original (variant A rejected on 13-fold evidence). 10. Thresholds live on the val-human tail-probability scale; the declared Phase 4 rule picked (d) for the original. 11. The held-out prompts and generators were checked once, after the definition was committed (d1dd1eb) and the run code (7670717).
- **Folder layout:** add `src/compare.py`, `conformal.py`, `ensemble.py`, `spelling.py`, `augment.py`; `scripts/lopo_fold*.py`, `train_variant.py`, `phase*_run.sh`, `build_persuade_demographics.py`; `Notebooks/15`-`21`; `docs/`: this file; `data/external/` (git-ignored: augmented training text, PERSUADE mapping).
- **Next up:** report and slides (storyline: fake 100% -> leakage-safe split -> honest scores -> what looked good but was not [topic shortcut, attribution, threshold shift, augmentation] -> error bars and the p scale -> the held-out check -> the demo).

## 5 · Recommendation: should the demo switch to the new method? (your decision; front end later)

**Evidence for switching the verdict to the ensemble with p-scale thresholds and the band**
- Human false flags on unseen topics fall from 3.85% to 0.70% (pooled), and from 7.7% to 1.60% on the hardest prompt.
- The ensemble protects against one bad seed (flip rate over all essays -1.1 and -1.8 points vs the average single model) and matches the Phase 4 predictions at the final thresholds (0.09% and 0.97% on the two folds tested).
- The band gives a way to avoid accusing the shifted tail, and the wording can be made honest (section 3 / `20`, H6).

**Evidence against, or costs to accept**
- Detection of unseen AI generators drops to 94.9% flagged (98.97% with the band); this was not measured in Phase 4.
- Individual verdicts are unstable: near the line a light perturbation flips 26-40% of verdicts; only 14-40% of humans flagged by any seed are flagged by all three. The demo's "try to fool it" would show this.
- Cost: three models per request (about 3x the scoring time and three DistilRoBERTa copies in 4 GB; the explanation methods would stay on one model).
- One of two held-out prompts is above 1% (1.60%), and two topics cannot confirm the 13-topic result.

**My recommendation:** switch, with these conditions: (1) show the zone (flagged / unusual but common for student essays / not flagged), not a yes/no; (2) use the revised wording numbers from `20` (about 7 in 10 of band essays are students' at one third AI, about 11 in 12 at 10%; about 1 in 16 flagged essays is a student's at 10% AI); (3) keep the explanations from the seed-42 model and say so; (4) show per-seed agreement on borderline essays; (5) state the 94.9% unseen-generator figure next to the headline. If three models per request is too heavy for the hosted version, keep the single model with the p-scale threshold calibrated on its own val humans and say the ensemble was not used.

## 6 · Requirements pin (done, not a proposal)

I chose to **add `requirements-lock.txt`** (exact installed versions of everything named in `requirements.txt` and `requirements-dev.txt`, plus scipy, nbformat, nbconvert, pillow, playwright and joblib, which the notebooks and tests of this pass use) and to leave `requirements.txt` with loose names, so a fresh machine can still resolve versions while the lock records what the results were produced with. torch is the CUDA build (`2.12.0+cu130`), noted in the file. The npm side is already locked by `frontend/package-lock.json`.

## 7 · Open items for the owner

- Rule (b) vs (d) for variant A is moot (variant A is rejected); the original recipe's rule (d) was applied unchanged.
- The "above usual" zone wording: adopt the revised fractions from `20` or drop the middle label.
- Whether to report the held-out numbers per prompt in the README headline (recommended: yes, both prompts, because one is above target).
- Optional later work: the repair-versus-injection ablation for variant A; a third and fourth held-out topic.
