import { Fragment, useMemo, useState } from 'react'
import * as api from '../api'
import Spectrum from './Spectrum'
import { fmt } from '../lib/format'
import { diffByParagraph } from '../lib/diff'

const ATTACKS = [
  { key: 'typos_5', name: 'Typos', detail: '5% of words' },
  { key: 'typos_10', name: 'Typos', detail: '10% of words' },
  { key: 'paraphrase_light', name: 'Paraphrase, light', detail: 'T5 · temp 1.0' },
  { key: 'paraphrase_heavy', name: 'Paraphrase, heavy', detail: 'T5 · temp 1.5' },
]

// One sentence on what the result means, by whether the verdict changed (wording from notebook 13's findings).
function outcomeFor(before, out) {
  if (before.flagged && !out.flagged) return 'The rewrite got past the detector. Read the rewritten text: does it still make sense?'
  if (before.flagged && out.flagged) return 'Still flagged. In the tests, typos and paraphrasing rarely changed a confident verdict unless they rewrote about half the words.'
  if (!before.flagged && out.flagged) return 'Now flagged. Running honest work through a paraphraser can make it look machine-written.'
  return out.score > before.score ? 'Still not flagged, but the rewrite moved it toward AI-like.' : 'Still not flagged.'
}

export default function FoolIt({ text, strictness, before }) {
  const [attack, setAttack] = useState(null)
  const [out, setOut] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [showChanges, setShowChanges] = useState(true)
  // No reset needed when the essay or strictness changes: App clears the result then, which unmounts this panel.

  async function run(key) {
    setAttack(key); setBusy(true); setErr('')
    try { setOut({ ...(await api.rewrite(text, strictness, key)), attack: key }) }
    catch (e) { setErr(e.message) }
    setBusy(false)
  }
  const diff = useMemo(() => (out ? diffByParagraph(text, out.edited) : null), [out, text])

  return (
    <section className="card" aria-labelledby="fool-h">
      <div className="card-head">
        <h2 id="fool-h">Try to fool it</h2>
        <span className="label">Rewrite, then re-score</span>
      </div>
      <div className="attacks" role="group" aria-label="Kind of rewrite">
        {ATTACKS.map((a) => (
          <button key={a.key} className="attack" aria-pressed={attack === a.key} disabled={busy} onClick={() => run(a.key)}>
            <b>{a.name}</b><span>{a.detail}</span>
          </button>
        ))}
      </div>
      {busy && (
        <div className="fool-out" aria-busy="true">
          <p className="verdict-sub">{attack && attack.startsWith('para') ? 'Paraphrasing with T5… about 15 s on a CPU.' : 'Adding typos…'}</p>
          <div className="skel" /><div className="skel" style={{ width: '70%' }} />
        </div>
      )}
      {err && <p className="err" role="alert">{err}</p>}
      {out && !busy && (
        <div className="fool-out" aria-live="polite">
          <Spectrum score={out.score} threshold={out.threshold} before={before.score} label="Score after rewrite" />
          <div className="delta">
            <span className="big">{fmt(before.score)} → {fmt(out.score)}</span>
            <span className="small">{Math.round(out.words_changed * 100)}% of words changed</span>
            <span className={`chip ${out.flagged ? 'ai' : 'human'}`}>{out.flagged ? 'Flagged' : 'Not flagged'}</span>
          </div>
          <p className="outcome">{outcomeFor(before, out)}</p>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <span className="label">Rewritten text</span>
            <button className="ghost-btn" onClick={() => setShowChanges((s) => !s)} aria-pressed={showChanges}>{showChanges ? 'Hide changes' : 'Show changes'}</button>
          </div>
          <div className="diff" tabIndex={0} aria-label="Rewritten text">
            {showChanges
              ? diff.map((ops, k) => (
                <Fragment key={k}>
                  {k > 0 && '\n\n'}
                  {ops.flatMap(([op, w], i) => {
                    const el = op === '=' ? <span key={i}>{w}</span> : op === '+' ? <ins key={i}>{w}</ins> : <del key={i}>{w}</del>
                    return i ? [' ', el] : [el]
                  })}
                </Fragment>
              ))
              : out.edited}
          </div>
        </div>
      )}
    </section>
  )
}
