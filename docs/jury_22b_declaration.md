# 22b (attacks on the final system) and the abstention rule: declared before computing

Written 2026-11-09, after Phase 2 (`8ab10bb`), before any attacked essay is scored. Applies to `Notebooks/22b_attack_final.ipynb`. Nothing here changes the final system.

## 22b: attacks on the official ensemble
**System under attack.** The official verdict: three-seed ensemble (seeds 42-44, mean of val-human tail probabilities, re-calibrated), computed on the fp16 copies (Phase 2 showed it reproduces notebook 20's verdicts exactly). *Flagged* = p_ens <= 0.00235; *above usual* = 0.00235 < p_ens <= 0.01032; otherwise *not flagged*. The 20 jurors (fp16, each on its own tail probability) give the jury's flag count.

**Samples (random, not chosen by jury state; on-topic essays, `random_state=42` as in notebook 13):**
| Group | Definition | n |
|---|---|---|
| AI, test | every on-topic AI essay in `test` | 473 |
| AI, held-out generators | 300 random on-topic essays of the held-out generators | 300 |
| Humans, test | 300 random on-topic `test` humans (same sample as notebook 13) | 300 |
| Humans, held-out prompts | 300 random on-topic `heldout_prompt` humans (new) | 300 |
The held-out groups are descriptive.

**Attacks (same seeds as notebook 13):** typos 2%, 5%, 10% (`inject_typos`, seed 42 + position); T5 paraphrase T=1.0 and T=1.5 (seed 42, `T5Paraphraser`, spacing cleaned as in 13); T5 (T=1.0) + 5% typos. No seq2seq (not requested). All T5 texts are regenerated for the 1,373 essays together, so they are not identical to notebook 13's; the old table is shown for orientation, not as a paired comparison.

**Statistics (per group and attack), saved in `results/22b_attack_final.csv`:**
- E1 % flagged (official ensemble); E2 % flagged-or-above-usual; both for AI groups (detection) and human groups (false flag), each with a Wilson 95% interval.
- E3 mean number of jurors (of 20) flagging, before and after the attack.
- E4 *Verdict flip* (paired): among essays flagged before the attack, the share not flagged after (AI: "typos removed the flag"); among not-flagged-before humans, the share flagged after. Wilson interval. This is the number the page copy for "Re-run the trial" uses.
- E5 the old single-model numbers from notebook 13 (`results/13_attack.csv`, DistilRoBERTa at the 1% logit threshold) beside them. They apply to that threshold and model only.
- Words changed and GPT-2 fluency are not re-measured (the attacked texts are the same recipe as in 13).

**Claims audit.** New file `results/22b_claims_audit.csv` (the old audit file is not edited): rows for notebook 13's robustness figures marked "old single-model 1% threshold only", and rows for the final-system figures above.
**Wording.** Proposed README/MODEL_CARD wording on typo robustness is written in the notebook and not applied.

## Exploratory: abstention rule "flag only if the official verdict flags AND at least k of 20 jurors flag"
Exploratory everywhere it is mentioned; it does not change the official system.
- **Choosing k, on validation only.** The candidates are k = 1..20. Among validation humans the official ensemble flags, count how many have fewer than k jurors flagging (they would be demoted). Among validation AI essays the ensemble flags, count how many are demoted. **k is the smallest k for which (a) at least half of the validation students that the official verdict flags are demoted and (b) the validation AI caught falls by at most 1 percentage point (absolute).** If no k satisfies both, the whole trade-off curve (k = 1..20) is reported and no k is chosen.
- A demoted essay is shown as **above usual**, not as not flagged.
- **Caveat stated in advance.** Validation is also the calibration set of every juror and of the ensemble, and only about 5 validation students are flagged, so the choice rests on very few essays.
- **Report** (k chosen or the curve): on test, held-out prompts and held-out generators (descriptive): students flagged, AI caught, essays demoted to above usual (students and AI separately), with Wilson intervals.
