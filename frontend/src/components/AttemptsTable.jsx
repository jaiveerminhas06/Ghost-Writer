import { useRef } from 'react'
import styles from './AttemptsTable.module.css'
import { useFlip } from '../lib/flip'
import { oneIn, ZONE_WORD } from '../lib/scale'
import { methodOf } from '../lib/fool'

/** Every run on this essay, newest first, the original last. The seed is recorded per row: it is what makes a run repeatable, and
 *  what makes two runs of the same method differ. Pick a row to see that run above.
 *  @param {{ attempts: import('../lib/fool').Attempt[], original: { zone: 'flagged' | 'above_usual' | 'not_flagged', p: number }, selected: number | null, words: number, valHumans: number, onSelect: (id: number | null) => void }} props */
export default function AttemptsTable({ attempts, original, selected, words, valHumans, onSelect }) {
  const table = useRef(/** @type {HTMLDivElement | null} */ (null))
  useFlip(table)                                   // a new attempt enters at the top; the rows below shift down (200 ms)
  const result = (/** @type {'flagged' | 'above_usual' | 'not_flagged'} */ zone) => ZONE_WORD[zone]
  return (
    <div className={styles.scroll}>
      <div className={styles.table} role="table" aria-label="Attempts on this essay" ref={table}>
        <div className={`${styles.row} ${styles.header}`} role="row">
          <span role="columnheader">#</span><span role="columnheader">Method</span><span role="columnheader" className={styles.right}>Seed</span>
          <span role="columnheader" className={styles.right}>Words changed</span><span role="columnheader" className={styles.right}>Students this high</span><span role="columnheader">Result</span>
        </div>
        {[...attempts].reverse().map((a, i) => (
          <button key={a.id} type="button" role="row" data-flip={`a${a.id}`} className={styles.row} aria-pressed={selected === a.id} onClick={() => onSelect(a.id)}>
            <span role="cell" className={styles.muted}>{attempts.length - i}</span>
            <span role="cell" className={styles.method}>{methodOf(a.method).title}</span>
            <span role="cell" className={styles.right}>{a.seed}</span>
            <span role="cell" className={styles.right}>{a.wordsChanged}<span className={styles.of}> of {words}</span></span>
            <span role="cell" className={`${styles.right} ${styles.score}`}>{oneIn(a.p, valHumans)}</span>
            <span role="cell">{result(a.zone)}</span>
          </button>
        ))}
        <button type="button" role="row" data-flip="original" className={`${styles.row} ${styles.origin}`} aria-pressed={selected === null} onClick={() => onSelect(null)}>
          <span role="cell">0</span><span role="cell" className={styles.method}>Original</span><span role="cell" className={styles.right}>–</span>
          <span role="cell" className={styles.right}>0</span><span role="cell" className={`${styles.right} ${styles.score}`}>{oneIn(original.p, valHumans)}</span><span role="cell">{result(original.zone)}</span>
        </button>
      </div>
    </div>
  )
}
