// The three real pages are built in later phases; until then the navigation needs somewhere to go.
/** @param {{ title: string, phase: number | string }} props */
export default function Placeholder({ title, phase }) {
  return (
    <div className="wrap" style={{ padding: '56px clamp(16px, 4vw, 40px) 96px' }}>
      <h1 className="t-display" style={{ maxWidth: '16ch' }}>{title}</h1>
      <p style={{ marginTop: 16, color: 'var(--ink-2)', maxWidth: '56ch' }}>This page is built in phase {phase}. The components it will use are on the <a href="/components">components sheet</a>.</p>
    </div>
  )
}
