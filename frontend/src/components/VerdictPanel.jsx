import { useEffect, useId, useRef, useState } from 'react'
import styles from './VerdictPanel.module.css'
import Button from './Button'
import Popover from './Popover'
import Ruler from './Ruler'
import Segmented from './Segmented'
import { Info, Spinner } from './Icons'
import { REPO } from './Header'
import { slippedUnder } from '../lib/verdict'

/** "0.5" -> "0.5", "1.0" -> "1": the way a rate is written in a sentence */
const num = (/** @type {number} */ x) => String(+x.toFixed(1))
const label = (/** @type {string} */ s) => (s === 'strict' ? 'Strict' : 'Standard')

/** The segmented control, shared by the page header (desktop) and this panel (phone). */
export function StrictnessSwitch({ value, onChange }) {
  return <Segmented label="How strict" value={value} onChange={onChange} options={[{ value: 'strict', label: 'Strict' }, { value: 'standard', label: 'Standard' }]} />
}

/**
 * The verdict: a sentence, the ruler, and what the flag line means in numbers. One component, five stages:
 *   reading   the first 300 ms, before the model answers: spinner, empty ruler (the flag line doesn't depend on the essay)
 *   loading   still waiting after 300 ms: skeleton in the same layout, so nothing jumps
 *   done      flagged or not flagged
 * (errors are a separate panel, below). Every percentage on it comes from `meta`.
 * @param {{ stage: 'reading' | 'loading' | 'done', words: number, logit: number | null, strictness: 'strict' | 'standard', onStrictness: (v: 'strict' | 'standard') => void,
 *           meta: import('../types').Meta, exampleLabel: 'ai' | 'human' | null }} props */
export default function VerdictPanel({ stage, words, logit, strictness, onStrictness, meta, exampleLabel }) {
  const [pop, setPop] = useState(false)
  const trigger = useRef(null)
  const popId = useId()
  const threshold = meta.thresholds[strictness]
  const rates = meta.rates[strictness]
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
          <span className={styles.long}>{label(strictness)}: about {num(rates.familiar_topics_percent)}% of student essays on familiar topics cross this line. On the two topics it never saw in training, {num(rates.unseen_topics_percent)}% did, and {num(rates.worst_topic.percent)}% on the worst one ({rates.worst_topic.topic}).</span>
          <span className={styles.short}>{label(strictness)} line. {num(rates.unseen_topics_percent)}% of students crossed it on new topics.</span>
        </p>
        <div className={styles.phoneSwitch}><StrictnessSwitch value={strictness} onChange={onStrictness} /></div>
        <div className={styles.popAnchor}>
          <Button variant="quiet" ref={trigger} aria-expanded={pop} aria-controls={popId} onClick={() => setPop((o) => !o)}><Info />What is the flag line?</Button>
          <Popover id={popId} open={pop} onClose={() => setPop(false)} triggerRef={trigger} label="What is the flag line?">
            <p>The flag line is a choice, not a fact</p>
            <p>It is the score that about {num(meta.rates.strict.familiar_topics_percent)}% (strict) or {num(meta.rates.standard.familiar_topics_percent)}% (standard) of student essays reached in validation. It was set on familiar topics. On new topics, more honest essays cross it.</p>
            <a href={`${REPO}/blob/main/Notebooks/09_threshold.ipynb`}>How it was chosen (notebook 09)</a>
          </Popover>
        </div>
      </div>
      {stage === 'done' && !flagged && (
        <p className={styles.passNote}>Heavily paraphrased AI text can land here too. In testing at the standard flag line, {num(slippedUnder(meta.attacks.caught_after.t5_heavy))}% of AI essays slipped under after a heavy T5 rewrite. Not flagged is not proof of a student.</p>
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
