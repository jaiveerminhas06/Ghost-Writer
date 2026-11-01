import { Link } from 'react-router-dom'
import styles from './EssayRow.module.css'
import { ChevronRight } from './Icons'

/** One essay in a list: file name (ends in an ellipsis if long), score, result, and a chevron saying "open".
 *  tone: rest | flagged | selected | queued | error. `to` makes the whole row a link. `label` adds a first column naming the
 *  state; only the /components sheet uses it. force="hover" draws the hover state without the pointer. */
/** @param {{ name: string, score: string, result: string, tone?: 'rest'|'flagged'|'selected'|'queued'|'error', to?: string, label?: string, force?: 'hover', onClick?: (e: any) => void }} props */
export default function EssayRow({ name, score, result, tone = 'rest', to, label, force, onClick }) {
  const common = { className: `${styles.row} ${label ? styles.labelled : ''}`, 'data-tone': tone, 'data-force': force }
  const cells = (
    <>
      {label && <span className={styles.state}>{label}</span>}
      <span className={styles.name} title={name}>{name}</span>
      <span className={`${styles.score} num`}>{score}</span>
      <span className={styles.result}>{result}</span>
      <span className={styles.open} aria-hidden="true"><ChevronRight /></span>
    </>
  )
  if (to) return <Link to={to} {...common}>{cells}</Link>
  if (onClick) return <div role="button" tabIndex={0} onClick={onClick} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick(e)} {...common}>{cells}</div>
  return <div {...common}>{cells}</div>
}
