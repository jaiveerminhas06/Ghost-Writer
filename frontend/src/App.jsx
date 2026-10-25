import { useEffect, useRef, useState } from 'react'
import * as api from './api'
import { SAMPLE_META } from './samples'
import { fmt, reduceMotion, words } from './lib/format'
import Icon from './components/Icon'
import AnalysisLog from './components/AnalysisLog'
import Verdict from './components/Verdict'
import Spectrum from './components/Spectrum'
import Attribution from './components/Attribution'
import FoolIt from './components/FoolIt'
import Fingerprint from './components/Fingerprint'
import AnnotatedEssay from './components/AnnotatedEssay'

const MIN_WORDS = 40
const STEP_TEXT = {
  read: 'Reading the essay',
  score: 'Scoring with fine-tuned DistilRoBERTa',
  explain: 'Tracing which sentences moved the score (up to a minute on CPU)',
  attrib: 'Comparing with training sources',
}
const THRESHOLD_PREVIEW = { strict: 7.80, standard: 4.67 }   // only for the idle "how to read" diagram; real runs use the API's threshold
const REPO = 'https://github.com/jaiveerminhas06/Ghost-Writer'

export default function App() {
  const [samples, setSamples] = useState({})           // essay texts from GET /api/samples
  const [pick, setPick] = useState(-1)                 // which example is loaded; -1 = your own
  const [text, setText] = useState('')
  const [strictness, setStrictness] = useState('strict')
  const [err, setErr] = useState('')
  const [mode, setMode] = useState('edit')             // 'edit' = textarea, 'read' = the essay as examined
  const [result, setResult] = useState(null)           // { verdict, highlights, attribution }
  const [steps, setSteps] = useState(null)             // the analysis log
  const [elapsed, setElapsed] = useState(0)
  const [active, setActive] = useState(null)           // sentence under the pointer / focus (shared by bars and essay)
  const [lit, setLit] = useState(false)                // true once highlights may fade in
  const [sweep, setSweep] = useState(0)                // bump to replay the lamp sweep
  const sentenceRefs = useRef([])
  const bodyRef = useRef(null)
  const booted = useRef(false)                         // React runs effects twice in development; analyse the first example only once
  const runId = useRef(0)                              // each run gets a number; stale runs are ignored

  // Open in a working state: ?sample=0|1|2 picks an example, otherwise example 3 (the false alarm) is analysed.
  useEffect(() => {
    if (booted.current) return
    booted.current = true
    api.getSamples().then((s) => {
      setSamples(s)
      const params = new URLSearchParams(window.location.search)
      const q = params.has('sample') ? Number(params.get('sample')) : 2
      const i = Number.isInteger(q) && q >= 0 && q < Object.keys(s).length ? q : 2
      const t = Object.values(s)[i]
      if (t) { setPick(i); setText(t); analyse(t, 'strict') }
    }).catch(() => setErr('Cannot reach the API. Start it with: uvicorn api.main:app --port 8000'))
  }, [])

  const working = !!steps && steps.some((s) => s.state === 'active')
  const activeStep = steps ? steps.findIndex((s) => s.state === 'active') : -1
  useEffect(() => {   // live timer for the active step
    if (!working) return
    const t0 = performance.now()
    const id = setInterval(() => setElapsed(performance.now() - t0), 100)
    return () => clearInterval(id)
  }, [working, activeStep])

  async function analyse(t = text, s = strictness) {
    const run = ++runId.current
    const mark = (key, state, ms) => setSteps((st) => st && st.map((x) => (x.key === key ? { ...x, state, ms } : x)))
    setErr(''); setResult(null); setLit(false); setActive(null); setMode('read')
    setSteps(['read', 'score', 'explain', 'attrib'].map((key) => ({ key, text: STEP_TEXT[key], state: 'pending' })))
    try {
      mark('read', 'done', 0); mark('score', 'active')
      let t0 = performance.now()
      const verdict = await api.score(t, s)
      if (run !== runId.current) return                // the user started something else meanwhile
      mark('score', 'done', performance.now() - t0)
      setResult({ verdict, highlights: null, attribution: null })   // show the verdict at once
      if (!verdict.flagged) { mark('explain', 'skipped'); mark('attrib', 'skipped'); return }
      mark('explain', 'active'); mark('attrib', 'active'); t0 = performance.now()
      const [highlights, attribution] = await Promise.all([
        api.explain(t, s).then((h) => { if (run === runId.current) mark('explain', 'done', performance.now() - t0); return h }),
        api.attribution(t, s).then((a) => { if (run === runId.current) mark('attrib', 'done', performance.now() - t0); return a }),
      ])
      if (run !== runId.current) return
      setResult({ verdict, highlights, attribution })
      requestAnimationFrame(() => {   // one lamp sweep down the paper, then the highlights fade in
        if (bodyRef.current) bodyRef.current.style.setProperty('--sweep-to', `${bodyRef.current.offsetHeight}px`)
        setSweep((x) => x + 1); setLit(true)
      })
    } catch (e) {
      if (run !== runId.current) return
      setErr(e.message); setSteps(null); setMode('edit')
    }
  }

  const n = words(text).length
  const ready = n >= MIN_WORDS
  const names = Object.keys(samples)

  // An example is analysed straight away; "Your own" opens an empty sheet.
  function load(i) {
    runId.current++
    const t = i >= 0 ? Object.values(samples)[i] : ''
    setPick(i); setText(t); setResult(null); setSteps(null); setErr(''); setMode('edit')
    if (i >= 0) analyse(t, strictness)
  }
  function edit() { runId.current++; setResult(null); setSteps(null); setMode('edit') }
  function changeStrictness(next) { setStrictness(next); if (result || working) analyse(text, next) }

  function jump(i) {   // bar clicked: bring its sentence into view
    const el = sentenceRefs.current[i]
    if (el) el.scrollIntoView({ behavior: reduceMotion() ? 'auto' : 'smooth', block: 'center' })
    setActive(i)
  }

  const v = result && result.verdict

  return (
    <>
      <div className="wrap">
        <header className="topbar">
          <p className="course label">CSE472 · Deep Learning for NLP</p>
          <nav aria-label="Project links">
            <a href="#method">How it works</a>
            <a href={`${REPO}/blob/main/MODEL_CARD.md`}>Model card</a>
            <a href={REPO}>GitHub</a>
          </nav>
        </header>

        <section className="hero" aria-label="Introduction">
          <div className="wordmark"><h1 className="wm-text">Ghost Writer</h1></div>
          <div className="thesis">
            <p className="lede">Did a student write this essay, or a language model? Paste one. The detector gives its verdict, shows which sentences moved it, and <em>lists its reasons to doubt itself.</em></p>
            <div className="facts">
              <div className="fact"><b>0.9998</b><span>AUC on essay topics it never saw</span></div>
              <div className="fact"><b>99.2%</b><span>of essays by unseen AI models caught</span></div>
              <div className="fact"><b>2.3%</b><span>of human essays on new topics wrongly flagged</span></div>
            </div>
          </div>
        </section>

        <main className="bench">
          <div className="doc">
            <div className="specimens" role="group" aria-label="Load an essay">
              {names.map((name, i) => (
                <button key={name} className="specimen" aria-pressed={pick === i} onClick={() => load(i)}>
                  <span className="kind"><i className={`dot ${SAMPLE_META[i]?.kind || 'own'}`} />{SAMPLE_META[i]?.tag || 'Example'}</span>
                  <span className="name">{SAMPLE_META[i]?.note || name}</span>
                </button>
              ))}
              <button className="specimen" aria-pressed={pick === -1} onClick={() => load(-1)}>
                <span className="kind"><i className="dot own" />Your own</span>
                <span className="name">Paste any essay of 40+ words</span>
              </button>
            </div>

            <article className="sheet" aria-label="The essay">
              <div className="sheet-head">
                <span className="label">Questioned document{pick >= 0 ? ` · example ${pick + 1}` : ''}</span>
                {mode === 'read' && v && (
                  <a className="mini-verdict" href="#verdict-h">
                    <span className={`chip ${v.flagged ? 'ai' : 'human'}`}>{v.flagged ? 'Flagged' : 'Not flagged'}</span>
                    <span className="mono">{fmt(v.score)}</span> vs <span className="mono">{fmt(v.threshold)}</span> ↓
                  </a>
                )}
                {mode === 'read' && <button className="ghost-btn" onClick={edit}><span className="row" style={{ gap: 6 }}><Icon name="edit" size={14} />Edit text</span></button>}
              </div>
              {mode === 'read' && result && result.highlights && (
                <Fingerprint data={result.highlights} active={active} setActive={setActive} onPick={jump} />
              )}
              {mode === 'read' && v && !v.flagged && (
                <div className="print"><p className="print-note">No sentence shading: highlights are only computed for flagged essays, because explanations of a “not flagged” score were unreliable in testing.</p></div>
              )}
              <div className="sheet-body" ref={bodyRef}>
                <div key={sweep} className={`lamp-sweep${sweep ? ' go' : ''}`} aria-hidden="true" />
                {mode === 'edit' ? (
                  <>
                    <label htmlFor="essay" className="sr-only">Essay text</label>
                    <textarea id="essay" className="essay-input" value={text} spellCheck="false"
                              placeholder="Paste an essay here. English, at least 40 words."
                              onChange={(e) => { setText(e.target.value); if (pick >= 0) setPick(-1) }} />
                  </>
                ) : result && result.highlights ? (
                  <AnnotatedEssay text={text} data={result.highlights} active={active} lit={lit} sentenceRefs={sentenceRefs} />
                ) : (
                  <p className="essay">{text}</p>
                )}
              </div>
              <div className="sheet-foot">
                <p className={`count${!ready && text ? ' warn' : ''}`} aria-live="polite">
                  <span className="mono">{n}</span> words{!ready && ` · at least ${MIN_WORDS} needed`} · not stored or logged
                </p>
                <div className="seg" role="group" aria-label="Strictness">
                  <button aria-pressed={strictness === 'strict'} onClick={() => changeStrictness('strict')}>Strict<small>0.5%</small></button>
                  <button aria-pressed={strictness === 'standard'} onClick={() => changeStrictness('standard')}>Standard<small>1%</small></button>
                </div>
                <button className="primary" disabled={!ready || working} onClick={() => analyse()}>{working ? 'Analysing…' : 'Analyse essay'}</button>
              </div>
            </article>
            {err && <p className="err" role="alert" style={{ marginTop: 10 }}>{err}</p>}
          </div>

          <aside className="readout" aria-label="Results" aria-live="polite">
            {steps && (working || !v) && (
              <section className="card"><div className="card-head"><h2>Analysis</h2><span className="label">{working ? 'running' : ''}</span></div><AnalysisLog steps={steps} elapsed={elapsed} /></section>
            )}
            {v && <Verdict v={v} text={text} highlights={result.highlights} strictness={strictness} />}
            {v && !working && steps && <p className="done-line">Analysed in {(((steps[1].ms || 0) + Math.max(steps[2].ms || 0, steps[3].ms || 0)) / 1000).toFixed(1)} s · {v.tokens_read} of {v.tokens} tokens read</p>}
            {result && result.attribution && <Attribution data={result.attribution} />}
            {v && !working && <FoolIt text={text} strictness={strictness} before={v} />}
            {!steps && (
              <section className="card idle">
                <h2>How to read the result</h2>
                <Spectrum score={-6} threshold={THRESHOLD_PREVIEW[strictness]} label="Example score" />
                <p>Every essay gets one score on this scale. Above the dashed flag line it is flagged as AI-like. The line is set on
                  human essays the model never trained on, so that only {strictness === 'strict' ? '0.5%' : '1%'} of them cross it.</p>
                <p>Choose an example or paste an essay, then press <b>Analyse essay</b>.</p>
              </section>
            )}
          </aside>
        </main>
      </div>

      <section className="method" id="method" aria-labelledby="method-h">
        <div className="wrap"><h2 id="method-h">How the verdict is made</h2></div>
      </section>
    </>
  )
}
