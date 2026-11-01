import { useState } from 'react'
import styles from './PenCompare.module.css'
import Button from '../components/Button'
import Field from '../components/Field'
import MethodCards from '../components/MethodCards'
import EssayRow from '../components/EssayRow'

/* TEMPORARY: compares two candidate pen colours side by side (decision pending). Delete this file, its CSS and its
   use in ComponentsSheet.jsx once the pen colour is chosen. */
const OPTIONS = [
  { id: 'a', name: 'Hue 265 (current)', pen: 'oklch(0.45 0.17 265)' },
  { id: 'b', name: 'Hue 255, chroma 0.16', pen: 'oklch(0.45 0.16 255)' },
]
const CARDS = [{ id: 'x', title: 'Typos in 5% of words', cost: 'Instant, on this machine', desc: 'Swaps or doubles letters in one word in twenty.', result: 'Last run: +9.1 to +3.3' }]

function Sample({ pen }) {
  return (
    <div className={styles.scope} style={/** @type {any} */ ({ '--pen': pen })}>
      <div className={styles.row}>
        <Button variant="primary">Score essay</Button>
        <Button variant="primary" force="hover">Hover</Button>
        <Button force="focus">Focus ring</Button>
      </div>
      <nav className={styles.tabs} aria-hidden="true"><span className={styles.current}>Check an essay</span><span>Try to fool it</span></nav>
      <div className={styles.ruler} aria-hidden="true">
        <span className={styles.zone} /><span className={styles.line} /><span className={styles.flag}>Flag line +7.8</span>
      </div>
      <p className={styles.note}>The sentence I lean on most. Take it out and the score falls further than for any other.</p>
      <p>A link in body text: <a href="#compare">How it was chosen (notebook 09)</a></p>
      <MethodCards label="sample" methods={CARDS} value="x" onChange={() => {}} />
      <div className={styles.rows}><EssayRow tone="selected" name="essay_22_nguyen.txt" score="+5.1" result="Flagged, standard only" /><EssayRow tone="flagged" name="essay_04_okafor.docx" score="+8.4" result="Flagged, strict" /></div>
      <Field label="Essay" force="focus" rows={2} value="A driverless car is a scary concept." onChange={() => {}} />
    </div>
  )
}

export default function PenCompare() {
  const [page, setPage] = useState('a')
  const choose = (o) => { setPage(o.id); document.documentElement.style.setProperty('--pen', o.pen) }
  return (
    <section aria-labelledby="pen" className={styles.compare}>
      <div className={styles.head}>
        <h2 id="pen" className="t-section">Pen colour: two candidates</h2>
        <p>Temporary. Both panels derive hover, pressed, tint and ring from their own pen colour. The buttons switch the colour of this whole page.</p>
        <div className={styles.row}>
          {OPTIONS.map((o) => <Button key={o.id} aria-pressed={page === o.id} onClick={() => choose(o)}>{`Whole page: ${o.name}`}</Button>)}
        </div>
      </div>
      <div className={styles.pair}>
        {OPTIONS.map((o) => <div key={o.id}><h3 className="t-heading">{o.name}</h3><Sample pen={o.pen} /></div>)}
      </div>
    </section>
  )
}
