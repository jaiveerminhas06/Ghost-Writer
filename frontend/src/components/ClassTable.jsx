import { useRef } from 'react'
import styles from './ClassTable.module.css'
import { useFlip } from '../lib/flip'
import { PAGE_SIZE } from '../lib/classStats'
import Button from './Button'
import { ChevronDown, ChevronRight } from './Icons'
import { oneIn } from '../lib/scale'
import { resultOf } from '../lib/classStats'

/** The essays in the class: name (ends in an ellipsis if long), words, score (click the heading to sort), and the result. A scored
 *  row is a link that opens that essay on the Check an essay page; a waiting or failed one is not. With more than 50 essays the
 *  rows come in pages. @param {{ rows: import('../lib/classStats').ClassItem[],
 *  sort: 'desc' | 'asc', onSort: () => void, onOpen: (item: import('../lib/classStats').ClassItem) => void, minWords: number,
 *  paging: { page: number, pages: number, from: number, to: number, total: number }, onPage: (page: number) => void }} props */
export default function ClassTable({ rows, sort, onSort, onOpen, minWords, paging, onPage }) {
  const body = useRef(/** @type {HTMLDivElement | null} */ (null))
  useFlip(body, { duration: 220, enter: false, fadeAbove: PAGE_SIZE - 1 })   // sorting glides; a page of 50 only cross-fades
  const firstErrorId = rows.find((r) => r.status === 'error')?.id         // the "Show" button of the toast scrolls to this row
  return (
    <div className={styles.card}>
      <div className={styles.scroll}>
        <div className={styles.table} role="table" aria-label="Essays in this class">
          <div className={`${styles.row} ${styles.header}`} role="row">
            <p role="columnheader" className={styles.pad}>Essay</p>
            <p role="columnheader" className={styles.right}>Words</p>
            <p role="columnheader" className={styles.sortCell} aria-sort={sort === 'desc' ? 'descending' : 'ascending'}>
              <button type="button" className={styles.sort} onClick={onSort}>Students this high <span className={sort === 'asc' ? styles.flip : ''}><ChevronDown /></span></button>
            </p>
            <p role="columnheader" className={styles.right}>Jurors flagging</p>
            <p role="columnheader">Result</p>
            <p role="columnheader"><span className="sr-only">Open</span></p>
          </div>
          <div className={styles.body} ref={body}>
            {rows.map((item) => {
              const res = resultOf(item, minWords)
              const err = res.text
              const mark = item.id === firstErrorId ? { 'data-first-error': true } : {}
              const cells = (
                <>
                  <p role="cell" className={styles.name} title={item.name}>{item.name}</p>
                  <p role="cell" className={`${styles.right} ${styles.muted} num`}>{item.words ?? '–'}</p>
                  <p role="cell" className={`${styles.right} ${styles.score} num`}>{item.verdict == null ? (item.status === 'queued' ? '…' : '–') : oneIn(item.verdict.p)}</p>
                  <p role="cell" className={`${styles.right} ${styles.muted} num`}>{item.jurors == null ? '–' : `${item.jurors} of 20`}</p>
                  <p role="cell" className={styles.result} title={item.error?.message}>{err}</p>
                  <p role="cell" className={styles.open} aria-hidden="true">{item.status === 'done' && <ChevronRight />}</p>
                </>
              )
              return item.status === 'done'
                ? <a key={item.id} role="row" href="/" data-flip={item.id} className={styles.row} data-tone={res.tone} onClick={(e) => { e.preventDefault(); onOpen(item) }}>{cells}</a>
                : <div key={item.id} role="row" data-flip={item.id} className={styles.row} data-tone={res.tone} {...mark}>{cells}</div>
            })}
          </div>
        </div>
      </div>
      {paging.pages > 1 && (
        <div className={styles.pager}>
          <p className="num">Essays {paging.from} to {paging.to} of {paging.total}</p>
          <div>
            <Button disabled={paging.page === 0} onClick={() => onPage(paging.page - 1)}>Previous 50</Button>
            <Button disabled={paging.page >= paging.pages - 1} onClick={() => onPage(paging.page + 1)}>Next 50</Button>
          </div>
        </div>
      )}
    </div>
  )
}
