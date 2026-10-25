import { useEffect, useId, useState } from 'react'
import { clamp, fmt } from '../lib/format'

// The detector's real scale: a score (a logit) from −10 to +10, with the flag line chosen on validation
// human essays. The optional hollow "before" pin is for the try-to-fool-it panel.
export default function Spectrum({ score, threshold, before, label = 'Score' }) {
  const id = useId()
  // the pin starts at the centre (or at "before") and glides to the score (CSS transition on transform)
  const [shown, setShown] = useState(before ?? 0)
  useEffect(() => {
    const r = requestAnimationFrame(() => setShown(score))
    return () => cancelAnimationFrame(r)
  }, [score])

  const L = 18, R = 302                                         // drawn in a 320-wide box so text stays ~1:1 in the readout column
  const X = (v) => L + ((clamp(v, -10, 10) + 10) / 20) * (R - L)
  const tx = X(threshold)
  const labelDx = (x, half) => clamp(x, L + half, R - half) - x // keep a label inside the box; the pin itself stays true
  const showBeforeLabel = before != null && Math.abs(X(before) - X(score)) > 62
  const desc = `${label} ${fmt(score)} on a scale from −10 (student-like) to +10 (AI-like). Flag line at ${fmt(threshold)}: ${score >= threshold ? 'above it, flagged' : 'below it, not flagged'}.`

  return (
    <svg className="spectrum" viewBox="0 0 320 112" role="img" aria-label={desc}>
      <defs><clipPath id={id}><rect x={L} y="44" width={R - L} height="20" rx="10" /></clipPath></defs>
      <g clipPath={`url(#${id})`}>
        <rect className="zone-h" x={L} y="44" width={tx - L} height="20" />
        <rect className="zone-a" x={tx} y="44" width={R - tx} height="20" />
      </g>
      <text className="zone-txt" x={L + 10} y="57.5">STUDENT-LIKE</text>
      {R - tx > 54 && <text className="zone-txt" x={R - 10} y="57.5" textAnchor="end">AI-LIKE</text>}
      {[-10, -5, 0, 5, 10].map((v) => (
        <g key={v}>
          <line className="tick" x1={X(v)} x2={X(v)} y1="68" y2="73" />
          <text className="axis" x={X(v)} y="86" textAnchor="middle">{v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0'}</text>
        </g>
      ))}
      <line className="flagline" x1={tx} x2={tx} y1="36" y2="76" />
      <text className="flagtxt" x={clamp(tx, 58, 262)} y="106" textAnchor="middle">flag line {fmt(threshold)}</text>
      {before != null && (
        <g className="pin before" style={{ transform: `translateX(${X(before)}px)` }}>
          <circle cx="0" cy="54" r="6.5" />
          {showBeforeLabel && <text x={labelDx(X(before), 30)} y="22" textAnchor="middle">before {fmt(before)}</text>}
        </g>
      )}
      <g className="pin" style={{ transform: `translateX(${X(shown)}px)` }}>
        <line x1="0" x2="0" y1="28" y2="46" />
        <circle cx="0" cy="54" r="7.5" />
        <text x={labelDx(X(shown), 16)} y="22" textAnchor="middle">{fmt(score)}</text>
      </g>
    </svg>
  )
}
