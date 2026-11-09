import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './CheckClass.module.css'
import Button from '../components/Button'
import ClassStrip from '../components/ClassStrip'
import ClassTable from '../components/ClassTable'
import DemoClassOption from '../components/DemoClassOption'
import DropZone from '../components/DropZone'
import MetaGate from '../components/MetaGate'
import { useClass, useEssay } from '../state/contexts'
import { MIN_CLASS, paginate, sortItems, summarize } from '../lib/classStats'
import { crossing, expectedFlags, knownAuthors } from '../lib/figures'
import { position } from '../lib/scale'

const DEFAULT_TYPES = ['.docx', '.pdf', '.txt']

/** Check a class: add a set of essay files, see the pattern across the class, and open any one of them. */
export default function CheckClass() {
  return <MetaGate>{(meta) => <Loaded meta={meta} />}</MetaGate>
}

/** @param {{ meta: import('../types').Meta }} props */
function Loaded({ meta }) {
  const cls = useClass()
  const essay = useEssay()
  const navigate = useNavigate()
  const input = useRef(/** @type {HTMLInputElement | null} */ (null))
  const [sort, setSort] = useState(/** @type {'desc' | 'asc'} */ ('desc'))
  const [page, setPage] = useState(0)
  const [seenReveal, setSeenReveal] = useState(cls.reveal)

  const scale = meta.jury.scale
  const minWords = meta.limits?.min_words ?? 40
  const sum = summarize(cls.items)
  const sorted = useMemo(() => sortItems(cls.items, sort), [cls.items, sort])
  const view = paginate(sorted, page)
  const entries = cls.items.filter((i) => i.status === 'done' && i.verdict).map((i) => ({ pos: position(/** @type {{ p: number }} */ (i.verdict).p, scale.cap), zone: /** @type {'flagged'} */ (/** @type {{ zone: string }} */ (i.verdict).zone) }))
  const only = sum.scored === 1 ? cls.items.find((i) => i.status === 'done') : undefined

  // the toast's "Show" button: go to the last page (failed files sort to the end) and bring the first one into view
  if (seenReveal !== cls.reveal) { setSeenReveal(cls.reveal); setPage(Number.MAX_SAFE_INTEGER) }
  useEffect(() => {
    if (cls.reveal) document.querySelector('[data-first-error]')?.scrollIntoView({ block: 'center', behavior: 'auto' })
  }, [cls.reveal, view.page])

  const open = (/** @type {{ name: string, text: string | null }} */ item) => { essay.openEssay({ name: item.name, text: item.text ?? '' }); navigate('/') }
  const headline = crossing(sum.flagged, sum.above, sum.scored)
  const known = knownAuthors(cls.items, cls.labels, meta)
  const demoOn = cls.items.length > 0 && cls.items.every((i) => cls.labels[i.name]) ? cls.demoTopic : null   // a demo class, and only that, is on the page
  const caption = sum.pending > 0 ? `Scoring ${sum.scored + sum.errors} of ${sum.files} files…` : `${sum.files} ${sum.files === 1 ? 'file' : 'files'}, ${sum.scored} scored.`

  return (
    <div className={`wrap ${styles.page}`}>
      <div className={styles.top}>
        <div className={styles.intro}>
          <h1 className="t-display">Check a class</h1>
          <p>Score a whole set of essays at once. The point is the pattern across a class, and how many flags you’d get even if nobody used AI.</p>
          {meta.demo_classes && meta.demo_classes.length > 0 && <div className={styles.demo}><DemoClassOption classes={meta.demo_classes} selected={demoOn} disabled={cls.working} onLoad={cls.loadDemo} /></div>}
        </div>
        <DropZone inputRef={input} onFiles={cls.addFiles} hasFiles={cls.items.length > 0} accept={meta.limits?.file_types ?? DEFAULT_TYPES} />
      </div>
      {cls.notice && <p className={styles.notice} role="status">{cls.notice}</p>}

      {sum.scored >= MIN_CLASS && (
        <section aria-labelledby="summary" className={styles.summary}>
          <div className={styles.summaryTop}>
            <div className={styles.summaryText}>
              <p className={styles.caption} aria-live="polite">{caption}</p>
              <h2 id="summary" className="t-verdict num">{headline}</h2>
              <p>{expectedFlags(meta, sum.scored)}</p>
              {known && <p className={styles.known}>{known}</p>}
            </div>
          </div>
          <ClassStrip entries={entries} scale={scale} summary={headline} />
        </section>
      )}

      {sum.scored > 0 && sum.scored < MIN_CLASS && (
        <section className={styles.card} aria-labelledby="few">
          <h2 id="few" className={styles.cardTitle}>{sum.scored === 1 ? 'You added one essay.' : `You added ${sum.scored} essays.`}</h2>
          <p>A class summary needs at least {MIN_CLASS} to say anything. {sum.scored === 1 ? 'Check this one on its own' : 'Open any of them to check it on its own'}, or add more files.</p>
          <div className={styles.actions}>
            {only && <Button variant="primary" onClick={() => open(only)}>Check it on its own</Button>}
            <Button onClick={() => input.current?.click()}>Add files</Button>
          </div>
        </section>
      )}

      {sum.scored === 0 && sum.pending === 0 && sum.errors > 0 && (
        <section className={styles.card} aria-labelledby="none">
          <h2 id="none" className={styles.cardTitle}>None of these files could be scored.</h2>
          <p>The reason for each is in the list below. Add .docx, .pdf or .txt files that hold at least {minWords} words of English text.</p>
          <div className={styles.actions}><Button variant="primary" onClick={() => input.current?.click()}>Add files</Button></div>
        </section>
      )}

      {cls.items.length > 0 && (
        <section aria-labelledby="essays" className={styles.essays}>
          <div className={styles.essaysHead}>
            <h2 id="essays" className="t-section">Essays</h2>
            <p>{sum.scored > 0 ? 'Open an essay to see which sentences drove its score.' : caption}</p>
            <Button variant="quiet" onClick={cls.clear}>Clear this class</Button>
          </div>
          <ClassTable rows={view.rows} sort={sort} onSort={() => setSort((s) => (s === 'desc' ? 'asc' : 'desc'))}
                      onOpen={open} minWords={minWords} paging={view} onPage={setPage} />
        </section>
      )}

      <p className={styles.promise}>Scores are kept on this computer and cleared when you close the tab. The files themselves are read in memory and never saved. Ghost Writer is a course project: use a flag to start a conversation with a student, never to decide a grade.</p>
    </div>
  )
}
