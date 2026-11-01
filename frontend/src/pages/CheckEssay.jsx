import { useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import styles from './CheckEssay.module.css'
import Button from '../components/Button'
import { EssayEditor, EssayReader } from '../components/EssayPaper'
import ExampleList from '../components/ExampleList'
import VerdictPanel, { ErrorPanel, StrictnessSwitch } from '../components/VerdictPanel'
import WhichAi from '../components/WhichAi'
import { useEssay, useMetaState } from '../state/contexts'
import { useDelayed } from '../lib/useDelayed'
import { legend } from '../lib/tiers'
import { marginNotes } from '../lib/notes'
import { useToast } from '../lib/toast'
import { ApiProblem } from '../api'

/** Problems the visitor fixes by editing the essay, so "Score again" would only repeat the refusal. */
const NEEDS_EDIT = new Set(['not_english', 'too_short', 'too_long'])

/** Check an essay: pick an example or paste an essay, read the verdict on the ruler, and see which sentences moved it. */
export default function CheckEssay() {
  const { state, retry } = useMetaState()
  if (state.status === 'loading') return <div className="wrap" style={{ padding: '56px 0' }} aria-busy="true"><div className="skel" style={{ height: 56, width: '50%' }} /></div>
  if (state.status === 'error') {
    return (
      <div className="wrap" style={{ padding: '56px 0' }}>
        <ErrorPanel problem={state.problem} onRetry={retry} />
      </div>
    )
  }
  return <Loaded meta={state.meta} />
}

/** @param {{ meta: import('../types').Meta }} props */
function Loaded({ meta }) {
  const essay = useEssay()
  const { state } = essay
  const toast = useToast()
  const [params] = useSearchParams()

  // ?example=0|1|2 opens with that example scored (handy for links and screenshots)
  const asked = useRef(false)
  useEffect(() => {
    if (asked.current) return
    asked.current = true
    const e = meta.examples.find((x) => String(x.id) === params.get('example'))
    if (e) essay.loadExample(e)
  }, [meta, params, essay])

  const scoring = state.status === 'scoring'
  const skeleton = useDelayed(scoring, 300)
  const score = state.status === 'scored' ? state.score : null
  const scored = score !== null
  const threshold = meta.thresholds[state.strictness]
  const flagged = score !== null && score.logit >= threshold
  const example = meta.examples.find((x) => x.id === state.exampleId) ?? null
  const explain = flagged && state.explain.status === 'done' ? state.explain.data : null
  const reading = scoring || scored
  const wordsNow = state.scoredText.trim().split(/\s+/).filter(Boolean).length
  const problem = state.status === 'error' ? state.problem : null
  const blocked = problem && NEEDS_EDIT.has(problem.code) ? problem.title : null

  const copyText = async () => {
    try { await navigator.clipboard.writeText(state.text); toast.show({ message: 'Essay copied.' }) }
    catch { toast.show({ kind: 'error', message: "Couldn't copy. Select the text and copy it yourself." }) }
  }
  const hasMarks = !!explain && marginNotes(explain.sentences, explain.method).length > 0

  return (
    <div className={`wrap ${styles.page}`}>
      <section className={styles.intro} aria-label="Introduction">
        <div className={styles.lede}>
          <h1 className="t-display">Did a student or an AI write this essay?</h1>
          <p className={styles.long}>Paste an essay or load an example. The detector compares it with the {meta.trained_on.toLocaleString('en-US')} essays it was trained on and says which side of its flag line it falls.</p>
          <p className={styles.course}>A course project for CSE472. Don’t use it to judge real students.</p>
        </div>
        <div className={styles.controls}>
          <ExampleList examples={meta.examples} value={state.exampleId} onChange={essay.loadExample} />
          <div className={styles.strictRow}>
            <p id="strictness" className={styles.strictLabel}>How strict</p>
            <StrictnessSwitch value={state.strictness} onChange={essay.setStrictness} />
          </div>
        </div>
      </section>

      {reading && (
        <VerdictPanel stage={scoring ? (skeleton ? 'loading' : 'reading') : 'done'} words={wordsNow} logit={score ? score.logit : null}
                      strictness={state.strictness} onStrictness={essay.setStrictness} meta={meta} exampleLabel={example ? example.label : null} />
      )}
      {problem && (
        <ErrorPanel problem={problem} onCopy={blocked ? undefined : copyText} onRetry={essay.submit} canRetry={!blocked} retryLabel={blocked ? 'Score essay' : 'Score again'} />
      )}

      <div className={styles.bench}>
        <div className={styles.paper}>
          {reading ? (
            scored
              ? (
                <>
                  <EssayReader key={state.scoredText} text={state.scoredText} title={example ? example.name : 'Your essay'}
                               scoreInfo={score} explain={explain} onEdit={essay.edit} />
                  {flagged && state.explain.status === 'loading' && <p className={styles.status} role="status">Finding the sentences I reacted to…</p>}
                  {flagged && state.explain.status === 'error' && (
                    <div className={styles.status} role="alert">
                      <span>{state.explain.problem instanceof ApiProblem ? state.explain.problem.title : 'I couldn’t work out which sentences moved the score.'}</span>
                      <Button onClick={essay.retryExplain}>Try again</Button>
                    </div>
                  )}
                </>
              )
              : <section className={styles.locked} aria-label="The essay"><p>{state.scoredText}</p></section>
          ) : (
            <>
              <EssayEditor text={state.text} onChange={essay.setText} onSubmit={essay.submit} minWords={meta.limits.min_words} disabledReason={blocked} />
              {!state.text && !problem && <p className={styles.invite}>No essay yet. Your score will land on a ruler from −10 to +10, next to the line where essays get flagged.</p>}
            </>
          )}
        </div>

        {scored && (
          <aside className={styles.aside} aria-label="What to do next">
            {hasMarks && explain && (
              <div className={styles.legend}>
                <h2 className="t-heading">Reading the highlights</h2>
                <p>{explain.method === 'occlusion'
                  ? 'Each sentence was removed in turn and the essay scored again. The bigger the drop, the darker the mark.'
                  : 'No single sentence decides this score, so the marks show each sentence’s share of it instead of what happens when it is removed.'}</p>
                <ul>
                  {legend(explain.method).map((l) => (
                    <li key={l.tier}><span aria-hidden="true" className={styles.swatch} data-tier={l.tier} /><span className={styles.legendText}><span>{l.name}</span><span className={styles.range}>{l.range}</span></span></li>
                  ))}
                </ul>
                <p className={styles.range}>Under 10% of the largest: no mark.</p>
              </div>
            )}
            <div className={styles.card}>
              <h2 className="t-heading">Could a few edits change the answer?</h2>
              <p>Add typos or paraphrase this essay, then score it again.</p>
              <Button variant="primary" as={Link} to="/fool">Try to fool it</Button>
            </div>
            {flagged && (
              <WhichAi guess={state.attribution} onOpen={essay.loadAttribution} knownHuman={example?.label === 'human'}
                       heldout={state.attribution.data?.heldout_accuracy ?? '0–28%'} />
            )}
          </aside>
        )}
      </div>

      <footer className={styles.footer}>
        <p className={styles.promise}>A flag is a reason to ask questions, not evidence.</p>
        <p className={styles.phoneLimits}>Trained on US school essays and 2023-era AI. Untested on non-native writers, adults, newer AI models and partly AI-written essays.</p>
        <div className={styles.limits}>
          <p>It learned to separate US school essays, grades 6 to 12, from essays written by 2023-era AI models. Nobody has measured how it treats:</p>
          <ul>
            <li>Writers whose first language isn’t English</li>
            <li>Adults, or any genre other than school essays</li>
            <li>Newer AI models, and humaniser tools that rewrite whole paragraphs</li>
            <li>Essays that are only partly AI-written</li>
          </ul>
        </div>
      </footer>

      {scored && (
        <div className={styles.bar}>
          <Button onClick={essay.edit}>Edit essay</Button>
          <Button variant="primary" as={Link} to="/fool">Try to fool it</Button>
        </div>
      )}
    </div>
  )
}
