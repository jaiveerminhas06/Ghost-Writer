import { useEffect, useId, useRef, useState } from 'react'
import styles from './EssayPaper.module.css'
import Button from './Button'
import { Check, Copy } from './Icons'
import { layoutEssay } from '../lib/essayLayout'
import { marginNotes } from '../lib/notes'
import { wordCountText, words } from '../lib/format'
import { useToast } from '../lib/toast'

const COPY_FAILED = "Couldn't copy. Select the text and copy it yourself."

/** The paper in edit mode: the essay typeface, a live word count, and the one primary action. Under 40 words the count says how
 *  far there is to go (a bar and "8 more to go"), not an error. Cmd or Ctrl + Enter also scores.
 *  @param {{ text: string, onChange: (t: string) => void, onSubmit: () => void, minWords: number, disabledReason?: string | null }} props */
export function EssayEditor({ text, onChange, onSubmit, minWords, disabledReason = null }) {
  const id = useId()
  const n = words(text).length
  const ready = n >= minWords && !disabledReason
  return (
    <section className={styles.sheet} aria-label="The essay">
      <div className={styles.editor}>
        <label htmlFor={id} className={styles.editLabel}>Essay</label>
        <textarea id={id} className={styles.input} value={text} spellCheck={false} rows={8}
                  placeholder="Paste an essay of at least 40 words, or load one of the examples."
                  aria-describedby={`${id}-count`}
                  onChange={(e) => onChange(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ready) onSubmit() }} />
        <div className={styles.editFoot}>
          <div className={styles.count}>
            {n > 0 && n < minWords && <div className={styles.bar} aria-hidden="true"><i style={{ width: `${(n / minWords) * 100}%` }} /></div>}
            <p id={`${id}-count`} className="num" aria-live="polite">{wordCountText(n, minWords)}</p>
          </div>
          <Button variant="primary" disabled={!ready} onClick={onSubmit}>Score essay</Button>
        </div>
      </div>
    </section>
  )
}

/** Put each margin note beside the sentence it is about. Notes are in a column next to the paragraph; this measures where the
 *  sentence sits and writes --note-top on each note. It writes straight to the DOM (no React state), so nothing re-renders.
 *  @param {{ current: HTMLElement | null }} row */
function useNotePositions(row) {
  useEffect(() => {
    const el = row.current
    if (!el) return
    const place = () => {
      const textTop = /** @type {HTMLElement} */ (el.querySelector('[data-text]')).getBoundingClientRect().top
      let stackEnd = 0                                   // bottom of the notes placed so far, measured from the top of the notes column
      const noteEls = /** @type {NodeListOf<HTMLElement>} */ (el.querySelectorAll('[data-note]'))
      noteEls.forEach((note, i) => {
        const anchor = el.querySelector(`mark[data-sentence="${note.dataset.sentence}"]`)
        const wanted = anchor ? anchor.getBoundingClientRect().top - textTop : 0       // where the sentence starts
        const margin = Math.max(wanted - stackEnd, i === 0 ? 0 : 12)                   // never closer than 12 px to the note above
        note.style.setProperty('--note-top', `${Math.round(margin)}px`)
        stackEnd += margin + note.offsetHeight
      })
    }
    place()
    const ro = new ResizeObserver(place)
    ro.observe(el)
    return () => ro.disconnect()
  }, [row])
}

/** @param {{ para: import('../lib/essayLayout').Paragraph, notes: import('../lib/notes').Note[], showCut: boolean }} props */
function ParagraphRow({ para, notes, showCut }) {
  const row = useRef(/** @type {HTMLDivElement | null} */ (null))
  useNotePositions(row)
  const render = (/** @type {import('../lib/essayLayout').Piece[]} */ pieces) => pieces.map((p) => {
    if (p.tier > 0) return <mark key={p.start} data-tier={p.tier} data-sentence={p.sentence}>{p.text}</mark>
    return p.dim ? <span key={p.start} className={styles.dim}>{p.text}</span> : <span key={p.start}>{p.text}</span>
  })
  const cut = para.cutAt
  const before = cut === null ? para.pieces : para.pieces.slice(0, cut)
  const after = cut === null ? [] : para.pieces.slice(cut)
  return (
    <div className={styles.row} ref={row}>
      <div className={styles.textCol} data-text>
        {before.length > 0 && <p className={styles.para}>{render(before)}</p>}
        {showCut && (
          <div className={styles.cut}><i /><p>I stopped reading here, at 512 tokens.</p></div>
        )}
        {after.length > 0 && <p className={`${styles.para} ${before.length ? styles.rest : ''}`}>{render(after)}</p>}
      </div>
      <div className={styles.notesCol}>
        {notes.map((n) => <p key={n.id} className={styles.note} data-note data-sentence={n.sentence}>{n.text}</p>)}
      </div>
    </div>
  )
}

/** The paper in read mode: the essay with marks, margin notes, and (for a long essay) the line where reading stopped.
 *  @param {{ text: string, title: string, scoreInfo: import('../types').ScoreResult, explain: import('../types').ExplainResult | null,
 *           onEdit: () => void }} props */
export function EssayReader({ text, title, scoreInfo, explain, onEdit }) {
  const toast = useToast()
  const [copied, setCopied] = useState(false)
  const sentences = explain ? explain.sentences : []
  const paragraphs = layoutEssay(text, sentences, scoreInfo.truncated ? scoreInfo.read_chars : text.length)
  const notes = explain ? marginNotes(sentences, explain.method) : []
  const firstCut = paragraphs.findIndex((p) => p.cutAt !== null)
  const noteFor = (/** @type {number} */ i) => notes.filter((n) => paragraphs[i].pieces.some((p) => p.sentence === n.sentence && p.tier > 0))
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true); setTimeout(() => setCopied(false), 1600)
    } catch { toast.show({ kind: 'error', message: COPY_FAILED }) }
  }
  return (
    <article className={styles.sheet} aria-labelledby="essay-title">
      <div className={styles.head}>
        <div className={styles.titles}>
          <h2 id="essay-title" className={styles.title}>{title}</h2>
          <p className={`${styles.caption} num`}>
            {scoreInfo.truncated ? `${scoreInfo.words.toLocaleString('en-US')} words. The score covers the first part only.` : `${scoreInfo.words.toLocaleString('en-US')} words, all of them read`}
          </p>
        </div>
        <div className={styles.actions}>
          <Button onClick={onEdit}>Edit essay</Button>
          <Button variant="icon" aria-label={copied ? 'Copied' : 'Copy essay'} done={copied} onClick={copy}>{copied ? <Check /> : <Copy />}</Button>
        </div>
      </div>
      <div className={styles.body}>
        {paragraphs.map((p, i) => <ParagraphRow key={p.start} para={p} notes={noteFor(i)} showCut={i === firstCut} />)}
      </div>
    </article>
  )
}
