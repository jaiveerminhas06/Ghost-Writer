import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import styles from './TryToFoolIt.module.css'
import AttemptsTable from '../components/AttemptsTable'
import Button from '../components/Button'
import CompareRuler from '../components/CompareRuler'
import ComparePanes from '../components/ComparePanes'
import MethodCards from '../components/MethodCards'
import { ErrorPanel } from '../components/VerdictPanel'
import { REPO } from '../components/Header'
import { useEssay, useMetaState } from '../state/contexts'
import { disagreement, FIRST_SEED, methodOf, METHODS, nextSeed, resultCopy, sidesOfTheLine } from '../lib/fool'
import { fmt, words } from '../lib/format'
import { useState } from 'react'

const COST = { typos: 'Instant', t5: 'Slower: runs the T5 model' }
const pctText = (/** @type {number} */ x) => `${+x.toFixed(1)}%`

/** Try to fool it: rewrite the essay (typos or a paraphrase), score it again, and see what moved. */
export default function TryToFoolIt() {
  const { state, retry } = useMetaState()
  if (state.status === 'loading') return <div className="wrap" style={{ padding: '56px 0' }} aria-busy="true"><div className="skel" style={{ height: 56, width: '50%' }} /></div>
  if (state.status === 'error') return <div className="wrap" style={{ padding: '56px 0' }}><ErrorPanel problem={state.problem} onRetry={retry} /></div>
  return <Loaded meta={state.meta} />
}

/** @param {{ meta: import('../types').Meta }} props */
function Loaded({ meta }) {
  const essay = useEssay()
  const { state } = essay
  const [method, setMethod] = useState('typos5')

  // arriving with an essay typed but not scored (for example after a reload): score it, so there is a "before"
  const started = useRef(false)
  useEffect(() => {
    if (started.current || state.status !== 'idle') return
    if (words(state.text).length >= meta.limits.min_words) { started.current = true; essay.submit() }
  }, [state.status, state.text, meta, essay])

  const score = state.status === 'scored' ? state.score : null
  const example = meta.examples.find((x) => x.id === state.exampleId) ?? null

  if (!score) {
    return (
      <div className={`wrap ${styles.page}`}>
        <h1 className="t-display">Try to fool it</h1>
        {state.status === 'scoring'
          ? <p className={styles.lede} role="status" aria-busy="true">Scoring the essay first…</p>
          : <p className={styles.lede}>There is no essay to rewrite yet. <Link to="/">Check an essay</Link> first, then come back to see what a few edits do to its score.</p>}
      </div>
    )
  }

  const strictness = state.strictness
  const threshold = meta.thresholds[strictness]
  const attempts = state.attempts
  const shown = attempts.find((a) => a.id === state.selected) ?? null
  const ran = attempts.some((a) => a.method === method)
  const busy = state.rewriting !== null
  const kind = methodOf(method).kind
  const t5Missing = !meta.t5_available
  const seed = nextSeed(attempts, method)
  const sides = sidesOfTheLine(attempts, method, threshold)
  const copy = shown ? resultCopy({ method: shown.method, before: score.logit, after: shown.logit, wordsChanged: shown.wordsChanged, thresholds: meta.thresholds, strictness }) : null
  const flagText = (/** @type {number} */ x) => (x >= threshold ? 'flagged' : 'not flagged')
  const atk = meta.attacks

  const cards = METHODS.map((m) => {
    const last = [...attempts].reverse().find((a) => a.method === m.id)
    const desc = {
      typos5: 'Swaps, drops or doubles a letter in about one word in twenty. Meaning stays; spelling gets worse.',
      typos10: `One word in ten. In testing, ${pctText(atk.caught_after.typos10)} of AI essays were still caught.`,
      t5: `Rewrites each sentence with a pretrained paraphraser. In testing it changed about ${Math.round(atk.words_changed_percent.t5)}% of the words and ${pctText(atk.caught_after.t5)} of AI essays were still caught. Check the result still says what the student meant.`,
      t5_heavy: `Rewrites about ${Math.round(atk.words_changed_percent.t5_heavy)}% of the words. The rewrite that moved the most verdicts in notebook 13: ${pctText(atk.caught_after.t5_heavy)} of AI essays were still caught, down from ${pctText(atk.caught_after.original)}.`,
    }[m.id]
    return {
      id: m.id, title: m.title, cost: COST[m.kind], desc: desc ?? '', muted: !last,
      result: last ? `Last run: ${fmt(score.logit)} to ${fmt(last.logit)}` : 'Not run on this essay',
      unavailable: m.kind === 't5' && t5Missing ? "Paraphrasing needs the T5 model, which isn't loaded on this machine. Typos still work." : undefined,
    }
  })

  const run = () => essay.rewrite(/** @type {any} */ (method), seed)
  const again = kind === 'typos' ? 'Try different typos' : 'Try a different paraphrase'

  return (
    <div className={`wrap ${styles.page}`}>
      <div className={styles.top}>
        <div className={styles.intro}>
          <h1 className="t-display">Try to fool it</h1>
          <p className={styles.lede}>Rewrite the essay and score it again. On a student essay, this shows the other side of the problem: changes that add nothing can flip the answer.</p>
        </div>
        <p className={styles.about}>Rewriting <Link to="/">{example ? example.name : 'your essay'}</Link>, {score.words} words, {strictness} flag line at {fmt(threshold)}.</p>
      </div>

      <section aria-labelledby="method" className={styles.method}>
        <h2 id="method" className="t-heading">Rewrite with</h2>
        <div className={styles.methodRow}>
          <div className={styles.cards}>
            <MethodCards label="Rewrite method" methods={cards} value={method} onChange={setMethod} />
          </div>
          <div className={styles.go}>
            <Button variant="primary" className={styles.goButton} busy={busy} disabled={ran || (kind === 't5' && t5Missing)} onClick={run}>{busy ? 'Rewriting…' : 'Rewrite and re-score'}</Button>
            {ran && !busy && <Button onClick={run}>{again}</Button>}
            <p className={styles.small}>{ran ? `Seed ${seed} is new for this method; the first run used seed ${FIRST_SEED}.` : 'Every run is kept in the list below.'}</p>
          </div>
        </div>
      </section>

      {state.rewriteProblem && <ErrorPanel problem={state.rewriteProblem} onRetry={run} />}

      <section aria-labelledby="result" className={styles.result} aria-live="polite">
        <div className={styles.resultHead}>
          <div className={styles.resultText}>
            {busy ? <h2 id="result" className="t-verdict">Rewriting and scoring…</h2>
              : copy ? <><h2 id="result" className="t-verdict">{copy.headline}</h2><p>{copy.body}</p></>
                : <><h2 id="result" className="t-section">Pick a rewrite, then press Rewrite and re-score.</h2><p>The essay scores {fmt(score.logit)} against a {strictness} flag line of {fmt(threshold)}. Its score will be marked here, and each new score beside it.</p></>}
          </div>
          {shown && !busy && (
            <dl className={styles.facts}>
              <dt>Score</dt><dd>{fmt(score.logit)} to {fmt(shown.logit)} <span>({fmt(shown.logit - score.logit)})</span></dd>
              <dt>Words changed</dt><dd>{shown.wordsChanged} of {score.words} <span>({Math.round(shown.share * 100)}%)</span></dd>
              <dt>Meaning</dt><dd>{methodOf(shown.method).kind === 'typos' ? 'Unchanged, spelling worse' : 'Not checked: read it'}</dd>
            </dl>
          )}
        </div>
        <CompareRuler before={score.logit} after={shown && !busy ? shown.logit : null} threshold={threshold} flagLabel="Flag line" strictness={strictness} />
      </section>

      {shown && (
        <section aria-labelledby="compare" className={styles.compare}>
          <div className={styles.compareHead}>
            <h2 id="compare" className="t-section">What changed</h2>
            <p className={styles.small}>The two pages scroll together. Changed words are underlined.</p>
          </div>
          <ComparePanes original={state.scoredText} edited={shown.edited}
                        left={{ title: 'Original', score: `${fmt(score.logit)}, ${flagText(score.logit)}` }}
                        right={{ title: methodOf(shown.method).title, score: `${fmt(shown.logit)}, ${flagText(shown.logit)}` }} />
        </section>
      )}

      <div className={styles.bottom}>
        <section aria-labelledby="attempts" className={styles.attempts}>
          <h2 id="attempts" className="t-section">Attempts on this essay</h2>
          {sides && <p className={styles.sides}>{disagreement(sides, method)}</p>}
          <AttemptsTable attempts={attempts} original={score.logit} selected={state.selected} threshold={threshold} words={score.words} onSelect={essay.selectAttempt} />
        </section>
        <aside aria-labelledby="tested" className={styles.tested}>
          <h2 id="tested" className="t-heading">{Math.abs(score.logit - threshold) < 2 ? 'This essay was borderline' : 'What the tests found'}</h2>
          <p>Across the test set, rewriting rarely saved an AI essay, and it hurt honest ones:</p>
          <ul>
            <li>With typos in 10% of words, {pctText(atk.caught_after.typos10)} of AI essays were still caught.</li>
            <li>After heavy T5 paraphrasing, {pctText(atk.caught_after.t5_heavy)} were.</li>
            <li>A light T5 paraphrase raised the flag rate of student essays from {pctText(atk.humans_flagged.original)} to {pctText(atk.humans_flagged.t5)}.</li>
          </ul>
          <p className={styles.small}>Measured at the standard flag line.</p>
          <a href={`${REPO}/blob/main/Notebooks/13_attack.ipynb`}>The full attack results (notebook 13)</a>
        </aside>
      </div>
    </div>
  )
}
