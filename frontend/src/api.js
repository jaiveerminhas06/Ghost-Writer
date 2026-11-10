// Every call to the Python server lives here, so the pages never build URLs or read raw responses themselves.
// In development Vite passes /api on to FastAPI; in the built app FastAPI serves both the page and /api.
// Response shapes are in types.js.

const BASE = '/api'
const SECONDS = { meta: 15, score: 30, explain: 120, attribution: 30, typos: 30, t5: 120, batch: 120, jury: 90 }

/** A failed request, in words the page can show. `title` is the first sentence, `detail` the rest. */
export class ApiProblem extends Error {
  /** @param {string} code  @param {string} message  @param {number} [status]  @param {number} [retryAfter]  seconds the server asked us to wait */
  constructor(code, message, status = 0, retryAfter = 0) {
    super(message)
    this.code = code
    this.status = status
    this.retryAfter = retryAfter
    const cut = message.search(/[.!?](\s|$)/)               // the server's messages are "Sentence one. Sentence two."
    this.title = cut === -1 ? message : message.slice(0, cut + 1)
    this.detail = cut === -1 ? '' : message.slice(cut + 1).trim()
  }
}

/** @param {string} path  @param {{ body?: any, form?: FormData, seconds: number }} options  @returns {Promise<any>} */
async function request(path, { body, form, seconds }) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), seconds * 1000)
  let res
  try {
    res = await fetch(BASE + path, {
      method: body || form ? 'POST' : 'GET', signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : form,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiProblem('timeout', `The detector didn't respond. The model server stopped answering after ${seconds} seconds. Your essay is still on the page below. Check the server is running, then try again.`)
    }
    throw new ApiProblem('unreachable', "The detector didn't respond. The page couldn't reach the model server. Your essay is still on the page below. Check the server is running, then try again.")
  } finally {
    clearTimeout(timer)
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiProblem(data?.code ?? 'error', data?.detail ?? 'Something went wrong. Please try again.', res.status, Number(res.headers.get('Retry-After')) || 0)
  return data
}

/** @returns {Promise<import('./types').Meta>} */
export const getMeta = () => request('/meta', { seconds: SECONDS.meta })
/** @param {string} text  @returns {Promise<import('./types').ScoreResult>} */
export const score = (text) => request('/score', { body: { text }, seconds: SECONDS.score })
/** @param {string} text  @returns {Promise<import('./types').ExplainResult>} */
export const explain = (text) => request('/explain', { body: { text }, seconds: SECONDS.explain })
/** @param {string} text  @returns {Promise<import('./types').AttributionResult>} */
export const attribution = (text) => request('/attribution', { body: { text }, seconds: SECONDS.attribution })
/** @param {string} text  @param {'typos5'|'typos10'|'t5'|'t5_heavy'} method  @param {number} [seed]  @returns {Promise<import('./types').RewriteResult>} */
export const rewrite = (text, method, seed) =>
  request('/rewrite', { body: { text, method, ...(seed === undefined ? {} : { seed }) }, seconds: method.startsWith('t5') ? SECONDS.t5 : SECONDS.typos })
/** @returns {Promise<{ essays: { name: string, text: string }[], labels: Record<string, 'human' | 'ai'> }>} */
export const demoClass = (/** @type {string} */ topic) => request(`/demo-class/${encodeURIComponent(topic)}`, { seconds: SECONDS.meta })
/** @param {File[]} files  @returns {Promise<{ results: import('./types').BatchItem[] }>} */
export const batch = (files) => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return request('/batch', { form, seconds: SECONDS.batch })
}

/** One trial of the twenty detectors. The server streams one JSON object per line (NDJSON over POST: a browser's EventSource can only GET,
 *  so the body is read with fetch). `onEvent` gets each object as it arrives: 'start', then 20 'juror' events in seed order, then 'summary'.
 *  A refusal before the stream (too short, not English, rate limit, no GPU) rejects with the server's sentence; an 'error' line inside the
 *  stream rejects the same way. Aborting `signal` stops reading. Essay text is only ever in the request, never in a response.
 *  @param {string} text  @param {{ typos?: boolean, seed?: number }} options  @param {(event: any) => void} onEvent  @param {AbortSignal} [signal]
 *  @returns {Promise<void>} */
export async function jury(text, { typos = false, seed } = {}, onEvent, signal) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), SECONDS.jury * 1000)
  signal?.addEventListener('abort', () => controller.abort())
  let res
  try {
    res = await fetch(`${BASE}/jury`, {
      method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, typos, ...(seed === undefined ? {} : { seed }) }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => null)
      throw new ApiProblem(data?.code ?? 'error', data?.detail ?? 'Something went wrong. Please try again.', res.status, Number(res.headers.get('Retry-After')) || 0)
    }
    if (!res.body) throw new ApiProblem('unreachable', 'The detectors could not be reached.')
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const handle = (/** @type {string} */ line) => {
      if (!line.trim()) return
      const event = JSON.parse(line)
      if (event.type === 'error') throw new ApiProblem(event.code ?? 'error', event.detail ?? 'The jury could not finish. Please try again.')
      onEvent(event)
    }
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      lines.forEach(handle)
    }
    handle(buffer)
  } catch (e) {
    if (e instanceof ApiProblem) throw e
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    if (e instanceof DOMException && e.name === 'AbortError') throw new ApiProblem('timeout', "The detectors didn't finish. The model server stopped answering. Your essay is still on the page. Check the server is running, then try again.")
    throw new ApiProblem('unreachable', "The detectors didn't respond. The page couldn't reach the model server. Your essay is still on the page. Check the server is running, then try again.")
  } finally {
    clearTimeout(timer)
  }
}
