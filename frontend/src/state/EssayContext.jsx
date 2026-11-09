import { useCallback, useEffect, useReducer, useRef } from 'react'
import * as api from '../api'
import { EssayContext } from './contexts'
import { FIRST_SEED } from '../lib/fool'

/**
 * The essay on the page and everything learned about it. One place, so the three pages (check, fool, class) agree.
 *
 *   status: idle (nothing scored) -> scoring -> scored | error
 *   explain / attribution: idle | loading | done | error   (the sentence highlights, and the "which AI" guess)
 *
 * The official verdict (three zones) comes with the score. The jury is a second request, a stream: one mark per detector as it
 * arrives. "Re-run the trial" streams a second trial on a typo version of the essay; the original trial is kept, so "Show original"
 * is instant. The essay on the page never changes.
 */

/** @typedef {import('./contexts').Async} Async */
/** @typedef {import('./contexts').EssayState} EssayState */

const idle = () => /** @type {Async} */ ({ status: 'idle', data: null, problem: null })
const KEY = 'gw-essay'
const noTrial = () => ({ start: null, marks: [], summary: null })
/** @returns {import('./contexts').JuryState} */
const noJury = () => ({ status: 'idle', running: null, original: noTrial(), rerun: null, view: 'original', runs: 0, problem: null })

/** @returns {EssayState} */
function initial() {
  /** @type {Partial<EssayState>} */
  let saved = {}
  try { saved = JSON.parse(sessionStorage.getItem(KEY) || '{}') } catch { /* private window or blocked storage: start empty */ }
  return {
    text: saved.text || '', exampleId: saved.exampleId ?? null, title: null,
    status: 'idle', score: null, scoredText: '', problem: null, explain: idle(), attribution: idle(), jury: noJury(),
    attempts: [], selected: null, rewriting: null, rewriteProblem: null,
  }
}

/** @param {EssayState} s  @param {any} a  @returns {EssayState} */
function reduce(s, a) {
  switch (a.type) {
    case 'text': return { ...s, text: a.text, exampleId: a.exampleId ?? null, title: null, status: 'idle', score: null, problem: null, explain: idle(), attribution: idle(), jury: noJury(), attempts: [], selected: null, rewriting: null, rewriteProblem: null }
    case 'scoring': return { ...s, text: a.text, exampleId: a.exampleId, title: a.title ?? null, status: 'scoring', score: null, scoredText: a.text, problem: null, explain: idle(), attribution: idle(), jury: noJury(), attempts: [], selected: null, rewriting: null, rewriteProblem: null }
    case 'scored': return { ...s, status: 'scored', score: a.score }
    case 'failed': return { ...s, status: 'error', problem: a.problem }
    case 'explain': return { ...s, explain: { status: a.status, data: a.data ?? null, problem: a.problem ?? null } }
    case 'rewriting': return { ...s, rewriting: { method: a.method, seed: a.seed }, rewriteProblem: null }
    case 'rewritten': return { ...s, rewriting: null, attempts: [...s.attempts, a.attempt], selected: a.attempt.id }
    case 'rewriteFailed': return { ...s, rewriting: null, rewriteProblem: a.problem }
    case 'juryStart': return { ...s, jury: { ...s.jury, status: 'running', running: a.which, problem: null, ...(a.which === 'original' ? { original: noTrial(), rerun: null, view: 'original' } : { rerun: { start: null, marks: s.jury.original.marks, summary: null }, view: 'rerun' }) } }   // a re-run starts from the original marks and replaces them one by one, so they travel to their new places
    case 'juryEvent': {
      const key = a.which
      const t = s.jury[key] ?? noTrial()
      const e = a.event
      const put = (/** @type {any[]} */ marks, /** @type {any} */ m) => (marks.some((x) => x.seed === m.seed) ? marks.map((x) => (x.seed === m.seed ? m : x)) : [...marks, m])
      const next = e.type === 'start' ? { ...t, start: e } : e.type === 'juror' ? { ...t, marks: put(t.marks, e) } : e.type === 'summary' ? { ...t, summary: e } : t
      return { ...s, jury: { ...s.jury, [key]: next } }
    }
    case 'juryDone': return { ...s, jury: { ...s.jury, status: 'done', running: null, runs: a.which === 'rerun' ? s.jury.runs + 1 : s.jury.runs } }
    case 'juryFailed': return { ...s, jury: { ...s.jury, status: a.problem.code === 'needs_gpu' ? 'unavailable' : 'error', running: null, problem: a.problem, ...(a.which === 'rerun' ? { rerun: null, view: 'original' } : {}) } }
    case 'juryView': return { ...s, jury: { ...s.jury, view: a.view } }
    case 'select': return { ...s, selected: a.id }
    case 'attribution': return { ...s, attribution: { status: a.status, data: a.data ?? null, problem: a.problem ?? null } }
    default: return s
  }
}

/** @param {{ children: any }} props */
export function EssayProvider({ children }) {
  const [state, dispatch] = useReducer(reduce, undefined, initial)
  const run = useRef(0)                       // each scoring gets a number; an answer for an older number is ignored
  const attempts = useRef(1)                  // numbers the attempts 1, 2, 3 ... (0 is the original essay)
  const stream = useRef(/** @type {AbortController | null} */ (null))   // the trial being read; a new essay or a new trial stops it

  useEffect(() => {
    try { sessionStorage.setItem(KEY, JSON.stringify({ text: state.text, exampleId: state.exampleId })) } catch { /* ignore */ }
  }, [state.text, state.exampleId])

  const loadExplain = useCallback(async (/** @type {string} */ text, /** @type {number} */ id) => {
    dispatch({ type: 'explain', status: 'loading' })
    try {
      const data = await api.explain(text)
      if (id === run.current) dispatch({ type: 'explain', status: 'done', data })
    } catch (problem) {
      if (id === run.current) dispatch({ type: 'explain', status: 'error', problem })
    }
  }, [])

  /** Stream one trial of the twenty detectors. `which` is 'original' or 'rerun' (typos, with a seed). An answer for an essay that has
   *  since changed is dropped; starting a trial stops the one still being read. */
  const runJury = useCallback(async (/** @type {string} */ text, /** @type {number} */ id, /** @type {'original' | 'rerun'} */ which, /** @type {number} */ seed = FIRST_SEED) => {
    stream.current?.abort()
    const controller = new AbortController()
    stream.current = controller
    dispatch({ type: 'juryStart', which })
    try {
      await api.jury(text, which === 'rerun' ? { typos: true, seed } : {}, (event) => { if (id === run.current && !controller.signal.aborted) dispatch({ type: 'juryEvent', which, event }) }, controller.signal)
      if (id === run.current && !controller.signal.aborted) dispatch({ type: 'juryDone', which })
    } catch (problem) {
      if (id === run.current && !controller.signal.aborted) dispatch({ type: 'juryFailed', which, problem })
    }
  }, [])

  const submit = useCallback(async (/** @type {string} */ text, /** @type {number | null} */ exampleId, /** @type {string | null} */ title = null) => {
    stream.current?.abort()
    const id = ++run.current
    dispatch({ type: 'scoring', text, exampleId, title })
    try {
      const score = await api.score(text)
      if (id !== run.current) return
      dispatch({ type: 'scored', score })
      if (score.verdict.zone !== 'not_flagged') loadExplain(text, id)        // highlights for flagged and above-usual essays; they come from seed 42 alone
      runJury(text, id, 'original')
    } catch (problem) {
      if (id === run.current) dispatch({ type: 'failed', problem })
    }
  }, [loadExplain, runJury])

  /** @type {import('./contexts').EssayApi} */
  const value = {
    state,
    /** typing or pasting: the old score no longer describes this text */
    setText: (/** @type {string} */ text) => { stream.current?.abort(); run.current++; dispatch({ type: 'text', text, exampleId: null }) },
    /** @param {{ id: number, text: string }} example  loads and scores it at once */
    loadExample: (example) => submit(example.text, example.id),
    submit: () => submit(state.text, state.exampleId, state.title),
    openEssay: (file) => submit(file.text, null, file.name),
    edit: () => { stream.current?.abort(); run.current++; dispatch({ type: 'text', text: state.text, exampleId: state.exampleId }) },
    /** "Re-run the trial": the same twenty detectors on a copy of the essay with typos in 5% of the words. New typos each time (seed 42, 43, ...). */
    rerunJury: () => runJury(state.scoredText, run.current, 'rerun', FIRST_SEED + state.jury.runs),
    /** back to the trial on the original essay (kept, so nothing is requested) */
    showOriginal: () => dispatch({ type: 'juryView', view: 'original' }),
    retryExplain: () => loadExplain(state.scoredText, run.current),
    /** one rewrite of the scored essay, scored again by the server. An answer for an essay that has since changed is dropped. */
    async rewrite(method, seed) {
      const id = run.current
      dispatch({ type: 'rewriting', method, seed })
      try {
        const r = await api.rewrite(state.scoredText, method, seed)
        if (id !== run.current) return
        dispatch({ type: 'rewritten', attempt: { id: attempts.current++, method, seed, edited: r.edited, wordsChanged: r.words_changed, share: r.words_changed_share, zone: r.verdict.zone, p: r.verdict.p } })
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
