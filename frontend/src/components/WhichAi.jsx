import { useId, useState } from 'react'
import styles from './WhichAi.module.css'
import Button from './Button'

/** "Which AI is it most like?" Shown only for flagged essays, closed by default, and the warning always comes first: attribution
 *  looked excellent on a random split and fell to 0-28% on a source it had never seen (notebook 11), so this is never "model X
 *  wrote it". The guess is fetched the first time the drawer opens.
 *  @param {{ guess: { status: string, data: import('../types').AttributionResult | null, problem: { title: string } | null },
 *           onOpen: () => void, knownHuman: boolean, heldout: string }} props */
export default function WhichAi({ guess, onOpen, knownHuman, heldout }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const toggle = () => { if (!open) onOpen(); setOpen(!open) }
  const range = heldout.replace('–', ' to ')
  return (
    <section aria-labelledby={`${id}-h`} className={styles.panel}>
      <h2 id={`${id}-h`} className="t-heading">Which AI is it most like?</h2>
      <p className={styles.warn}>
        It can’t tell you which model wrote an essay. For a source it never saw, it picked the right family {range} of the time, at or below chance.{' '}
        {knownHuman ? 'Here the flag is a false alarm, so this means nothing at all.' : 'If the flag is a false alarm, this means nothing at all.'}
      </p>
      <div>
        <Button aria-expanded={open} aria-controls={`${id}-body`} onClick={toggle}>
          {open ? 'Hide the guess' : knownHuman ? 'Show the guess anyway' : 'Show the guess'}
        </Button>
      </div>
      <div id={`${id}-body`} className={styles.drawer} data-open={open}>
        <div className={styles.inner} inert={!open}>
          {guess.status === 'loading' && <><div className="skel" style={{ height: 14 }} /><div className="skel" style={{ height: 14, width: '70%' }} /></>}
          {guess.status === 'error' && <p className={styles.problem}>{guess.problem?.title}</p>}
          {guess.status === 'done' && guess.data && guess.data.families.map((f) => (
            <div className={styles.fam} key={f.family}>
              <p>{f.family}-based sources</p>
              <p className="num">{Math.round(f.share * 100)}%</p>
              <div className={styles.track}><i style={{ width: `${f.share * 100}%` }} /></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
