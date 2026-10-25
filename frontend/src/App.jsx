import { useEffect, useState } from 'react'
import * as api from './api'
import { SAMPLE_META } from './samples'
import { words } from './lib/format'

const MIN_WORDS = 40
const REPO = 'https://github.com/jaiveerminhas06/Ghost-Writer'

export default function App() {
  const [samples, setSamples] = useState({})           // essay texts from GET /api/samples
  const [pick, setPick] = useState(-1)                 // which example is loaded; -1 = your own
  const [text, setText] = useState('')
  const [strictness, setStrictness] = useState('strict')
  const [err, setErr] = useState('')

  useEffect(() => {
    api.getSamples().then(setSamples).catch(() => setErr('Cannot reach the API. Start it with: uvicorn api.main:app --port 8000'))
  }, [])

  const n = words(text).length
  const ready = n >= MIN_WORDS
  const names = Object.keys(samples)

  function load(i) {
    setPick(i)
    setText(i >= 0 ? Object.values(samples)[i] : '')
  }

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
              </div>
              <div className="sheet-body">
                <label htmlFor="essay" className="sr-only">Essay text</label>
                <textarea id="essay" className="essay-input" value={text} spellCheck="false"
                          placeholder="Paste an essay here. English, at least 40 words."
                          onChange={(e) => { setText(e.target.value); if (pick >= 0) setPick(-1) }} />
              </div>
              <div className="sheet-foot">
                <p className={`count${!ready && text ? ' warn' : ''}`} aria-live="polite">
                  <span className="mono">{n}</span> words{!ready && ` · at least ${MIN_WORDS} needed`} · not stored or logged
                </p>
                <div className="seg" role="group" aria-label="Strictness">
                  <button aria-pressed={strictness === 'strict'} onClick={() => setStrictness('strict')}>Strict<small>0.5%</small></button>
                  <button aria-pressed={strictness === 'standard'} onClick={() => setStrictness('standard')}>Standard<small>1%</small></button>
                </div>
                <button className="primary" disabled>Analyse essay</button>
              </div>
            </article>
            {err && <p className="err" role="alert" style={{ marginTop: 10 }}>{err}</p>}
          </div>

          <aside className="readout" aria-label="Results" aria-live="polite">
            <section className="card idle">
              <h2>How to read the result</h2>
              <p>Every essay gets one score. Above the flag line it is flagged as AI-like. Choose an example or paste an essay to begin.</p>
            </section>
          </aside>
        </main>
      </div>

      <section className="method" id="method" aria-labelledby="method-h">
        <div className="wrap"><h2 id="method-h">How the verdict is made</h2></div>
      </section>
    </>
  )
}
