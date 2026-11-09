import { useEffect, useId, useMemo, useRef, useState } from 'react'
import styles from './JuryScale.module.css'
import { markText } from '../lib/jury'
import { layoutScale, oneIn } from '../lib/scale'

const PHONE_BELOW = 560      // a container narrower than this gets the phone layout (Jury.html boards 4 to 6)

/** Width of an element, kept up to date as it resizes. 0 until the first measurement. @param {React.RefObject<HTMLElement | null>} ref */
function useWidth(ref) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    setWidth(el.clientWidth)
    const watch = new ResizeObserver(() => setWidth(el.clientWidth))
    watch.observe(el)
    return () => watch.disconnect()
  }, [ref])
  return width
}

/** The one scale: how many of the student essays we checked score this high or higher. The official verdict is the marker on top; the
 *  twenty detectors hang underneath. Marks that sit on the end of the scale (every detector on a clear AI essay) are stacked in a box
 *  labelled "Off the scale": their order means nothing. Only transform and opacity ever animate: each mark moves with translate (so on
 *  "Re-run the trial" it travels to its new place), drops in with opacity and a 12 px translateY, and the official marker lands last with
 *  the spring. The twenty marks are one tab stop: arrow keys move between them, and the active one is described in the line below.
 *  @param {{ scale: import('../types').Scale, marks: import('../types').JurorMark[], official: { p: number } | null, activeSeed: number | null,
 *    onActive: (seed: number | null) => void, label: string, noun?: string, names?: Record<number, string> }} props   noun/names: the same scale draws the essays of a class (one mark per essay, named by file) */
export default function JuryScale({ scale, marks, official, activeSeed, onActive, label, noun = 'detector', names }) {
  const box = useRef(/** @type {HTMLDivElement | null} */ (null))
  const width = useWidth(box)
  const id = useId()
  const phone = width > 0 && width < PHONE_BELOW
  const L = useMemo(() => (width > 0 ? layoutScale({ width, scale, marks, official, phone }) : null), [width, scale, marks, official, phone])
  const refs = useRef(/** @type {Map<number, SVGGElement>} */ (new Map()))
  const stop = marks.some((m) => m.seed === activeSeed) ? activeSeed : (marks[0]?.seed ?? null)    // the one mark that is in the tab order

  const onKey = (/** @type {React.KeyboardEvent} */ e) => {
    const i = marks.findIndex((m) => m.seed === stop)
    const to = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: marks.length - 1 }[/** @type {'Home'} */ (e.key)]
    if (to === undefined || !marks.length) return
    e.preventDefault()
    const next = marks[Math.min(marks.length - 1, Math.max(0, to))]
    onActive(next.seed)
    refs.current.get(next.seed)?.focus()
  }

  if (!L) return <div ref={box} className={styles.box} />
  const cls = (/** @type {string} */ name) => `${styles[name]}${phone ? ` ${styles.phone}` : ''}`
  const place = (/** @type {number} */ x, /** @type {number} */ y) => ({ transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)` })
  const dot = (/** @type {{ mark: import('../types').JurorMark, cx: number, cy: number }} */ d, /** @type {number} */ i) => {
    const m = d.mark
    const active = m.seed === activeSeed
    return (
      <g key={m.seed} className={styles.mark} style={place(d.cx, d.cy)} role="listitem" aria-label={markText(m, scale.val_humans, names?.[m.seed])}
         tabIndex={m.seed === stop ? 0 : -1} data-zone={m.zone} data-seed={m.seed} ref={(el) => { if (el) refs.current.set(m.seed, el); else refs.current.delete(m.seed) }}
         onFocus={() => onActive(m.seed)} onBlur={() => onActive(null)} onPointerEnter={() => onActive(m.seed)} onPointerLeave={() => { if (document.activeElement?.getAttribute('data-seed') !== String(m.seed)) onActive(null) }}>
        <circle r={L.r + 6} className={styles.hit} />
        <g className={styles.drop} style={/** @type {any} */ ({ '--i': i })}>
          {m.ensemble_member && <circle r={L.r + 3.2} className={styles.ens} />}
          <circle r={L.r} className={styles[m.zone === 'flagged' ? 'flag' : m.zone === 'above_usual' ? 'above' : 'not']} />
          {active && <circle r={L.r + 6.5} className={styles.ring} />}
        </g>
      </g>
    )
  }
  const o = L.official
  const pile = L.pile
  return (
    <div ref={box} className={styles.box}>
      <svg className={styles.svg} width={L.W} height={L.H} viewBox={`0 0 ${L.W} ${L.H}`} role="group" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{label}</title>
        <g aria-hidden="true">
          {/* on a phone the bands are too narrow to centre both names: "Above usual" ends at the flag line and "Flagged" starts just after it */}
          <text x={phone ? L.xf - 3 : (L.xa + L.xf) / 2} y={L.zoneY} textAnchor={phone ? 'end' : 'middle'} className={cls('zone')}>Above usual</text>
          <text x={phone ? L.xf + 5 : (L.xf + L.AX) / 2} y={L.zoneY} textAnchor={phone ? 'start' : 'middle'} className={cls('zone')}>Flagged</text>
          <rect x={L.xa} y={L.axY - L.band} width={L.xf - L.xa} height={2 * L.band} className={styles.bandAbove} />
          <rect x={L.xf} y={L.axY - L.band} width={L.AX - L.xf} height={2 * L.band} className={styles.bandFlag} />
          <line x1={L.x0} x2={L.AX} y1={L.axY} y2={L.axY} className={styles.axis} />
          {L.ticks.map((t) => (
            <g key={t.t}>
              <line x1={t.x} x2={t.x} y1={L.axY - L.band} y2={L.axY + L.band} className={styles.tick} />
              <line x1={t.x} x2={t.x} y1={L.axY + L.band + 24} y2={L.bottom} className={styles.grid} />
              <text x={t.x + (t.t === 0 ? 2 : 0)} y={L.axY + L.band + 18} textAnchor={t.t === 0 ? 'start' : 'middle'} className={cls('tl')}>{t.label}</text>
            </g>
          ))}
          <line x1={L.AX} x2={L.AX} y1={L.axY - L.band - 4} y2={L.axY + L.band + 4} className={styles.ceiling} />
          <line x1={L.xa} x2={L.xa} y1={L.axY - L.band - 3} y2={L.axY + L.band + 3} className={styles.edge} />
          <line x1={L.xf} x2={L.xf} y1={L.axY - L.band - 6} y2={L.bottom} className={styles.flagLine} />
          <text x={L.xf - 8} y={L.flagLabelY} textAnchor="end" className={cls('flagLabel')}>Flag line{phone ? '' : ` · ${oneIn(scale.tau_flag, scale.val_humans)}`}</text>
          {pile && (
            <>
              <rect x={pile.x} y={pile.y} width={pile.w} height={pile.h} rx="12" className={styles.pile} />
              <path d={phone ? `M${L.AX} ${L.axY + L.band + 6} V${pile.y - 4}` : `M${L.AX} ${L.axY + L.band + 6} V${pile.y + 22} H${pile.x}`} className={styles.bracket} />
              <text x={phone ? L.W : pile.x} y={pile.y + pile.h + 20} textAnchor={phone ? 'end' : 'start'} className={cls('pileText')}>
                <tspan className={styles.pileHead}>Off the scale</tspan>
                {(phone
                  ? [`${L.pileDots.length} of ${marks.length} are off the scale: higher than every`, 'student essay we checked. Order here means nothing.']
                  : [`${L.pileDots.length} of ${marks.length} score higher than`, 'every student essay we checked', `(all ${scale.val_humans.toLocaleString('en-US')}). Stacked: the`, 'order here means nothing.']
                ).map((t) => <tspan key={t} x={phone ? L.W : pile.x} dy={phone ? 16 : 17}>{t}</tspan>)}
              </text>
            </>
          )}
        </g>
        {o && (
          <>
            <g key="official" className={styles.official} style={place(o.x, 0)} aria-hidden="true">
              <g className={styles.land} style={/** @type {any} */ ({ '--from': `${L.x0 - o.x}px` })}>
                <path d={`M-8 ${L.axY - L.band - 21} h16 l-8 12 z`} className={styles.tri} />
                <line x1="0" x2="0" y1={L.axY - L.band - 9} y2={L.axY + L.band} className={styles.stem} />
              </g>
            </g>
            <text x={o.label.x} y={L.axY - L.band - (phone ? 27 : 31)} textAnchor={o.label.anchor} className={cls('official')} aria-hidden="true">{o.text}</text>
          </>
        )}
        <g role="list" aria-label={`The ${marks.length} ${noun}s`} onKeyDown={onKey}>
          {L.dots.map((d, i) => dot(d, i))}
          {L.pileDots.map((d, i) => dot(d, L.dots.length + i))}
        </g>
      </svg>
    </div>
  )
}
