// All calls to the Python backend live here, so the components never build URLs themselves.
const BASE = 'http://localhost:8000/api'

async function call(path, body) {
  const res = await fetch(BASE + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed')
  return data
}

export const getSamples = () => call('/samples')
export const score = (text, strictness) => call('/score', { text, strictness })
export const explain = (text, strictness) => call('/explain', { text, strictness })
export const attribution = (text, strictness) => call('/attribution', { text, strictness })
export const rewrite = (text, strictness, attack) => call('/rewrite', { text, strictness, attack })
