import { useState } from 'react'

const signed = (c) => (c >= 0 ? '+' : '−') + Math.abs(c).toFixed(2)

// One bar per sentence above the essay: up (amber) pushes toward AI-like, down (blue) toward student-like.
// Hovering or tabbing to a bar outlines its sentence; clicking scrolls to it. "Show numbers" gives the same data
// as a table, so colour is never the only way to read it.
export default function Fingerprint({ data, active, setActive, onPick }) {
  const [asTable, setAsTable] = useState(false)
  const max = Math.max(1e-6, ...data.sentences.map((s) => Math.abs(s.contribution ?? 0)))
  return (
    <div className="print">
      <div className="print-top">
        <p className="print-note">
          {data.method === 'occlusion'
            ? 'Each bar is one sentence: how much the score drops when that sentence is removed.'
            : 'Each bar is one sentence, scored with integrated gradients: removing any single sentence barely changes this score.'}
        </p>
        <button className="ghost-btn" onClick={() => setAsTable((x) => !x)} aria-pressed={asTable}>{asTable ? 'Show bars' : 'Show numbers'}</button>
      </div>
      {!asTable ? (
        <>
          <div className="bars" role="group" aria-label="Contribution of each sentence">
            {data.sentences.map((s, i) => {
              const c = s.contribution
              const height = c == null ? 0 : (Math.abs(c) / max) * 48
              return (
                <button key={i} className={`bar-btn${active === i ? ' active' : ''}`}
                        aria-label={`Sentence ${i + 1}: ${c == null ? 'not read' : `contribution ${signed(c)}`}`}
                        onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)}
                        onFocus={() => setActive(i)} onBlur={() => setActive(null)} onClick={() => onPick(i)}>
                  {c == null ? <i className="none" /> : <i className={c >= 0 ? 'up' : 'down'} style={{ height: `${Math.max(2, height)}%` }} />}
                </button>
              )
            })}
          </div>
          <div className="print-legend">
            <span><i className="dot ai" />pushes toward AI-like</span>
            <span><i className="dot human" />pushes toward student-like</span>
            <span>Hover or tab to a bar to find its sentence</span>
          </div>
        </>
      ) : (
        <div className="table-wrap">
          <table className="nums">
            <thead><tr><th>#</th><th>Sentence</th><th style={{ textAlign: 'right' }}>Contribution</th></tr></thead>
            <tbody>
              {data.sentences.map((s, i) => (
                <tr key={i}><td className="n">{i + 1}</td><td>{s.text}</td><td className="n">{s.contribution == null ? 'not read' : signed(s.contribution)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
