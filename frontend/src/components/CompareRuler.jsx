import styles from './CompareRuler.module.css'
import { fmt } from '../lib/format'
import { rulerPos } from '../lib/verdict'

const TICKS = [-10, -5, 0, 5, 10]
const tickLabel = (/** @type {number} */ v) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0')
const spoken = (/** @type {number} */ v) => `${v < 0 ? 'minus' : 'plus'} ${Math.abs(v).toFixed(1)}`

/** The ruler on the Try to fool it page: the original score as a hollow marker, the rewritten score as a filled one, joined by a
 *  dashed line. While the rewrite is being scored the "after" marker waits, hollow and dashed, at the old score and moves to
 *  the new one when the answer arrives. Everything moves with transform only.
 *  @param {{ before: number, after: number | null, threshold: number, flagLabel: string, strictness: string }} props  after = null while waiting or before any run */
export default function CompareRuler({ before, after, threshold, flagLabel, strictness }) {
  const b = rulerPos(before), a = after == null ? b : rulerPos(after), t = rulerPos(threshold)
  const desc = after == null
    ? `The original essay scores ${spoken(before)}. The ${strictness} flag line is at ${spoken(threshold)}.`
    : `Score moved from ${spoken(before)} to ${spoken(after)}. The ${strictness} flag line is at ${spoken(threshold)}.`
  return (
    <div className={styles.fit}>
      <div className={styles.ruler} role="img" aria-label={desc} style={/** @type {any} */ ({ '--t': t, '--b': b, '--a': a, '--lo': Math.min(a, b), '--span': Math.abs(a - b) })}>
        <div className={styles.zone} />
        <div className={styles.axis} />
        {TICKS.map((v) => (
          <span key={v} className={`${styles.tickWrap} ${Math.abs(v) === 5 ? styles.mid : ''}`} style={{ left: `${rulerPos(v)}%` }}>
            <i className={styles.tick} /><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span>
          </span>
        ))}
        <i className={styles.flagLine} />
        <p className={`${styles.flagLabel} num`}>{flagLabel} {fmt(threshold)}</p>
        <svg className={styles.link} viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true">
          <line x1="0" y1="1" x2="100" y2="1" vectorEffect="non-scaling-stroke" />
        </svg>
        <i className={styles.before} />
        <i className={`${styles.after} ${after == null ? styles.waiting : ''}`} />
        {after != null && <p className={`${styles.afterLabel} num`}>After {fmt(after)}</p>}
        <p className={`${styles.beforeLabel} num`}>Before {fmt(before)}</p>
      </div>
    </div>
  )
}
