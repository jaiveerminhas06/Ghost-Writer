import styles from './Segmented.module.css'

/** Two or more options, one chosen (Strict / Standard). The chosen segment is the only raised thing in its track.
 *  Buttons with aria-pressed (not radios) because the choice applies at once and nothing needs submitting. */
/** @param {{ label: string, options: { value: string, label: string }[], value: string, onChange: (v: string) => void, force?: Record<string, 'focus'> }} props */
export default function Segmented({ label, options, value, onChange, force }) {
  return (
    <div role="group" aria-label={label} className={styles.track}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} className={styles.seg}
                data-force={force && force[o.value]} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}
