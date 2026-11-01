import styles from './MethodCards.module.css'

/** Rewrite methods as a radio group. Each card is title, cost, description, last result; the cards share rows (CSS subgrid), so
 *  titles, costs, descriptions and results line up even when one description is longer. Arrow keys move the choice, as a real
 *  radio group does. A card with `unavailable` is dashed and says why. */
/** @param {{ label: string, methods: { id: string, title: string, cost: string, desc: string, result: string, unavailable?: string }[], value: string | null, onChange: (id: string) => void, force?: string }} props */
export default function MethodCards({ label, methods, value, onChange, force }) {
  const usable = methods.filter((m) => !m.unavailable)
  const move = (e, id) => {
    const i = usable.findIndex((m) => m.id === id)
    const step = /** @type {Record<string, number>} */ ({ ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 })[e.key]
    if (!step) return
    e.preventDefault()
    const next = usable[(i + step + usable.length) % usable.length]
    onChange(next.id)
    e.currentTarget.parentElement.querySelector(`[data-id="${next.id}"]`)?.focus()
  }
  return (
    <div role="radiogroup" aria-label={label} className={styles.group}>
      {methods.map((m) => {
        const checked = value === m.id
        return (
          <div key={m.id} role="radio" data-id={m.id} aria-checked={checked} aria-disabled={m.unavailable ? true : undefined}
               tabIndex={m.unavailable ? -1 : checked ? 0 : (value == null && m === usable[0] ? 0 : -1)}
               className={styles.card} data-force={force === m.id ? 'focus' : undefined}
               onClick={() => { if (!m.unavailable) onChange(m.id) }}
               onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); if (!m.unavailable) onChange(m.id) } else move(e, m.id) }}>
            <p className={styles.title}>{m.title}</p>
            <p className={`${styles.cost} num`}>{m.cost}</p>
            <p className={styles.desc}>{m.unavailable || m.desc}</p>
            <p className={`${styles.result} num`}>{m.result}</p>
          </div>
        )
      })}
    </div>
  )
}
