import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api'
import { ClassContext } from './contexts'
import { useToast } from '../lib/toast'
import { sleep } from '../lib/format'

const KEY = 'gw-class'
const LABELS = 'gw-class-labels'
const CHUNK = 10                         // files per request: a batch of up to ten costs one unit of the server's rate limit
const CHUNK_BYTES = 12 * 1024 * 1024     // and never more than this many bytes, to stay well inside the server's 20 MB limit
const TYPES = ['.docx', '.pdf', '.txt']

/** @typedef {import('../lib/classStats').ClassItem} ClassItem */
const failed = (/** @type {string} */ code, /** @type {string} */ message) => ({ code, message })

/** The class: every file added, and the work of sending them to the server a few at a time.
 *  Files are read by the browser and sent, scored in the server's memory and forgotten there; the scores and the extracted text
 *  stay in this tab (sessionStorage), so closing the tab clears them. Rows appear at once as "Waiting to score" and fill in
 *  as each group of ten comes back. If the server says "too many requests", the queue waits as long as it asks and carries on.
 *  @param {{ children: any, maxFileBytes?: number }} props */
export function ClassProvider({ children, maxFileBytes = 5 * 1024 * 1024 }) {
  const toast = useToast()
  const [items, setItems] = useState(() => {
    try { return /** @type {ClassItem[]} */ (JSON.parse(sessionStorage.getItem(KEY) || '[]')) } catch { return [] }
  })
  const [labels, setLabels] = useState(() => {
    try { return /** @type {Record<string, string>} */ (JSON.parse(sessionStorage.getItem(LABELS) || '{}')) } catch { return {} }
  })
  const [demoTopic, setDemoTopic] = useState(() => {
    try { return sessionStorage.getItem(LABELS + '-topic') } catch { return null }
  })
  const [working, setWorking] = useState(false)
  const [notice, setNotice] = useState(/** @type {string | null} */ (null))
  const [reveal, setReveal] = useState(0)
  const queue = useRef(/** @type {{ id: number, file: File }[]} */ ([]))      // files waiting to be sent; they are not kept after scoring
  const running = useRef(false)
  const failedNow = useRef(0)                                                 // files that could not be scored since the queue last emptied
  const nextId = useRef(items.reduce((m, i) => Math.max(m, i.id + 1), 1))
  const session = useRef(0)                                                   // bumped by clear(), so work for a cleared class is dropped

  useEffect(() => {
    try { sessionStorage.setItem(KEY, JSON.stringify(items.filter((i) => i.status !== 'queued'))) } catch { /* storage full or blocked: the class still works until the tab is reloaded */ }
  }, [items])

  const patch = useCallback((/** @type {number[]} */ ids, /** @type {(i: ClassItem, k: number) => ClassItem} */ fn) => {
    setItems((all) => all.map((i) => (ids.includes(i.id) ? fn(i, ids.indexOf(i.id)) : i)))
  }, [])

  const drain = useCallback(async () => {
    if (running.current) return
    running.current = true
    setWorking(true)
    const mine = session.current
    try {
      while (queue.current.length && mine === session.current) {
        const chunk = []
        let bytes = 0
        while (queue.current.length && chunk.length < CHUNK && (chunk.length === 0 || bytes + queue.current[0].file.size <= CHUNK_BYTES)) {
          const next = /** @type {{ id: number, file: File }} */ (queue.current.shift())
          bytes += next.file.size
          chunk.push(next)
        }
        const ids = chunk.map((c) => c.id)
        try {
          const { results } = await api.batch(chunk.map((c) => c.file))
          if (mine !== session.current) return
          failedNow.current += results.filter((r) => r.error).length
          patch(ids, (i, k) => {
            const r = results[k]
            return r.error ? { ...i, status: 'error', words: r.words, error: r.error } : { ...i, status: 'done', words: r.words, logit: r.logit, text: r.text, error: null }
          })
        } catch (e) {
          const problem = /** @type {api.ApiProblem} */ (e)
          if (problem.code === 'rate_limited') {
            queue.current.unshift(...chunk)                                    // put them back and wait as long as the server asked
            const wait = Math.max(1, problem.retryAfter || 10)
            setNotice(`The server asked for a short pause (${wait} seconds). The remaining files will be scored after it.`)
            await sleep(wait * 1000)
            setNotice(null)
          } else {
            failedNow.current += chunk.length
            patch(ids, (i) => ({ ...i, status: 'error', error: failed(problem.code, problem.message) }))
          }
        }
      }
    } finally {
      running.current = false
      setWorking(false)
    }
    const errors = failedNow.current
    failedNow.current = 0
    if (errors > 0 && mine === session.current) {
      toast.show({ kind: 'error', message: `${errors === 1 ? '1 file' : `${errors} files`} couldn't be scored. ${errors === 1 ? "It's" : "They're"} at the end of the list.`, action: 'Show', onAction: () => setReveal((n) => n + 1) })
    }
  }, [patch, toast])

  const addFiles = useCallback((/** @type {File[]} */ files) => {
    const added = []
    for (const file of files) {
      const id = nextId.current++
      const ext = file.name.includes('.') ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase() : ''
      /** @type {ClassItem} */
      const base = { id, name: file.name, status: 'queued', words: null, logit: null, text: null, error: null }
      if (!TYPES.includes(ext)) failedNow.current++
      else if (file.size > maxFileBytes) failedNow.current++
      if (!TYPES.includes(ext)) added.push({ ...base, status: /** @type {const} */ ('error'), error: failed('unsupported_file', `${ext || 'This kind of'} files can't be read. Use .docx, .pdf or .txt.`) })
      else if (file.size > maxFileBytes) added.push({ ...base, status: /** @type {const} */ ('error'), error: failed('too_large', `This file is larger than ${Math.round(maxFileBytes / (1024 * 1024))} MB.`) })
      else { added.push(base); queue.current.push({ id, file }) }
    }
    setItems((all) => [...all, ...added])
    drain()
  }, [drain, maxFileBytes])

  const clear = useCallback(() => {
    session.current++
    queue.current = []
    setItems([])
    setNotice(null)
    setLabels({})
    setDemoTopic(null)
    try { sessionStorage.removeItem(KEY); sessionStorage.removeItem(LABELS); sessionStorage.removeItem(LABELS + '-topic') } catch { /* ignore */ }
  }, [])

  /** A demo class: 30 essays whose real authors are known. It replaces the class on the page (so two topics never mix in one summary)
   *  and goes through the same path as files the visitor adds. */
  const loadDemo = useCallback(async (/** @type {string} */ topic) => {
    try {
      const d = await api.demoClass(topic)
      clear()
      setLabels(d.labels)
      setDemoTopic(topic)
      try { sessionStorage.setItem(LABELS, JSON.stringify(d.labels)); sessionStorage.setItem(LABELS + '-topic', topic) } catch { /* ignore */ }
      addFiles(d.essays.map((e) => new File([e.text], e.name, { type: 'text/plain' })))
    } catch (e) {
      toast.show({ kind: 'error', message: /** @type {api.ApiProblem} */ (e).title || "Couldn't load the demo class." })
    }
  }, [addFiles, clear, toast])

  return (
    <ClassContext.Provider value={{ items, working, notice, reveal, labels, demoTopic, loadDemo, addFiles, clear, showErrors: () => setReveal((n) => n + 1) }}>
      {children}
    </ClassContext.Provider>
  )
}

