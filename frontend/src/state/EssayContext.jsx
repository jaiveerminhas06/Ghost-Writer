import { useCallback, useEffect, useReducer, useRef } from 'react'
import * as api from '../api'
import { EssayContext } from './contexts'

/**
 * The essay on the page and everything learned about it. One place, so the three pages (check, fool, class) agree.
 *
 *   status: idle (nothing scored) -> scoring -> scored | error
 *   explain / attribution: idle | loading | done | error   (the sentence highlights, and the "which AI" guess)
 *
 * Strict / Standard is deliberately not a request: the server returns the score, and the page compares it with the flag line
 * for the chosen setting. So `strictness` is plain state here.
 */

/** @typedef {import('./contexts').Async} Async */
/** @typedef {import('./contexts').EssayState} EssayState */

const idle = () => /** @type {Async} */ ({ status: 'idle', data: null, problem: null })
const KEY = 'gw-essay'

/** @returns {EssayState} */
function initial() {
  /** @type {Partial<EssayState>} */
  let saved = {}
  try { saved = JSON.parse(sessionStorage.getItem(KEY) || '{}') } catch { /* private window or blocked storage: start empty */ }
  return {
    text: saved.text || '', exampleId: saved.exampleId ?? null, title: null, strictness: saved.strictness === 'standard' ? 'standard' : 'strict',
    status: 'idle', score: null, scoredText: '', problem: null, explain: idle(), attribution: idle(),
    attempts: [], selected: null, rewriting: null, rewriteProblem: null,
  }
}

/** @param {EssayState} s  @param {any} a  @returns {EssayState} */
function reduce(s, a) {
  switch (a.type) {
    case 'text': return { ...s, text: a.text, exampleId: a.exampleId ?? null, title: null, status: 'idle', score: null, problem: null, explain: idle(), attribution: idle(), attempts: [], selected: null, rewriting: null, rewriteProblem: null }
    case 'strictness': return { ...s, strictness: a.value }
    case 'scoring': return { ...s, text: a.text, exampleId: a.exampleId, title: a.title ?? null, status: 'scoring', score: null, scoredText: a.text, problem: null, explain: idle(), attribution: idle(), attempts: [], selected: null, rewriting: null, rewriteProblem: null }
    case 'scored': return { ...s, status: 'scored', score: a.score }
    case 'failed': return { ...s, status: 'error', problem: a.problem }
    case 'explain': return { ...s, explain: { status: a.status, data: a.data ?? null, problem: a.problem ?? null } }
    case 'rewriting': return { ...s, rewriting: { method: a.method, seed: a.seed }, rewriteProblem: null }
    case 'rewritten': return { ...s, rewriting: null, attempts: [...s.attempts, a.attempt], selected: a.attempt.id }
    case 'rewriteFailed': return { ...s, rewriting: null, rewriteProblem: a.problem }
    case 'select': return { ...s, selected: a.id }
    case 'attribution': return { ...s, attribution: { status: a.status, data: a.data ?? null, problem: a.problem ?? null } }
    default: return s
  }
}

/** @param {{ children: any, lowestFlagLine: number | null }} props  lowestFlagLine: highlights are fetched for any essay flagged in at least one setting */
export function EssayProvider({ children, lowestFlagLine }) {
  const [state, dispatch] = useReducer(reduce, undefined, initial)
  const run = useRef(0)                       // each scoring gets a number; an answer for an older number is ignored
  const attempts = useRef(1)                  // numbers the attempts 1, 2, 3 ... (0 is the original essay)

  useEffect(() => {
    try { sessionStorage.setItem(KEY, JSON.stringify({ text: state.text, exampleId: state.exampleId, strictness: state.strictness })) } catch { /* ignore */ }
  }, [state.text, state.exampleId, state.strictness])

  const loadExplain = useCallback(async (/** @type {string} */ text, /** @type {number} */ id) => {
    dispatch({ type: 'explain', status: 'loading' })
    try {
      const data = await api.explain(text)
      if (id === run.current) dispatch({ type: 'explain', status: 'done', data })
    } catch (problem) {
      if (id === run.current) dispatch({ type: 'explain', status: 'error', problem })
    }
  }, [])

  const submit = useCallback(async (/** @type {string} */ text, /** @type {number | null} */ exampleId, /** @type {string | null} */ title = null) => {
    const id = ++run.current
    dispatch({ type: 'scoring', text, exampleId, title })
    try {
      const score = await api.score(text)
      if (id !== run.current) return
      dispatch({ type: 'scored', score })
      if (lowestFlagLine != null && score.logit >= lowestFlagLine) loadExplain(text, id)
    } catch (problem) {
      if (id === run.current) dispatch({ type: 'failed', problem })
    }
  }, [lowestFlagLine, loadExplain])

  /** @type {import('./contexts').EssayApi} */
  const value = {
    state,
    /** typing or pasting: the old score no longer describes this text */
    setText: (/** @type {string} */ text) => { run.current++; dispatch({ type: 'text', text, exampleId: null }) },
    /** @param {{ id: number, text: string }} example  loads and scores it at once */
    loadExample: (example) => submit(example.text, example.id),
    submit: () => submit(state.text, state.exampleId, state.title),
    openEssay: (file) => submit(file.text, null, file.name),
    edit: () => { run.current++; dispatch({ type: 'text', text: state.text, exampleId: state.exampleId }) },
    setStrictness: (/** @type {'strict' | 'standard'} */ value) => dispatch({ type: 'strictness', value }),
    retryExplain: () => loadExplain(state.scoredText, run.current),
    /** one rewrite of the scored essay, scored again by the server. An answer for an essay that has since changed is dropped. */
    async rewrite(method, seed) {
      const id = run.current
      dispatch({ type: 'rewriting', method, seed })
      try {
        const r = await api.rewrite(state.scoredText, method, seed)
        if (id !== run.current) return
        dispatch({ type: 'rewritten', attempt: { id: attempts.current++, method, seed, edited: r.edited, wordsChanged: r.words_changed, share: r.words_changed_share, logit: r.logit } })
      } catch (problem) {
        if (id === run.current) dispatch({ type: 'rewriteFailed', problem })
      }
    },
    selectAttempt: (id) => dispatch({ type: 'select', id }),
    /** the "which AI" guess is fetched the first time the drawer opens, not for every flagged essay */
    async loadAttribution() {
      if (state.attribution.status === 'loading' || state.attribution.status === 'done') return
      const id = run.current
      dispatch({ type: 'attribution', status: 'loading' })
      try {
        const data = await api.attribution(state.scoredText)
        if (id === run.current) dispatch({ type: 'attribution', status: 'done', data })
      } catch (problem) {
        if (id === run.current) dispatch({ type: 'attribution', status: 'error', problem })
      }
    },
  }
  return <EssayContext.Provider value={value}>{children}</EssayContext.Provider>
}
