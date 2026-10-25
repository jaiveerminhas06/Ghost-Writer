// All calls to the Python backend live here, so the components never build URLs themselves.
// In the hosted build the page and API share one address, so a relative path works; in development the API is on port 8000.
const BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api'

async function call(path, body) {
  let res
  try {
    res = await fetch(BASE + path, {
      method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    // No response at all: the server is down, or (in development) it answered 429 without CORS headers.
    throw new Error('Could not reach the server. If you have been trying many essays, wait a minute (there is a request limit) and try again.')
  }
  const data = await res.json()
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed')
  return data
}

export const getSamples = () => call('/samples')
export const score = (text, strictness) => call('/score', { text, strictness })
export const explain = (text, strictness) => call('/explain', { text, strictness })
export const attribution = (text, strictness) => call('/attribution', { text, strictness })
export const rewrite = (text, strictness, attack) => call('/rewrite', { text, strictness, attack })
