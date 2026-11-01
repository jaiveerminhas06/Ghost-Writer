import { useEffect, useRef } from 'react'
import styles from './ExampleList.module.css'
import { reduceMotion } from '../lib/format'

/** The built-in examples as a radio group. At desktop width it is a list in a well with the word counts; on a phone the same
 *  buttons become sideways-scrolling chips. Arrow keys move the choice (roving tabindex), as a radio group should.
 *  @param {{ examples: import('../types').Example[], value: number | null, onChange: (e: import('../types').Example) => void, disabled?: boolean }} props */
export default function ExampleList({ examples, value, onChange, disabled = false }) {
  const move = (/** @type {KeyboardEvent & { currentTarget: HTMLElement }} */ e, /** @type {number} */ i) => {
    const step = /** @type {Record<string, number>} */ ({ ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 })[e.key]
    if (!step) return
    e.preventDefault()
    const next = (i + step + examples.length) % examples.length
    onChange(examples[next])
    const nextButton = /** @type {HTMLElement | undefined} */ (e.currentTarget.parentElement?.children[next])
    nextButton?.focus()
  }
  // on a phone the chips scroll sideways: keep the chosen one in view
  const list = useRef(/** @type {HTMLDivElement | null} */ (null))
  useEffect(() => {
    const chosen = list.current?.querySelector('[aria-checked="true"]')
    chosen?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: reduceMotion() ? 'auto' : 'smooth' })
  }, [value])
  const tab = (/** @type {number} */ i) => (value === examples[i].id || (value == null && i === 0) ? 0 : -1)
  return (
    <div className={styles.field}>
      <p id="examples" className={styles.label}>Examples</p>
      <div role="radiogroup" aria-labelledby="examples" className={styles.list} ref={list}>
        {examples.map((e, i) => (
          <button key={e.id} type="button" role="radio" aria-checked={value === e.id} tabIndex={tab(i)} disabled={disabled}
                  className={styles.option} onClick={() => onChange(e)} onKeyDown={(ev) => move(/** @type {any} */ (ev), i)}>
            <span>{e.name}</span><span className={`${styles.words} num`}>{e.words} words</span>
          </button>
        ))}
      </div>
    </div>
  )
}
