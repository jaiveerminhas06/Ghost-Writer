import { useEffect, useId, useMemo, useRef, useState } from 'react'
import styles from './VerdictPanel.module.css'
import Button from './Button'
import JuryScale from './JuryScale'
import { Spinner } from './Icons'
import { authorSentence, disagree, DISAGREE_SENTENCE, headline, jurySummary, markText, rerunFigures, rerunLead, SAME_SENTENCE, whyText } from '../lib/jury'
import { oneIn, scoreWords, ZONE_WORD } from '../lib/scale'

const DOT = { flagged: 'flag', above_usual: 'above', not_flagged: 'not' }

/** One row of twenty small marks, coloured by zone: the jury before and after the typos. @param {{ counts: Record<string, number>, label: string }} props */
function Waffle({ counts, label }) {
  const zones = [...Array(counts.flagged).fill('flagged'), ...Array(counts.above_usual).fill('above_usual'), ...Array(counts.not_flagged).fill('not_flagged')]
  return (
    <svg className={styles.waffle} viewBox={`0 0 ${zones.length * 17} 18`} role="img" aria-label={label}>
      {zones.map((z, i) => <circle key={i} cx={8 + i * 17} cy="9" r="6" className={styles[DOT[z]]} />)}
    </svg>
  )
}

/** The verdict: a sentence, the scale (the official verdict on top, the twenty detectors hanging under it), what the marks mean, what the
 *  jury says, and "Re-run the trial". Stages: reading (the first 300 ms), loading (a skeleton after that), done. While the detectors answer,
 *  their marks drop in one by one; the official marker lands last and the sentence fades in with it. If the live jury is not available
 *  (a server without a GPU, an essay that is not a built-in example) the official verdict is still shown, with the reason.
 *  @param {{ stage: 'reading' | 'loading' | 'done', words: number, score: import('../types').ScoreResult | null, jury: import('../state/contexts').JuryState,
 *    meta: import('../types').Meta, example: import('../types').Example | null, onRerun: () => void, onShowOriginal: () => void }} props */
export default function VerdictPanel({ stage, words, score, jury, meta, example, onRerun, onShowOriginal }) {
  const scale = meta.jury.scale
  const [act, setAct] = useState(/** @type {{ view: string, seed: number | null }} */ ({ view: 'original', seed: null }))
  const active = act.view === jury.view ? act.seed : null          // the highlighted mark belongs to the view it was chosen in
  const setActive = (/** @type {number | null} */ seed) => setAct({ view: jury.view, seed })
  const listId = useId()
  const rerunShown = jury.view === 'rerun' && jury.rerun !== null
  const trial = rerunShown ? /** @type {import('../state/contexts').Trial} */ (jury.rerun) : jury.original
  const running = jury.status === 'running'
  const jurorsDown = jury.status === 'error' || jury.status === 'unavailable'
  const summary = trial.summary
  const verdict = summary ? summary.official : jurorsDown && score ? score.verdict : null        // the official marker lands once the jury has answered
  const marks = trial.marks
  const activeMark = marks.find((m) => m.seed === active)
  const wrote = example?.note ?? (example ? (example.label === 'human' ? 'This example was written by a student.' : 'This example was written by an AI model.') : null)
  const typos = trial.start?.typos ?? null
  const label = verdict
    ? `The official verdict is ${ZONE_WORD[verdict.zone].toLowerCase()}: ${scoreWords(verdict.p, scale.val_humans)}. ${summary ? jurySummary(summary) : ''}`
    : 'Scale of how many student essays score this high or higher, with the marks of the twenty detectors.'
  const rows = useMemo(() => [...marks].sort((a, b) => a.seed - b.seed), [marks])

  // the sentence changes when the verdict does; the page announces the summary sentence, not the whole panel
  const rr = rerunShown && summary && typos && summary.before
    ? { lead: rerunLead({ words, wordsChanged: typos.words_changed, changed: summary.jurors_changed_zone ?? 0, jurors: summary.jurors, before: summary.before.official.zone, after: summary.official.zone }),
        author: authorSentence(example ? example.label : null, summary.before.official.zone, summary.official.zone), general: rerunFigures(meta) }
    : null

  return (
    <section aria-labelledby="verdict" className={styles.panel} aria-busy={stage !== 'done' || running}>
      <div className={styles.top}>
        <div className={styles.headWrap}>
          {stage === 'reading' && <p id="verdict" className={styles.reading}><Spinner /> Reading {words} words…</p>}
          {stage === 'loading' && <><h2 id="verdict" className="sr-only">Reading the essay</h2><div className="skel" style={{ width: '82%', height: 26 }} /><div className="skel" style={{ width: '48%', height: 26, marginTop: 10 }} /></>}
          {stage === 'done' && !verdict && running && <p id="verdict" className={styles.reading} role="status"><Spinner /> {jury.running === 'rerun' ? 'Asking the 20 detectors again…' : 'Asking the 20 detectors…'}</p>}
          {stage === 'done' && verdict && (
            <h2 id="verdict" key={`${jury.view}-${verdict.zone}-${rerunShown ? typos?.seed : 0}`} className={`t-verdict ${styles.headline} ${verdict.zone === 'above_usual' ? styles.long : ''}`}>
              {headline(verdict.zone, verdict.p, meta, rerunShown)}
            </h2>
          )}
        </div>
        {stage === 'done' && wrote && <p className={`t-note ${styles.wrote}`}>{wrote}</p>}
      </div>

      {stage === 'done' && rerunShown && (
        <div className={styles.banner}>
          <p>{typos ? `Showing the essay with typos in ${typos.words_changed} of ${words} words (seed ${typos.seed}${typos.requested_seed !== undefined && typos.requested_seed !== typos.seed ? `; stored run, you asked for ${typos.requested_seed}` : ''}). The essay below is still the original.` : 'Showing the essay with typos. The essay below is still the original.'}</p>
          <Button onClick={onShowOriginal}>Show original</Button>
        </div>
      )}

      {stage === 'done' && (
        <>
          <JuryScale scale={scale} marks={marks} official={verdict ? { p: verdict.p } : null} activeSeed={active} onActive={setActive} label={label} />
          <p className={styles.axisCaption}>How many student essays score this high or higher<span className={styles.sub}> (of the {scale.val_humans.toLocaleString('en-US')} we checked)</span></p>
          <p className={`${styles.detail} num`} aria-hidden="true">{activeMark ? markText(activeMark, scale.val_humans) : (marks.length ? 'Hover or focus a mark to read it. Arrow keys move between the 20.' : '')}</p>
          <ul className={styles.legend}>
            <li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="7" className={styles.flag} /></svg>Flagged</li>
            <li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="7" className={styles.above} /></svg>Above usual</li>
            <li><svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="7" className={styles.not} /></svg>Not flagged</li>
            <li><svg width="22" height="22" aria-hidden="true"><circle cx="11" cy="11" r="6.5" className={styles.flag} /><circle cx="11" cy="11" r="9.7" className={styles.ens} /></svg>One of the three detectors in the official verdict</li>
          </ul>
        </>
      )}

      {stage === 'done' && jury.problem && jurorsDown && (
        <p className={styles.note} role="status">{jury.problem.title} {jury.problem.detail}</p>
      )}

      {stage === 'done' && summary && (
        <div className={styles.jury}>
          <p className={styles.sentence} aria-live="polite"><strong>{jurySummary(summary)}</strong> {SAME_SENTENCE}</p>
          {disagree(summary.counts) && <p className={styles.disagree}>{DISAGREE_SENTENCE}</p>}
          {trial.start?.truncated && <p className={styles.small}>The detectors read the first {trial.start.tokens_read} tokens of this essay.</p>}
        </div>
      )}

      {stage === 'done' && marks.length > 0 && (
        <details className={styles.fold}>
          <summary>The 20 marks as a list</summary>
          <table className={styles.table} id={listId}>
            <thead><tr><th scope="col">Detector</th><th scope="col">Verdict</th><th scope="col">Student essays that score this high or higher</th></tr></thead>
            <tbody>{rows.map((m) => (
              <tr key={m.seed}><th scope="row">{m.seed}{m.ensemble_member ? ' (in the official verdict)' : ''}</th><td>{ZONE_WORD[m.zone]}</td><td className="num">{oneIn(m.p, scale.val_humans)}</td></tr>
            ))}</tbody>
          </table>
        </details>
      )}

      {stage === 'done' && (
        <details className={styles.fold}>
          <summary>Why 20 detectors?</summary>
          <p>{whyText(meta)}</p>
        </details>
      )}

      {stage === 'done' && rr && (
        <section className={styles.rerun} aria-labelledby="rerun-h">
          <h3 id="rerun-h" className={styles.rerunHead}>{rr.lead}</h3>
          {rr.author && <p>{rr.author}</p>}
          <p className={styles.row}><span className={styles.k}>Before</span><Waffle counts={summary?.before?.counts ?? { flagged: 0, above_usual: 0, not_flagged: 0 }} label={`Before the typos: ${summary?.before?.counts.flagged} flagged`} /><span className={styles.v}>{summary?.before?.counts.flagged} flag</span></p>
          <p className={styles.row}><span className={styles.k}>After</span><Waffle counts={summary?.counts ?? { flagged: 0, above_usual: 0, not_flagged: 0 }} label={`After the typos: ${summary?.counts.flagged} flagged`} /><span className={styles.v}>{summary?.counts.flagged} flag</span></p>
          {rr.general && <p className={styles.general}>{rr.general}</p>}
        </section>
      )}

      {stage === 'done' && (
        <div className={styles.rerunBar}>
          <Button busy={running && jury.running === 'rerun'} disabled={running || jury.status === 'unavailable'} onClick={onRerun}>{running && jury.running === 'rerun' ? 'Re-running…' : 'Re-run the trial'}</Button>
          <p className={styles.small}>{rerunShown ? 'New typos each time. Different seeds give different results.' : 'Adds typos to 5% of the words and asks the same 20 detectors again.'}</p>
        </div>
      )}
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
