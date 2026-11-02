import styles from './Ruler.module.css'
import { fmt } from '../lib/format'
import { rulerPos } from '../lib/verdict'

const TICKS = [-10, -5, 0, 5, 10]
const tickLabel = (/** @type {number} */ v) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0')
const spoken = (/** @type {number} */ v) => `${v < 0 ? 'minus' : 'plus'} ${Math.abs(v).toFixed(1)}`

/** The one ruler every score sits on: -10 to +10, the flag line, and the +9.8 ceiling where scores stop.
 *  With no `score` it draws the empty ruler (flag line only) with a dashed marker waiting at the left, which is what the page
 *  shows while the model is still answering. Only transform and opacity ever animate: the flag line and marker slide with
 *  translateX (positions are percentages of the ruler's width, written as cqw), the yellow zone scales from its right edge.
 *  @param {{ score?: number | null, threshold: number, label?: string }} props */
export default function Ruler({ score = null, threshold, label = 'This essay' }) {
  const t = rulerPos(threshold)
  const s = score == null ? 0 : rulerPos(score)
  const desc = `Score scale from minus 10 to plus 10. ${score == null ? 'Waiting for a score.' : `${label} scores ${spoken(score)}.`} The flag line is at ${spoken(threshold)}.`
  return (
    <div className={styles.fit}>
      <div className={styles.ruler} role="img" aria-label={desc} style={/** @type {any} */ ({ '--t': t, '--s': s })}>
        <div className={styles.zone} />
        <div className={styles.axis} />
        {TICKS.map((v) => (
          <span key={v} className={`${styles.tickWrap} ${Math.abs(v) === 5 ? styles.mid : ''}`} style={{ left: `${rulerPos(v)}%` }}>
            <i className={styles.tick} /><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span>
          </span>
        ))}
        <i className={styles.ceiling} />
        <i className={styles.flagLine} />
        <p className={`${styles.flagLabel} num`}>Flag line {fmt(threshold)}</p>
        {score == null
          ? <i className={styles.waiting} />
          : (
            <div className={`${styles.marker} ${s < 50 ? styles.flip : ''}`}>
              <i className={styles.triangle} /><i className={styles.stem} />
              <p className={`${styles.here} num`}>{label} {fmt(score)}</p>
            </div>
          )}
        <p className={styles.capLeft}>More like the student essays</p>
        <p className={styles.capRight}>Scores stop near +9.8</p>
      </div>
    </div>
  )
}
