import styles from './ClassStrip.module.css'
import { fmt } from '../lib/format'
import { rulerPos } from '../lib/verdict'
import { ROW, stripLayout } from '../lib/classStats'

const TICKS = [-10, -5, 0, 5, 10]
const tickLabel = (/** @type {number} */ v) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0')

/** Every scored essay on the score scale. A small class is one dot per essay (filled and blue over the flag line, hollow under it);
 *  a large one, or one where scores crowd together, is a histogram of half-point columns. The flag line and its yellow zone slide
 *  with transform when the setting changes. @param {{ scores: number[], threshold: number, summary: string }} props */
export default function ClassStrip({ scores, threshold, summary }) {
  const layout = stripLayout(scores, threshold)
  const t = rulerPos(threshold)
  const tallest = Math.max(1, ...layout.bars.map((b) => b.over + b.under))
  return (
    <div className={styles.fit}>
      <div className={`${styles.strip} ${layout.mode === 'bars' ? styles.bars : ''}`} role="img" style={/** @type {any} */ ({ '--t': t, ...(layout.mode === 'dots' ? { height: 150 + layout.extra } : {}) })}
           aria-label={layout.mode === 'bars' ? `Histogram of ${scores.length} essay scores from minus 10 to plus 10. ${summary}` : `Each dot is one essay on the score scale from minus 10 to plus 10. ${summary}`}>
        <div className={styles.zone} />
        {layout.mode === 'dots' && layout.dots.map((d, i) => (
          <i key={i} className={`${styles.dot} ${d.flagged ? styles.flagged : ''}`} style={/** @type {any} */ ({ left: `${d.pos}%`, bottom: 44 + d.stack * ROW, '--n': i })} />
        ))}
        {layout.mode === 'bars' && (
          <div className={styles.columns}>
            {layout.bars.map((b, i) => (
              <div key={i} className={styles.column} style={{ height: `${((b.over + b.under) / tallest) * 100}%` }}>
                {b.over > 0 && <i className={styles.over} style={{ flexGrow: b.over }} />}
                {b.under > 0 && <i className={styles.under} style={{ flexGrow: b.under }} />}
              </div>
            ))}
          </div>
        )}
        <div className={styles.axis} />
        {layout.mode === 'dots' && TICKS.map((v) => (
          <span key={v} className={styles.tickWrap} style={{ left: `${rulerPos(v)}%` }}><i className={styles.tick} /><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span></span>
        ))}
        {layout.mode === 'bars' && <><span className={`${styles.end} ${styles.endLeft} num`}>−10</span><span className={`${styles.end} ${styles.endRight} num`}>+10</span></>}
        <i className={styles.flagLine} />
        {layout.mode === 'dots' && <p className={`${styles.flagLabel} num`}>Flag line {fmt(threshold)}</p>}
      </div>
    </div>
  )
}
