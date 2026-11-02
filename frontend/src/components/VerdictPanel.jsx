import { useEffect, useId, useRef, useState } from 'react'
import styles from './VerdictPanel.module.css'
import Button from './Button'
import Popover from './Popover'
import Ruler from './Ruler'
import StrictnessSwitch from './StrictnessSwitch'
import { Info, Spinner } from './Icons'
import { REPO } from './Header'
import { passNote, popoverText, rateSentences } from '../lib/figures'

/**
 * The verdict: a sentence, the ruler, and what the flag line means in numbers. One component, five stages:
 *   reading   the first 300 ms, before the model answers: spinner, empty ruler (the flag line doesn't depend on the essay)
 *   loading   still waiting after 300 ms: skeleton in the same layout, so nothing jumps
 *   done      flagged or not flagged
 * (errors are a separate panel, below). Every percentage on it comes from `meta`.
 * @param {{ stage: 'reading' | 'loading' | 'done', words: number, logit: number | null, strictness: 'strict' | 'standard',
 *           meta: import('../types').Meta, exampleLabel: 'ai' | 'human' | null }} props */
export default function VerdictPanel({ stage, words, logit, strictness, meta, exampleLabel }) {
  const [pop, setPop] = useState(false)
  const trigger = useRef(null)
  const popId = useId()
  const threshold = meta.thresholds[strictness]
  const rate = rateSentences(meta, strictness)
  const flagged = logit != null && logit >= threshold
  const wrote = exampleLabel === 'human' ? 'This example was written by a student.' : exampleLabel === 'ai' ? 'This example was written by an AI model.' : null

  return (
    <section aria-labelledby="verdict" className={styles.panel} aria-busy={stage !== 'done'}>
      <div className={styles.top}>
        <div className={styles.headWrap} aria-live="polite">
          {stage === 'reading' && <p id="verdict" className={styles.reading}><Spinner /> Reading {words} words…</p>}
          {stage === 'loading' && <><h2 id="verdict" className="sr-only">Reading the essay</h2><div className="skel" style={{ width: '82%', height: 26 }} /><div className="skel" style={{ width: '48%', height: 26, marginTop: 10 }} /></>}
          {stage === 'done' && (
            <h2 id="verdict" className={`t-verdict ${styles.headline}`}>
              {flagged
                ? <><span className={styles.long}>Flagged. This reads like the AI essays I was trained on, but that isn’t proof.</span><span className={styles.short}>Flagged, but that isn’t proof.</span></>
                : 'Not flagged. This reads like the student essays I was trained on.'}
            </h2>
          )}
        </div>
        {stage === 'done' && wrote && <p className={`t-note ${styles.wrote}`}>{wrote}</p>}
      </div>

      <Ruler score={stage === 'done' ? logit : null} threshold={threshold} />

      <div className={styles.foot}>
        <p className={styles.rate}>
          <span className={styles.long}>{rate.long}</span>
          <span className={styles.short}>{rate.short}</span>
        </p>
        <div className={styles.phoneSwitch}><StrictnessSwitch /></div>
        <div className={styles.popAnchor}>
          <Button variant="quiet" ref={trigger} aria-expanded={pop} aria-controls={popId} onClick={() => setPop((o) => !o)}><Info />What is the flag line?</Button>
          <Popover id={popId} open={pop} onClose={() => setPop(false)} triggerRef={trigger} label="What is the flag line?">
            <p>The flag line is a choice, not a fact</p>
            <p>{popoverText(meta)}</p>
            <a href={`${REPO}/blob/main/Notebooks/09_threshold.ipynb`}>How it was chosen (notebook 09)</a>
          </Popover>
        </div>
      </div>
      {stage === 'done' && !flagged && (
        <p className={styles.passNote}>{passNote(meta)}</p>
      )}
      {stage === 'reading' && <p className={styles.passNote}>The flag line is drawn at once because it doesn't depend on the essay.</p>}
    </section>
  )
}

/** The error panel that replaces the verdict. It says what happened and what to do, keeps the essay, and uses brick (errors
 *  only, so it never reads as a verdict on the student).
 *  @param {{ problem: { title: string, detail: string }, onRetry?: () => void, onCopy?: () => void, canRetry?: boolean, retryLabel?: string }} props */
export function ErrorPanel({ problem, onRetry, onCopy, canRetry = true, retryLabel = 'Score again' }) {
  const ref = useRef(/** @type {HTMLElement | null} */ (null))
  useEffect(() => { ref.current?.focus() }, [])             // focus moves to the message, so a screen reader reads it
  return (
    <section role="alert" ref={ref} tabIndex={-1} className={`${styles.panel} ${styles.error}`}>
      <p className={styles.errorTitle}>{problem.title}</p>
      {problem.detail && <p className={styles.errorBody}>{problem.detail}</p>}
      <div className={styles.errorActions}>
        {onRetry && <Button variant="primary" disabled={!canRetry} onClick={onRetry}>{retryLabel}</Button>}
        {onCopy && <Button onClick={onCopy}>Copy essay</Button>}
      </div>
    </section>
  )
}
