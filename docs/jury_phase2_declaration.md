# Jury, Phase 2: statistics declared before they are computed

Written 2026-11-08, after the 20 jurors were trained and exported (`f66d642`), before any jury statistic was computed.
The notebook `Notebooks/22_jury.ipynb` repeats this list in its first cells and fills it in. If a number is not on this list, the notebook labels it "extra".

## Fixed definitions
- **Juror**: one of 20 DistilRoBERTa detectors (seeds 42-61, same data and recipe), served from its fp16 copy. Group **A** = seeds 42-44 (they are also the official ensemble), group **B** = seeds 45-61 (17 jurors that are not).
- **A juror's zone** for an essay: its logit goes to its own tail probability `p` against its own 2,291 validation humans (`src/conformal.tail_p`). Flagged if p <= 0.00235, above usual if p <= 0.01032, else not flagged. These taus came from single-seed folds in 18b, so they apply to single models.
- `n_flag` = number of the 20 jurors (or of group A / group B) whose zone is "flagged". Not tuned on anything: the taus are the pre-declared ones.
- **Official verdict** = the 3-seed ensemble (mean of p-values of seeds 42-44, re-calibrated on the validation humans, flagged if p_ens <= 0.00235) computed here from the fp16 copies. It is checked against the pre-registered held-out numbers (results/20_heldout_scores.csv); differences are reported.
- **Populations**: `test` (humans and AI), `heldout_prompt` (humans and AI, pooled and by prompt), `heldout_generator` (AI only). `val` is used only for calibration and for rank agreement. **Held-out slices are descriptive: nothing is chosen from them.**
- Intervals: Wilson 95% for proportions (essays are near-independent after deduplication). Bootstrap intervals are stated where used.

## Statistics (id, definition, where saved)
All in `results/22_jury_summary.csv` (long format: stat, population, group, metric, value, lo, hi, n) unless a file is named; per-essay counts in `results/22_jury_per_essay.csv` (row_id, split, label, counts, no text).

| id | Statistic | File / metric |
|---|---|---|
| S0 | fp16 vs fp32-path zones, all 20 jurors, all 7,002 val+test essays, each path calibrated on its own validation humans. **Rule fixed now: a juror whose zones differ on more than 10 essays is served from fp32 and reported.** Also reported: fp32 scores judged with the fp16 cut-offs. | `22_fp16_vs_fp32_zones.csv` |
| S1 | Distribution of n_flag (0..20; group B 0..17), humans and AI separately, for test, heldout_prompt, heldout_generator (AI only). | summary: `n_flag_dist` |
| S2 | Among test + heldout_prompt humans that the official ensemble flags: how many jurors flag them (distribution, mean). | `ensemble_flagged_humans_n_flag` |
| S3 | Share of humans flagged by at least 1 juror, by all of them; share of AI flagged by all, by a majority (>= 11 of 20), by at least 1. Groups all-20, A, B. | `share_humans_ge1`, `share_humans_all`, `share_ai_all`, `share_ai_majority`, `share_ai_ge1` |
| S4 | Per juror: share of AI caught at its own tau(1%) line (test, heldout_prompt, heldout_generator), and its human false-flag rate (test, heldout_prompt). Range over jurors (min, median, max). | `22_jury_per_juror.csv`; summary `detect_range` |
| S5 | For AI essays: distribution of n_flag; and, for the "ceiling" AI essays (every one of the 20 jurors' logits >= 8.0, the tanh head saturates at about 9.8): how many have n_flag < 20. Plain-words wording for the page is proposed from these. | `n_flag_dist`, `ceiling_ai_not_unanimous` |
| S6 | Per juror: ceiling (max logit over val+test), flag line, gap = ceiling - flag line; number of test essays (humans, AI) within 0.5 logit either side of the flag line; share of the test AI essays that are flagged by less than 0.5 logit. | `22_jury_per_juror.csv` |
| S7 | Spearman rank correlation between jurors' logits, pairwise, on val and on test (all essays, and within humans, within AI): mean / min within A, within B, across all 190 pairs. | `spearman_pairs` |
| S8 | Flag-line bootstrap: jurors seeds 42, 50 and 56 (the first ensemble member, a juror whose val-1% cut-off is in the middle, and the one with the lowest). 1,000 cluster-bootstrap resamples (by dup_cluster) of the validation humans; range (2.5%-97.5%) of the juror's tau(1%) logit cut-off, and the number of test + heldout_prompt essays whose flagged / not flagged status changes from that alone (mean, 95th percentile). | `22_flagline_bootstrap.csv` |
| S9 | Typo jitter, 5% typos (`inject_typos`, seed = row_id), on a fixed sample: up to 600 test + heldout_prompt essays that split the jury (1 <= n_flag <= 19, "near the line"), and 600 that do not (n_flag 0 or 20, "far"), random seed 0. Per juror: share whose zone changes; per essay: mean number of jurors whose zone changes; share of essays on which the official ensemble's flagged / not flagged verdict changes. | `22_typo_jitter.csv`; summary `typo_*` |
| S10 | Seeds 45-61 reported separately from 42-44 in S1-S4 (group B rows). | group column |

## Why disagreement exists (stated for the page)
Two sources: (1) the trained weights differ with the seed; (2) each juror's calibration rests on the few validation humans near its line (at most 4 validation humans may score above the flag line). S8 measures the second one.
