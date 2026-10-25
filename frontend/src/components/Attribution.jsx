import Icon from './Icon'

// "Which training sources does it resemble?" A closed drawer, only for flagged essays. The warning comes BEFORE the
// bars on purpose: notebook 11 showed this only recognises how the training essays were generated, so it is never
// presented as "model X wrote this" (decision of 2026-10-25).
export default function Attribution({ data }) {
  return (
    <details className="drawer">
      <summary>
        Which training sources does it resemble?
        <span className="chip neutral">Not authorship</span>
        <span className="chev"><Icon name="chev" /></span>
      </summary>
      <div className="drawer-body">
        <p className="warn-box">
          <b>This cannot tell you which model wrote the essay.</b> When a whole data source was hidden from training, the right
          family came up only {data.heldout_accuracy} of the time, at or below chance. It recognises how the training essays were
          generated, not the model. If the flag is a false alarm, this panel means nothing.
        </p>
        <div style={{ display: 'grid', gap: 10 }}>
          {data.families.map((f) => (
            <div className="fam" key={f.family}>
              <span>{f.family}</span>
              <span className="track"><i style={{ width: `${f.probability * 100}%` }} /></span>
              <span className="pct">{Math.round(f.probability * 100)}%</span>
            </div>
          ))}
        </div>
      </div>
    </details>
  )
}
