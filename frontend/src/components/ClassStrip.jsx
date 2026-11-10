import { useState } from 'react'
import styles from './ClassStrip.module.css'
import JuryScale from './JuryScale'
import { markText } from '../lib/jury'
import { atCap, oneIn, pct, tickLabel, TICKS } from '../lib/scale'
import { stripLayout } from '../lib/classStats'

/** Every scored essay on the page's one scale, drawn by the same component as the jurors on Check an essay: a mark per essay (solid in
 *  "flagged", amber with a ring in "above usual", hollow under), the flag line, and the essays that score higher than every student
 *  essay we checked stacked in the "Off the scale" box with their count. A class too large for dots (past 60 essays, or where marks crowd
 *  one column) is a histogram split by zone, with the same axis caption and the same count at the end.
 *  @param {{ entries: { id: number, name: string, p: number, pos: number, zone: 'flagged' | 'above_usual' | 'not_flagged' }[], scale: import('../types').Scale, summary: string }} props */
export default function ClassStrip({ entries, scale, summary }) {
  const layout = stripLayout(entries, scale.cap)
  const [active, setActive] = useState(/** @type {number | null} */ (null))
  const off = entries.filter((e) => atCap(e.p, scale.val_humans)).length
  const caption = <p className={styles.caption}>How many student essays score this high or higher<span className={styles.sub}> (of the {scale.val_humans.toLocaleString('en-US')} we checked)</span></p>
  if (layout.mode === 'dots') {
    const marks = entries.map((e) => ({ seed: e.id, p: e.p, position: e.pos, zone: e.zone, at_cap: atCap(e.p, scale.val_humans), ensemble_member: false }))
    const names = Object.fromEntries(entries.map((e) => [e.id, e.name]))
    const current = marks.find((m) => m.seed === active)
    return (
      <div className={styles.wrap}>
        <JuryScale scale={scale} marks={marks} official={null} activeSeed={active} onActive={setActive} noun="essay" names={names}
                   label={`Each mark is one essay on the scale of how many student essays score this high or higher. ${summary}`} />
        {caption}
        <p className={`${styles.detail} num`} aria-hidden="true">{current ? markText(current, scale.val_humans, names[current.seed]) : 'Hover or focus a mark to read it. Arrow keys move between the essays.'}</p>
      </div>
    )
  }
  const t = pct(scale.flag_line, scale.cap), u = pct(scale.above_usual_line, scale.cap)
  const tallest = Math.max(1, ...layout.bars.map((b) => b.flagged + b.above + b.rest))
  return (
    <div className={styles.wrap}>
      <div className={styles.fit}>
        <div className={`${styles.strip} ${styles.bars}`} role="img" style={/** @type {any} */ ({ '--t': t, '--u': u })}
             aria-label={`Histogram of ${entries.length} essays on the scale of how many student essays score this high or higher. ${off ? `${off} are off the scale: higher than every student essay we checked. ` : ''}${summary}`}>
          <div className={styles.zone} />
          <div className={styles.zoneFlag} />
          <div className={styles.columns}>
            {layout.bars.map((b, i) => (
              <div key={i} className={styles.column} style={{ height: `${((b.flagged + b.above + b.rest) / tallest) * 100}%` }}>
                {b.flagged > 0 && <i className={styles.over} style={{ flexGrow: b.flagged }} />}
                {b.above > 0 && <i className={styles.mid} style={{ flexGrow: b.above }} />}
                {b.rest > 0 && <i className={styles.under} style={{ flexGrow: b.rest }} />}
              </div>
            ))}
          </div>
          <div className={styles.axis} />
          {TICKS.map((v) => <span key={v} className={`${styles.tickWrap} ${styles.barTick} ${v === 0 ? styles.first : ''}`} style={{ left: `${pct(v, scale.cap)}%` }}><span className={`${styles.tickLabel} num`}>{tickLabel(v)}</span></span>)}
          <i className={styles.flagLine} />
        </div>
      </div>
      {caption}
      <p className={styles.detail}>Flag line: {oneIn(scale.tau_flag, scale.val_humans)}.{off ? ` ${off} of ${entries.length} essays are off the scale (higher than all ${scale.val_humans.toLocaleString('en-US')} student essays we checked); they sit in the last column.` : ''}</p>
    </div>
  )
}
