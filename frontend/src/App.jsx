import { useEffect, useState } from 'react'
import * as api from './api'

const MIN_WORDS = 40
const SCORE_RANGE = 10        // the detector's score (a logit) saturates near ±9.8, so the meter runs -10 to +10

const ATTACKS = {
  typos_5: 'Typos, 5% of words',
  typos_10: 'Typos, 10% of words',
  paraphrase_light: 'Paraphrase, light',
  paraphrase_heavy: 'Paraphrase, heavy',
}

const wordCount = (t) => t.trim().split(/\s+/).filter(Boolean).length

// Turns a sentence's contribution into a highlighter colour. Sentences below 10% of the
// strongest one get none, so near-zero sentences are not painted (same rule as the Streamlit demo).
function shade(c, max) {
  if (c == null || max <= 0 || c / max < 0.1) return undefined
  const a = Math.min(c / max, 1)
  return `rgba(255, 178, 36, ${0.18 + 0.55 * a})`
}

// Position of a score on the meter, as a percentage of its width.
const pct = (x) => `${((Math.max(-SCORE_RANGE, Math.min(SCORE_RANGE, x)) + SCORE_RANGE) / (2 * SCORE_RANGE)) * 100}%`

function Meter({ score, threshold }) {
  return (
    <div className="meter" role="img" aria-label={`Score ${score.toFixed(1)} against a flag threshold of ${threshold.toFixed(1)}`}
         style={{ '--t': pct(threshold), '--s': pct(score) }}>
      <span className="meter-threshold" />
      <span className="meter-score" />
      <span className="meter-end left">human-like</span>
      <span className="meter-end right">AI-like</span>
    </div>
  )
}

function Verdict({ v }) {
  return (
    <section>
      <h2>Verdict</h2>
      <p className={v.flagged ? 'flag yes' : 'flag no'}>{v.flagged ? 'AI-like' : 'Not flagged'}</p>
      <Meter score={v.score} threshold={v.threshold} />
      <p className="numbers">Score {v.score.toFixed(2)} · flag threshold {v.threshold.toFixed(2)}</p>
      <p className="caveat">
        A flag is a statistical hint about writing style, not proof of who wrote it. Careful, fluent human writing is
        sometimes flagged. The detector read {v.tokens_read} of {v.tokens} tokens.
      </p>
    </section>
  )
}

function Highlights({ data }) {
  const max = Math.max(0, ...data.sentences.map((s) => s.contribution ?? 0))
  return (
    <section>
      <h2>Which sentences drove the score</h2>
      <p className="note">
        {data.method === 'occlusion'
          ? 'Darker means the score drops more when that sentence is removed.'
          : 'The AI style runs through the whole essay, so removing one sentence changes little. Shading uses integrated gradients instead.'}
      </p>
      <p className="essay">
        {data.sentences.map((s, i) => (
          <span key={i} style={{ background: shade(s.contribution, max) }}
                title={s.contribution == null ? 'Beyond the 512 tokens the detector reads' : `Contribution ${s.contribution.toFixed(2)}`}>
            {s.text}{' '}
          </span>
        ))}
      </p>
      {data.truncated && <p className="note">Only the first sentences are shown.</p>}
    </section>
  )
}

function Attribution({ data }) {
  return (
    <details>
      <summary>Most similar training sources <span className="note">(not proof of origin)</span></summary>
      <ul className="families">
        {data.families.map((f) => (
          <li key={f.family}>
            <span>{f.family}</span>
            <span className="bar"><span style={{ width: `${f.probability * 100}%` }} /></span>
            <span className="numbers">{(f.probability * 100).toFixed(0)}%</span>
          </li>
        ))}
      </ul>
      <p className="caveat">
        This only says which training essays the text resembles. On sources the model had never seen, the right family
        came up only {data.heldout_accuracy} of the time, so it does not show which model wrote the essay.
      </p>
    </details>
  )
}

function Fool({ text, strictness, before }) {
  const [attack, setAttack] = useState('typos_5')
  const [out, setOut] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function run() {
    setBusy(true); setErr('')
    try { setOut(await api.rewrite(text, strictness, attack)) }
    catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <section>
      <h2>Try to fool it</h2>
      <p className="note">Rewrite the essay automatically, then score the new version.</p>
      <div className="row start">
        <select value={attack} onChange={(e) => setAttack(e.target.value)} aria-label="Kind of rewrite">
          {Object.entries(ATTACKS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
        <button className="secondary" onClick={run} disabled={busy}>{busy ? 'Rewriting…' : 'Rewrite and re-score'}</button>
      </div>
      {err && <p className="error" role="alert">{err}</p>}
      {out && (
        <>
          <p className="numbers">
            Score {before.score.toFixed(2)} → {out.score.toFixed(2)} ·{' '}
            <strong>{out.flagged ? 'still flagged' : 'no longer flagged'}</strong> · {(out.words_changed * 100).toFixed(0)}% of words changed
          </p>
          <Meter score={out.score} threshold={out.threshold} />
          <p className="essay edited">{out.edited}</p>
        </>
      )}
    </section>
  )
}

export default function App() {
  const [samples, setSamples] = useState({})
  const [text, setText] = useState('')
  const [strictness, setStrictness] = useState('strict')
  const [result, setResult] = useState(null)   // { verdict, highlights, attribution }
  const [busy, setBusy] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)   // highlights still being computed
  const [err, setErr] = useState('')

  useEffect(() => { api.getSamples().then(setSamples).catch(() => setErr('Cannot reach the API. Start it with: uvicorn api.main:app --port 8000')) }, [])

  async function analyse() {
    setBusy(true); setErr(''); setResult(null)
    try {
      const verdict = await api.score(text, strictness)
      setResult({ verdict, highlights: null, attribution: null })   // show the verdict at once
      setBusy(false)
      if (verdict.flagged) {
        // Highlights are slow on a CPU host, so they fill in when ready. Only flagged essays get them.
        setLoadingMore(true)
        const [highlights, attribution] = await Promise.all([api.explain(text, strictness), api.attribution(text, strictness)])
        setResult({ verdict, highlights, attribution })
      }
    } catch (e) { setErr(e.message) }
    setBusy(false); setLoadingMore(false)
  }

  const words = wordCount(text)
  const ready = words >= MIN_WORDS

  return (
    <main>
      <header>
        <h1>Ghost Writer</h1>
        <p>Was this essay written by a person or an AI? Paste one to see the verdict and the sentences behind it.</p>
      </header>

      <div className="layout">
        <div className="input">
          <label htmlFor="example">Start from an example</label>
          <select id="example" value="" onChange={(e) => { setText(samples[e.target.value]); setResult(null) }}>
            <option value="" disabled>Choose…</option>
            {Object.keys(samples).map((k) => <option key={k} value={k}>{k}</option>)}
          </select>

          <label htmlFor="essay">Essay</label>
          <textarea id="essay" value={text} rows={14} placeholder="Paste an essay here"
                    onChange={(e) => { setText(e.target.value); setResult(null) }} />
          <p className={ready || !text ? 'note' : 'note warn'}>
            {words} {words === 1 ? 'word' : 'words'}{!ready && ` · at least ${MIN_WORDS} needed`}. Your text is sent to the server only
            to be scored. It is not saved or logged.
          </p>

          <label htmlFor="strictness">Strictness</label>
          <select id="strictness" value={strictness} onChange={(e) => { setStrictness(e.target.value); setResult(null) }}>
            <option value="strict">Strict (0.5% false positives)</option>
            <option value="standard">Standard (1% false positives)</option>
          </select>
          <button onClick={analyse} disabled={busy || !ready}>{busy ? 'Analysing…' : 'Analyse'}</button>
          {err && <p className="error" role="alert">{err}</p>}
        </div>

        <div className="results" aria-live="polite">
          {!result && !busy && (
            <div className="empty">
              <h2>Results appear here</h2>
              <p>Load an example or paste your own essay. The third example is a careful human essay that the detector
                wrongly flags, which is worth trying to see how it can be wrong.</p>
            </div>
          )}
          {busy && <p className="note">Scoring… the first request can take several seconds while the model loads.</p>}
          {result && (
            <>
              <Verdict v={result.verdict} />
              {loadingMore && !result.highlights && (
                <section aria-busy="true">
                  <h2>Which sentences drove the score</h2>
                  <p className="note">Working this out takes up to a minute.</p>
                  <div className="skeleton" /><div className="skeleton short" />
                </section>
              )}
              {result.highlights && <Highlights data={result.highlights} />}
              {result.attribution && <Attribution data={result.attribution} />}
              <Fool text={text} strictness={strictness} before={result.verdict} />
            </>
          )}
        </div>
      </div>

      <footer>
        CSE472 course project. Scores, limits and evaluation:{' '}
        <a href="https://github.com/jaiveerminhas06/Ghost-Writer">README and model card on GitHub</a>.
      </footer>
    </main>
  )
}
