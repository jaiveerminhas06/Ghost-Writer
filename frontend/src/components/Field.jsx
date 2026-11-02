import { useId } from 'react'
import styles from './Field.module.css'

/** The essay box: a labelled textarea in the essay typeface, a live hint underneath ("12 words. 28 more to go."), and an
 *  error message that says what to do. The error is tied to the textarea with aria-describedby so a screen reader reads it.
 *  force="focus" draws the focus glow on the /components sheet. */
/** @param {{ label: string, value: string, onChange: (e: any) => void, placeholder?: string, hint?: string, error?: string, rows?: number, force?: 'focus', id?: string } & Record<string, any>} props */
export default function Field({ label, value, onChange, placeholder, hint, error, rows = 8, force, id, ...rest }) {
  const auto = useId()
  const fid = id || auto
  const msgId = `${fid}-msg`
  return (
    <div className={styles.field}>
      <label htmlFor={fid} className={styles.label}>{label}</label>
      <textarea id={fid} className={styles.area} value={value} onChange={onChange} placeholder={placeholder} rows={rows}
                data-force={force} aria-invalid={error ? true : undefined} aria-describedby={error || hint ? msgId : undefined} {...rest} />
      {error
        ? <p id={msgId} className={styles.error}>{error}</p>
        : hint && <p id={msgId} className={`${styles.hint} num`} aria-live="polite">{hint}</p>}
    </div>
  )
}

/** A select with its reason for being disabled written underneath (dashed outline, as drawn). */
/** @param {{ label: string, children: any, hint?: string, disabled?: boolean, id?: string } & Record<string, any>} props */
export function SelectField({ label, children, hint, disabled, id, ...rest }) {
  const auto = useId()
  const fid = id || auto
  return (
    <div className={styles.field}>
      <label htmlFor={fid} className={`${styles.label} ${disabled ? styles.muted : ''}`}>{label}</label>
      <select id={fid} className={styles.select} disabled={disabled} aria-describedby={hint ? `${fid}-msg` : undefined} {...rest}>{children}</select>
      {hint && <p id={`${fid}-msg`} className={styles.hint}>{hint}</p>}
    </div>
  )
}
