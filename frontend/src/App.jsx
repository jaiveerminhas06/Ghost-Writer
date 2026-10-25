import { useEffect, useState } from 'react'
import * as api from './api'

const ATTACKS = {
  typos_5: 'Typos 5%',
  typos_10: 'Typos 10%',
  paraphrase_light: 'Paraphrase (light)',
  paraphrase_heavy: 'Paraphrase (heavy)',
}

// Turns a sentence's contribution into a background colour. Sentences below 10% of the
// strongest one get none, so near-zero sentences are not painted (same rule as the Streamlit demo).
function shade(c, max) {
  if (c == null || max <= 0 || c / max < 0.1) return undefined
  const a = Math.min(c / max, 1)
  return `rgba(255, 140, 0, ${0.15 + 0.5 * a})`
}

function Verdict({ v }) {
  return (
    <section>
      <h2>Verdict</h2>
      <p className={v.flagged ? 'flag yes' : 'flag no'}>{v.flagged ? 'AI-like' : 'Not flagged'}</p>
      <p>Score {v.score.toFixed(2)} · flag threshold {v.threshold.toFixed(2)}</p>
      <p className="muted">
        The detector read {v.tokens_read} of {v.tokens} tokens. A flag is a statistical hint about writing style,
        not proof: careful, fluent human writing is sometimes flagged.
      </p>
    </section>
  )
}

function Highlights({ data }) {
  const max = Math.max(0, ...data.sentences.map((s) => s.contribution ?? 0))
  return (
    <section>
      <h2>Sentence highlights</h2>
      <p className="muted">
        {data.method === 'occlusion'
          ? 'Darker = the score drops more when this sentence is removed.'
          : 'The AI style is spread through the whole essay, so removing one sentence changes little. Shading uses integrated gradients instead.'}
      </p>
      <p className="essay">
        {data.sentences.map((s, i) => (
          <span key={i} style={{ background: shade(s.contribution, max) }}>{s.text} </span>
        ))}
      </p>
      {data.truncated && <p className="muted">Only the first sentences are shown.</p>}
    </section>
  )
}

function Attribution({ data }) {
  return (
    <details>
      <summary>Most similar training sources</summary>
      {data.families.map((f) => (
        <p key={f.family}>{f.family}: {(f.probability * 100).toFixed(0)}%</p>
      ))}
      <p className="muted">
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
      <select value={attack} onChange={(e) => setAttack(e.target.value)}>
        {Object.entries(ATTACKS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
      </select>{' '}
      <button onClick={run} disabled={busy}>{busy ? 'Rewriting…' : 'Rewrite and re-score'}</button>
      {err && <p className="error">{err}</p>}
      {out && (
        <>
          <p>
            Score {before.score.toFixed(2)} → {out.score.toFixed(2)} ·{' '}
            {out.flagged ? 'still flagged' : 'no longer flagged'} · {(out.words_changed * 100).toFixed(0)}% of words changed
          </p>
          <p className="essay">{out.edited}</p>
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
  const [err, setErr] = useState('')

  useEffect(() => { api.getSamples().then(setSamples).catch(() => setErr('Cannot reach the API. Start it with: uvicorn api.main:app --port 8000')) }, [])

  async function analyse() {
    setBusy(true); setErr(''); setResult(null)
    try {
      const verdict = await api.score(text, strictness)
      // Highlights and attribution are only shown for flagged essays.
      const [highlights, attribution] = verdict.flagged
        ? await Promise.all([api.explain(text, strictness), api.attribution(text, strictness)])
        : [null, null]
      setResult({ verdict, highlights, attribution })
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <main>
      <h1>Ghost Writer</h1>
      <p className="muted">Was this essay written by a person or an AI? Paste one and see why the detector decides as it does.</p>

      <select value="" onChange={(e) => { setText(samples[e.target.value]); setResult(null) }}>
        <option value="" disabled>Load an example…</option>
        {Object.keys(samples).map((k) => <option key={k} value={k}>{k}</option>)}
      </select>
      <textarea value={text} onChange={(e) => { setText(e.target.value); setResult(null) }} rows={12} placeholder="Paste an essay (at least 40 words)" />

      <div className="row">
        <label>
          Strictness{' '}
          <select value={strictness} onChange={(e) => { setStrictness(e.target.value); setResult(null) }}>
            <option value="strict">Strict (0.5% false positives)</option>
            <option value="standard">Standard (1% false positives)</option>
          </select>
        </label>
        <button onClick={analyse} disabled={busy || !text.trim()}>{busy ? 'Analysing…' : 'Analyse'}</button>
      </div>
      {err && <p className="error">{err}</p>}

      {result && (
        <>
          <Verdict v={result.verdict} />
          {result.highlights && <Highlights data={result.highlights} />}
          {result.attribution && <Attribution data={result.attribution} />}
          <Fool text={text} strictness={strictness} before={result.verdict} />
        </>
      )}
    </main>
  )
}
