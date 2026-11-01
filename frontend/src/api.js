// Every call to the Python server lives here, so the pages never build URLs or read raw responses themselves.
// In development Vite passes /api on to FastAPI; in the built app FastAPI serves both the page and /api.
// Response shapes are in types.js.

const BASE = '/api'
const SECONDS = { meta: 15, score: 30, explain: 120, attribution: 30, typos: 30, t5: 120, batch: 120 }

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
export const demoClass = () => request('/demo-class', { seconds: SECONDS.meta })
/** @param {File[]} files  @returns {Promise<{ results: import('./types').BatchItem[] }>} */
export const batch = (files) => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return request('/batch', { form, seconds: SECONDS.batch })
}
