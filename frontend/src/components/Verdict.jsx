import Spectrum from './Spectrum'
import { fmt, words } from '../lib/format'

// "Before you trust this": at most four reasons to doubt THIS result, computed from data the API already returned.
// Each message is anchored to a measured number (notebooks 09 and 14, README).
function doubtsFor(v, text, highlights, strictness) {
  const out = []
  const margin = v.score - v.threshold
  const n = words(text).length
  if (v.flagged && margin < 2) out.push(<><b>Borderline.</b> The score is only {fmt(margin)} above the flag line. Small edits can move it under (try the typo rewrite below).</>)
  if (!v.flagged && margin > -2) out.push(<><b>Close call.</b> The score is {Math.abs(margin).toFixed(1)} below the flag line.</>)
  if (v.flagged && n > 420) out.push(<><b>Long, polished essay.</b> The human essays this detector wrongly flags tend to be long and nearly free of spelling mistakes (median 489 words).</>)
  if (highlights && highlights.method === 'integrated_gradients') out.push(<><b>No single sentence decides it.</b> The style runs through the whole essay, so the shading spreads thin.</>)
  if (v.tokens > v.tokens_read) out.push(<><b>Only part was read.</b> The detector reads the first {v.tokens_read} of {v.tokens} tokens.</>)
  if (v.flagged) out.push(<><b>Topics shift the error rate.</b> This setting flags {strictness === 'strict' ? '0.5%' : '1%'} of human essays on familiar prompts, but {strictness === 'strict' ? '2.3%' : '3.9%'} on prompts it never saw.</>)
  if (!v.flagged) out.push(<><b>Not flagged is not proof.</b> It means the style is closer to the 2023 student essays it trained on.</>)
  return out.slice(0, 4)
}

export default function Verdict({ v, text, highlights, strictness }) {
  const doubts = doubtsFor(v, text, highlights, strictness)
  return (
    <section className="card verdict" aria-labelledby="verdict-h">
      <div className="card-head">
        <h2 id="verdict-h">Verdict</h2>
        <span className={`chip ${v.flagged ? 'ai' : 'human'}`}>{v.flagged ? 'Flagged' : 'Not flagged'}</span>
      </div>
      <p className="verdict-word">
        {v.flagged ? <>Reads as <span className="ai">AI-written</span></> : <>Reads as <span className="human">student-written</span></>}
      </p>
      <Spectrum score={v.score} threshold={v.threshold} />
      <p className="verdict-sub">
        Score <b>{fmt(v.score)}</b> against a flag line of <b>{fmt(v.threshold)}</b>, set so {strictness === 'strict' ? '0.5%' : '1%'} of
        validation human essays cross it. A statistical hint about style, never proof of who wrote it.
      </p>
      <div>
        <p className="label" style={{ marginBottom: 10 }}>Before you trust this</p>
        <ul className="doubts">
          {doubts.map((d, i) => (
            <li key={i}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 8v4.5M12 16h.01" strokeLinecap="round" /></svg>
              <span>{d}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
