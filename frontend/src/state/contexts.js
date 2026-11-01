import { createContext, useContext } from 'react'

/** @typedef {{ status: 'loading' } | { status: 'ready', meta: import('../types').Meta } | { status: 'error', problem: import('../api').ApiProblem } | { status: 'mismatch', kind: 'outdated' | 'newer' }} MetaState */
/** @typedef {{ status: 'idle' | 'loading' | 'done' | 'error', data: any, problem: import('../api').ApiProblem | null }} Async */
/** @typedef {object} EssayState
 *  @property {string} text  @property {number | null} exampleId  @property {string | null} title   a file name, when the essay was opened from the class page
 *  @property {'strict' | 'standard'} strictness
 *  @property {'idle' | 'scoring' | 'scored' | 'error'} status
 *  @property {import('../types').ScoreResult | null} score  @property {string} scoredText
 *  @property {import('../api').ApiProblem | null} problem
 *  @property {Async} explain  @property {Async} attribution
 *  @property {import('../lib/fool').Attempt[]} attempts   every rewrite tried on the scored essay, oldest first
 *  @property {number | null} selected   id of the attempt shown on the Try to fool it page (null = none yet)
 *  @property {{ method: string, seed: number } | null} rewriting   a rewrite is waiting for the server
 *  @property {import('../api').ApiProblem | null} rewriteProblem */
/** @typedef {object} EssayApi
 *  @property {EssayState} state
 *  @property {(text: string) => void} setText   typing or pasting: the old score no longer describes this text
 *  @property {(example: { id: number, text: string }) => void} loadExample   loads the example and scores it at once
 *  @property {() => void} submit  @property {() => void} edit
 *  @property {(file: { name: string, text: string }) => void} openEssay   loads an essay from a class file and scores it
 *  @property {(value: 'strict' | 'standard') => void} setStrictness
 *  @property {() => void} retryExplain
 *  @property {(method: 'typos5' | 'typos10' | 't5' | 't5_heavy', seed: number) => void} rewrite   rewrites the scored essay and scores the result; the seed is kept with the attempt
 *  @property {(id: number | null) => void} selectAttempt
 *  @property {() => void} loadAttribution   the "which AI" guess is fetched the first time the drawer opens */

export const MetaContext = createContext(/** @type {{ state: MetaState, retry: () => void } | null} */ (null))
export const EssayContext = createContext(/** @type {EssayApi | null} */ (null))

export function useMetaState() {
  const ctx = useContext(MetaContext)
  if (!ctx) throw new Error('useMetaState needs <MetaProvider>')
  return ctx
}

export function useEssay() {
  const ctx = useContext(EssayContext)
  if (!ctx) throw new Error('useEssay needs <EssayProvider>')
  return ctx
}

/** @typedef {import('../lib/classStats').ClassItem} ClassItem */
/** @typedef {object} ClassApi
 *  @property {ClassItem[]} items   every file added, in the order added
 *  @property {boolean} working   files are still being sent or scored
 *  @property {string | null} notice   why things are paused (the server asked us to slow down)
 *  @property {number} reveal   bumps when the "Show" button of the could-not-be-scored toast is pressed
 *  @property {Record<string, string>} labels   the true author (human or ai) of each file, for the demo class only; empty otherwise
 *  @property {() => Promise<void>} loadDemo   adds the 30 demo essays to the class
 *  @property {(files: File[]) => void} addFiles
 *  @property {() => void} clear
 *  @property {() => void} showErrors */
export const ClassContext = createContext(/** @type {ClassApi | null} */ (null))

export function useClass() {
  const ctx = useContext(ClassContext)
  if (!ctx) throw new Error('useClass needs <ClassProvider>')
  return ctx
}
