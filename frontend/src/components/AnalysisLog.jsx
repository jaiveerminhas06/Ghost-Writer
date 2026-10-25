// Step-by-step status with live timings, instead of a spinner. Highlights can take up to a minute on a CPU host.
export default function AnalysisLog({ steps, elapsed }) {
  return (
    <ul className="log" aria-label="Analysis progress">
      {steps.map((s) => (
        <li key={s.key} className={s.state}>
          <span className="mark" aria-hidden="true" />
          <span>{s.text}{s.state === 'skipped' && ' · skipped, only for flagged essays'}</span>
          <span className="t">{s.state === 'done' && s.ms != null ? `${(s.ms / 1000).toFixed(1)} s` : s.state === 'active' ? `${(elapsed / 1000).toFixed(1)} s` : ''}</span>
        </li>
      ))}
    </ul>
  )
}
