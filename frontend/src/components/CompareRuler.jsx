import styles from './CompareRuler.module.css'
import { oneIn, pct, position, scoreWords, TICKS, tickLabel, ZONE_WORD } from '../lib/scale'

/** The scale on the Try to fool it page: the original verdict as a hollow marker, the rewritten one as a filled marker, joined by a dashed
 *  line. While the rewrite is being scored the "after" marker waits, hollow and dashed, at the old place and moves to the new one when the
 *  answer arrives. The scale is the page's one scale (how many student essays score this high or higher), with the same two zones.
 *  Everything moves with transform only.
 *  @param {{ scale: import('../types').Scale, before: { zone: string, p: number }, after: { zone: string, p: number } | null }} props  after = null while waiting or before any run */
export default function CompareRuler({ scale, before, after }) {
  const at = (/** @type {number} */ p) => pct(position(p, scale.cap), scale.cap)
  const b = at(before.p), a = after == null ? b : at(after.p)
  const t = pct(scale.flag_line, scale.cap), u = pct(scale.above_usual_line, scale.cap)
  const word = (/** @type {{ zone: string, p: number }} */ v) => `${ZONE_WORD[/** @type {'flagged'} */ (v.zone)].toLowerCase()}, ${scoreWords(v.p, scale.val_humans)}`
  const desc = after == null
    ? `The original essay is ${word(before)}. The flag line is at ${oneIn(scale.tau_flag, scale.val_humans)}.`
    : `The verdict moved from ${word(before)} to ${word(after)}. The flag line is at ${oneIn(scale.tau_flag, scale.val_humans)}.`
  return (
    <div className={styles.fit}>
      <div className={styles.ruler} role="img" aria-label={desc} style={/** @type {any} */ ({ '--t': t, '--u': u, '--b': b, '--a': a, '--lo': Math.min(a, b), '--span': Math.abs(a - b) })}>
        <div className={styles.zone} />
        <div className={styles.zoneFlag} />
        <div className={styles.axis} />
        {TICKS.map((v) => (
          <span key={v} className={`${styles.tickWrap} ${v === 0 ? styles.first : ''}`} style={{ left: `${pct(v, scale.cap)}%` }}>
            <i className={styles.tick} /><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span>
          </span>
        ))}
        <i className={styles.flagLine} />
        <p className={`${styles.flagLabel} num`}>Flag line · {oneIn(scale.tau_flag, scale.val_humans)}</p>
        <svg className={styles.link} viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true">
          <line x1="0" y1="1" x2="100" y2="1" vectorEffect="non-scaling-stroke" />
        </svg>
        <i className={styles.before} />
        <i className={`${styles.after} ${after == null ? styles.waiting : ''}`} />
        {after != null && <p className={`${styles.afterLabel} num`}>After: {ZONE_WORD[/** @type {'flagged'} */ (after.zone)].toLowerCase()}</p>}
        <p className={`${styles.beforeLabel} num`}>Before: {ZONE_WORD[/** @type {'flagged'} */ (before.zone)].toLowerCase()}</p>
      </div>
    </div>
  )
}
