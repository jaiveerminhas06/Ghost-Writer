// The shapes of everything the API returns (api/main.py, api/results.py). The type checker (npm run typecheck) holds
// the rest of the code to these, so a renamed field is caught before the page breaks.

/** @typedef {'flagged' | 'above_usual' | 'not_flagged'} Zone */
/** @typedef {{ id: number, name: string, label: 'ai' | 'human', kind: string, note: string | null, words: number, text: string }} Example   kind: example, final_system_wrong or split_jury */
/** @typedef {{ value: number, lo: number, hi: number }} Interval   a fraction between 0 and 1 with its 95% interval */
/** @typedef {{ zone: Zone, p: number, seeds: { seed: number, p: number, zone: Zone }[], explained_by: string }} Verdict   the official verdict: the three-seed ensemble. p is the share of student essays that score this high or higher. */
/** @typedef {{ min: number, above_usual_line: number, flag_line: number, cap: number, val_humans: number, tau_flag: number, tau_above_usual: number }} Scale   positions are -log10 p; the scale ends at cap */
/** @typedef {{ flagged: number, flagged_lo: number, flagged_hi: number, flagged_or_above: number, above_usual: number, flip: number, flip_k: number, flip_of: number, flip_to_above_usual: number, flip_to_not_flagged: number, jurors_flagging_before: number, jurors_flagging_after: number, words_changed: number }} AttackFigures   fractions; notebook 22b */
/**
 * GET /api/meta: everything the page needs before any essay. Every figure comes from a results file on the server. The `official` and `jury`
 * blocks (fractions between 0 and 1) describe the final system; `thresholds`, `rates` and `attacks` are the older single-model blocks and the
 * page no longer quotes them.
 * @typedef {object} Meta
 * @property {number} api_version   which version of the API this is; the page checks it against the one it was built for
 * @property {number} trained_on
 * @property {{ min_words: number, max_chars: number, max_tokens: number, max_files: number, max_file_bytes: number, file_types: string[] }} limits
 * @property {boolean} t5_available
 * @property {Example[]} examples
 * @property {{ id: string, name: string, essays: number, human: number, ai: number }[]} [demo_classes]   the demo classes on the Check a class page, one per held-out topic
 * @property {{ students_unseen_topics: { n: number, flagged: Interval, above_usual: Interval, by_topic: Record<string, { n: number, flagged: Interval }> },
 *   ai_unseen_generators: { n: number, flagged: Interval, above_usual: Interval }, ai_unseen_prompts: { n: number, flagged: Interval },
 *   p_ai_given_zone: Record<string, Record<string, Interval>> }} official   notebook 20
 * @property {{ api: number, live: boolean, jurors: number, ensemble_seeds: number[], typo_rate: number, scale: Scale, statistics: any,
 *   attacks_final: Record<string, { n: number, descriptive: boolean, attacks: Record<string, AttackFigures> }> }} jury   notebooks 22 and 22b; live is false on a server without a GPU
 */

/**
 * POST /api/score
 * @typedef {object} ScoreResult
 * @property {number} logit        seed 42's score (the highlights explain this one); the verdict is `verdict`
 * @property {Verdict} verdict
 * @property {number} words
 * @property {number} tokens
 * @property {number} tokens_read  at most 512
 * @property {boolean} truncated
 * @property {number} read_chars   character index where reading stopped (the text's length if it read everything)
 */

/** @typedef {{ seed: number, p: number, position: number, zone: Zone, at_cap: boolean, ensemble_member: boolean }} JurorMark */
/** @typedef {{ type: 'start', jurors: number, words: number, typos: { rate: number, seed: number, words_changed: number, words_changed_share: number, requested_seed?: number } | null, scale: Scale, precomputed: boolean, truncated: boolean, tokens_read: number }} JuryStart */
/** @typedef {{ type: 'summary', jurors: number, counts: Record<Zone, number>, official: { zone: Zone, p: number, seeds: any[] }, jurors_changed_zone?: number, official_changed?: boolean, before?: { counts: Record<Zone, number>, official: { zone: Zone, p: number } } }} JurySummary */

/** @typedef {{ start: number, end: number, score: number | null }} SentenceScore   score is null beyond the part read */
/** @typedef {{ method: 'occlusion' | 'integrated_gradients', list_truncated: boolean, sentences: SentenceScore[] }} ExplainResult */
/** @typedef {{ families: { family: string, share: number }[], heldout_accuracy: string }} AttributionResult */
/** @typedef {ScoreResult & { method: string, edited: string, words_changed: number, words_changed_share: number }} RewriteResult */
/** @typedef {{ name: string, words: number | null, logit: number | null, verdict?: { zone: Zone, p: number }, jurors_flagging?: number | null, text: string | null, error: { code: string, message: string } | null }} BatchItem */

/** @typedef {{ code: string, message: string }} ApiProblem */
export {}
