// The shapes of everything the API returns (api/main.py, api/results.py). The type checker (npm run typecheck) holds
// the rest of the code to these, so a renamed field is caught before the page breaks.

/** @typedef {{ topic: string, percent: number }} WorstTopic */
/** @typedef {{ unseen_topics_percent: number, worst_topic: WorstTopic, familiar_topics_percent: number }} Rates */
/** @typedef {{ id: number, name: string, label: 'ai' | 'human', words: number, text: string }} Example */
/**
 * GET /api/meta: everything the page needs before any essay. Every figure comes from a results file on the server.
 * @typedef {object} Meta
 * @property {{ strict: number, standard: number }} thresholds   flag lines, on the score scale
 * @property {{ strict: Rates, standard: Rates }} rates
 * @property {{ threshold: string, caught_after: Record<string, number>, humans_flagged: Record<string, number>, words_changed_percent: Record<string, number> }} attacks   keys: original (before any rewrite), typos5, typos10, t5, t5_heavy
 * @property {number} trained_on
 * @property {{ min_words: number, max_chars: number, max_tokens: number, max_files: number, file_types: string[] }} limits
 * @property {boolean} t5_available
 * @property {Example[]} examples
 */

/**
 * POST /api/score
 * @typedef {object} ScoreResult
 * @property {number} logit        the score: higher means more AI-like
 * @property {number} words
 * @property {number} tokens
 * @property {number} tokens_read  at most 512
 * @property {boolean} truncated
 * @property {number} read_chars   character index where reading stopped (the text's length if it read everything)
 */

/** @typedef {{ start: number, end: number, score: number | null }} SentenceScore   score is null beyond the part read */
/** @typedef {{ method: 'occlusion' | 'integrated_gradients', list_truncated: boolean, sentences: SentenceScore[] }} ExplainResult */
/** @typedef {{ families: { family: string, share: number }[], heldout_accuracy: string }} AttributionResult */
/** @typedef {ScoreResult & { method: string, edited: string, words_changed: number, words_changed_share: number }} RewriteResult */
/** @typedef {{ name: string, words: number | null, logit: number | null, text: string | null, error: { code: string, message: string } | null }} BatchItem */

/** @typedef {{ code: string, message: string }} ApiProblem */
export {}
