import { useMemo, useRef } from 'react'
import styles from './ComparePanes.module.css'
import { diffByParagraph } from '../lib/diff'

/** The original essay and the rewrite side by side. The two panes scroll together, and the words the rewrite changed are
 *  underlined in the right-hand one. Each is keyboard-focusable so it can be scrolled without a mouse.
 *  @param {{ original: string, edited: string, left: { title: string, score: string }, right: { title: string, score: string } }} props */
export default function ComparePanes({ original, edited, left, right }) {
  const panes = useRef(/** @type {(HTMLDivElement | null)[]} */ ([null, null]))
  const syncing = useRef(false)
  const diff = useMemo(() => diffByParagraph(original, edited), [original, edited])
  const originalParagraphs = original.split(/\n[ \t]*\n+/).filter((p) => p.trim())

  // keep the same relative position in both panes (a share of the scrollable height, since the two texts differ in length)
  const sync = (/** @type {number} */ from) => {
    if (syncing.current) { syncing.current = false; return }
    const src = panes.current[from], dst = panes.current[1 - from]
    if (!src || !dst) return
    const share = src.scrollTop / Math.max(1, src.scrollHeight - src.clientHeight)
    syncing.current = true
    dst.scrollTop = share * (dst.scrollHeight - dst.clientHeight)
  }

  return (
    <div className={styles.pair}>
      <article aria-label="Original essay" className={styles.sheet}>
        <p className={styles.head}><span>{left.title}</span><span className={`${styles.score} num`}>{left.score}</span></p>
        <div className={styles.pane} tabIndex={0} aria-label="Original essay text, scrollable" ref={(el) => { panes.current[0] = el }} onScroll={() => sync(0)}>
          {originalParagraphs.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      </article>
      <article aria-label="Rewritten essay" className={styles.sheet}>
        <p className={styles.head}><span>{right.title}</span><span className={`${styles.score} num`}>{right.score}</span></p>
        <div className={styles.pane} tabIndex={0} aria-label="Rewritten essay text, scrollable" ref={(el) => { panes.current[1] = el }} onScroll={() => sync(1)}>
          {diff.map((ops, i) => (
            <p key={i}>
              {ops.filter(([op]) => op !== '-').map(([op, word], k) => (
                <span key={k}>{k > 0 ? ' ' : ''}{op === '+' ? <ins>{word}</ins> : word}</span>
              ))}
            </p>
          ))}
        </div>
      </article>
    </div>
  )
}
