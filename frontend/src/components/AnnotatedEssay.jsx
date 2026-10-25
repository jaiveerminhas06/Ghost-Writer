const signed = (c) => (c >= 0 ? '+' : '−') + Math.abs(c).toFixed(2)

// The original essay text with a <span> around each sentence (positions come from /api/explain) and the text
// between sentences left exactly as typed. Paint strength = contribution ÷ strongest positive contribution;
// under 10% of the strongest gets no paint (same rule as demo/app.py). Paint is a CSS variable (--w) that the
// stylesheet turns into a background colour, so light and dark themes only need different colours.
export default function AnnotatedEssay({ text, data, active, lit, sentenceRefs }) {
  const max = Math.max(1e-6, ...data.sentences.map((s) => Math.max(0, s.contribution ?? 0)))
  const pieces = []
  let last = 0
  data.sentences.forEach((s, i) => {
    pieces.push(text.slice(last, s.start))
    const share = (s.contribution ?? 0) / max
    const w = share < 0.1 ? 0 : ((share - 0.1) / 0.9) * 0.85 + 0.15
    pieces.push(
      <span key={i} ref={(el) => (sentenceRefs.current[i] = el)}
            className={`s${s.contribution == null ? ' beyond' : ''}${active === i ? ' active' : ''}`}
            style={{ '--w': w, '--d': `${Math.min(i * 45, 1300)}ms` }}    // stagger the fade-in, capped at 1.3 s
            title={s.contribution == null ? 'Beyond the 512 tokens the detector reads' : `Contribution ${signed(s.contribution)}`}>
        {text.slice(s.start, s.end)}
      </span>
    )
    last = s.end
  })
  pieces.push(text.slice(last))
  return <p className={`essay${lit ? ' lit' : ''}`}>{pieces}</p>
}
