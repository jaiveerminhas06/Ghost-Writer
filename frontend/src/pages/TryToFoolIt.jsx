import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import styles from './TryToFoolIt.module.css'
import AttemptsTable from '../components/AttemptsTable'
import Button from '../components/Button'
import CompareRuler from '../components/CompareRuler'
import ComparePanes from '../components/ComparePanes'
import MethodCards from '../components/MethodCards'
import MetaGate from '../components/MetaGate'
import { ErrorPanel } from '../components/VerdictPanel'
import { REPO } from '../components/Header'
import { useEssay } from '../state/contexts'
import { disagreement, FIRST_SEED, methodOf, METHODS, nextSeed, resultCopy, sidesOfTheLine } from '../lib/fool'
import { words } from '../lib/format'
import { oneIn, scoreWords, ZONE_WORD } from '../lib/scale'
import { attackFacts, testedBullets } from '../lib/figures'

const COST = { typos: 'Instant', t5: 'Slower: runs the T5 model' }

/** Try to fool it: rewrite the essay (typos or a paraphrase), score it again, and see what moved. */
export default function TryToFoolIt() {
  return <MetaGate>{(meta) => <Loaded meta={meta} />}</MetaGate>
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
    if (words(state.text).length >= (meta.limits?.min_words ?? 40)) { started.current = true; essay.submit() }
  }, [state.status, state.text, meta, essay])

  const score = state.status === 'scored' ? state.score : null
  const example = (meta.examples ?? []).find((x) => x.id === state.exampleId) ?? null

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

  const before = score.verdict
  const attempts = state.attempts
  const shown = attempts.find((a) => a.id === state.selected) ?? null
  const ran = attempts.some((a) => a.method === method)
  const busy = state.rewriting !== null
  const kind = methodOf(method).kind
  const t5Missing = meta.t5_available === false
  const seed = nextSeed(attempts, method)
  const sides = sidesOfTheLine(attempts, method)
  const copy = shown ? resultCopy({ method: shown.method, before: before.zone, after: shown.zone, wordsChanged: shown.wordsChanged }) : null
  const zoneWord = (/** @type {'flagged' | 'above_usual' | 'not_flagged'} */ z) => ZONE_WORD[z].toLowerCase()
  const facts = attackFacts(meta)

  const cards = METHODS.map((m) => {
    const last = [...attempts].reverse().find((a) => a.method === m.id)
    const desc = {
      typos5: 'Swaps, drops or doubles a letter in about one word in twenty. Meaning stays; spelling gets worse.',
      typos10: `One word in ten.${facts.typos10}`,
      t5: `Rewrites each sentence with a pretrained paraphraser.${facts.t5} Check the result still says what the student meant.`,
      t5_heavy: facts.heavy,
    }[m.id]
    return {
      id: m.id, title: m.title, cost: COST[m.kind], desc: desc ?? '', muted: !last,
      result: last ? `Last run: ${zoneWord(before.zone)} to ${zoneWord(last.zone)}` : 'Not run on this essay',
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
        <div className={styles.aboutBox}>
          <p className={styles.about}>Rewriting <Link to="/">{example ? example.name : 'your essay'}</Link>, {score.words} words. Official verdict: {zoneWord(before.zone)}.</p>
        </div>
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
                : <><h2 id="result" className="t-section">Pick a rewrite, then press Rewrite and re-score.</h2><p>The official verdict is {zoneWord(before.zone)}: {scoreWords(before.p, meta.jury.scale.val_humans)}. It is marked here, and each new verdict beside it.</p></>}
          </div>
          {shown && !busy && (
            <dl className={styles.facts}>
              <dt>Verdict</dt><dd>{ZONE_WORD[before.zone]} to {ZONE_WORD[shown.zone]} <span>({oneIn(before.p, meta.jury.scale.val_humans)} to {oneIn(shown.p, meta.jury.scale.val_humans)})</span></dd>
              <dt>Words changed</dt><dd>{shown.wordsChanged} of {score.words} <span>({Math.round(shown.share * 100)}%)</span></dd>
              <dt>Meaning</dt><dd>{methodOf(shown.method).kind === 'typos' ? 'Unchanged, spelling worse' : 'Not checked: read it'}</dd>
            </dl>
          )}
        </div>
        <CompareRuler scale={meta.jury.scale} before={before} after={shown && !busy ? { zone: shown.zone, p: shown.p } : null} />
      </section>

      {shown && (
        <section aria-labelledby="compare" className={styles.compare}>
          <div className={styles.compareHead}>
            <h2 id="compare" className="t-section">What changed</h2>
            <p className={styles.small}>The two pages scroll together. Changed words are underlined.</p>
          </div>
          <ComparePanes original={state.scoredText} edited={shown.edited}
                        left={{ title: 'Original', score: zoneWord(before.zone) }}
                        right={{ title: methodOf(shown.method).title, score: zoneWord(shown.zone) }} />
        </section>
      )}

      <div className={styles.bottom}>
        <section aria-labelledby="attempts" className={styles.attempts}>
          <h2 id="attempts" className="t-section">Attempts on this essay</h2>
          {sides && <p className={styles.sides}>{disagreement(sides, method)}</p>}
          <AttemptsTable attempts={attempts} original={before} selected={state.selected} words={score.words} valHumans={meta.jury.scale.val_humans} onSelect={essay.selectAttempt} />
        </section>
        <aside aria-labelledby="tested" className={styles.tested}>
          <h2 id="tested" className="t-heading">{before.zone === 'above_usual' ? 'This essay was between the lines' : 'What the tests found'}</h2>
          {testedBullets(meta).length > 0 ? <p>In random samples of the test set, small edits moved some verdicts, in both directions:</p> : <p>The results of testing these rewrites on the whole test set are in notebook 22b.</p>}
          {testedBullets(meta).length > 0 && <ul>{testedBullets(meta).map((b) => <li key={b}>{b}</li>)}</ul>}
          {testedBullets(meta).length > 0 && <p className={styles.small}>Random samples of on-topic essays, scored by the official verdict (notebook 22b).</p>}
          <a href={`${REPO}/blob/main/Notebooks/22b_attack_final.ipynb`}>The full attack results (notebook 22b)</a>
        </aside>
      </div>
    </div>
  )
}
