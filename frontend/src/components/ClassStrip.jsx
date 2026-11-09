import styles from './ClassStrip.module.css'
import { oneIn, pct, TICKS, tickLabel } from '../lib/scale'
import { ROW, stripLayout } from '../lib/classStats'

const ZONE_CLASS = { flagged: 'flagged', above_usual: 'above', not_flagged: '' }

/** Every scored essay on the page's one scale (how many student essays score this high or higher). A small class is one dot per essay
 *  (solid over the flag line, amber with a ring in "above usual", hollow under it); a large one, or one where positions crowd together,
 *  is a histogram split by zone. @param {{ entries: { pos: number, zone: 'flagged' | 'above_usual' | 'not_flagged' }[], scale: import('../types').Scale, summary: string }} props */
export default function ClassStrip({ entries, scale, summary }) {
  const layout = stripLayout(entries, scale.cap)
  const t = pct(scale.flag_line, scale.cap), u = pct(scale.above_usual_line, scale.cap)
  const tallest = Math.max(1, ...layout.bars.map((b) => b.flagged + b.above + b.rest))
  return (
    <div className={styles.fit}>
      <div className={`${styles.strip} ${layout.mode === 'bars' ? styles.bars : ''}`} role="img" style={/** @type {any} */ ({ '--t': t, '--u': u, ...(layout.mode === 'dots' ? { height: 150 + layout.extra } : {}) })}
           aria-label={layout.mode === 'bars' ? `Histogram of ${entries.length} essays on the scale of how many student essays score this high or higher. ${summary}` : `Each dot is one essay on the scale of how many student essays score this high or higher. ${summary}`}>
        <div className={styles.zone} />
        <div className={styles.zoneFlag} />
        {layout.mode === 'dots' && layout.dots.map((d, i) => (
          <i key={i} className={`${styles.dot} ${styles[ZONE_CLASS[d.zone]] ?? ''}`} style={/** @type {any} */ ({ left: `${d.pos}%`, bottom: 44 + d.stack * ROW, '--n': i })} />
        ))}
        {layout.mode === 'bars' && (
          <div className={styles.columns}>
            {layout.bars.map((b, i) => (
              <div key={i} className={styles.column} style={{ height: `${((b.flagged + b.above + b.rest) / tallest) * 100}%` }}>
                {b.flagged > 0 && <i className={styles.over} style={{ flexGrow: b.flagged }} />}
                {b.above > 0 && <i className={styles.mid} style={{ flexGrow: b.above }} />}
                {b.rest > 0 && <i className={styles.under} style={{ flexGrow: b.rest }} />}
              </div>
            ))}
          </div>
        )}
        <div className={styles.axis} />
        {layout.mode === 'dots' && TICKS.map((v) => (
          <span key={v} className={`${styles.tickWrap} ${v === 0 ? styles.first : ''}`} style={{ left: `${pct(v, scale.cap)}%` }}><i className={styles.tick} /><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span></span>
        ))}
        {layout.mode === 'bars' && <><span className={`${styles.end} ${styles.endLeft} num`}>1 in 1</span><span className={`${styles.end} ${styles.endRight} num`}>Off the scale</span></>}
        <i className={styles.flagLine} />
        {layout.mode === 'dots' && <p className={`${styles.flagLabel} num`}>Flag line · {oneIn(scale.tau_flag)}</p>}
      </div>
    </div>
  )
}
