import { ErrorPanel } from './VerdictPanel'
import { useMetaState } from '../state/contexts'

/** Every page needs the server's figures (the flag lines above all) before it can draw anything. This shows what the visitor needs
 *  while they are not there: a placeholder while loading, the problem if the server did not answer, and, if the server and the
 *  page are different versions, which one to update. Once they are there it calls `children(meta)`.
 *  @param {{ children: (meta: import('../types').Meta) => any }} props */
export default function MetaGate({ children }) {
  const { state, retry } = useMetaState()
  if (state.status === 'ready') return children(state.meta)
  const frame = (/** @type {any} */ inner) => <div className="wrap" style={{ boxSizing: 'content-box', padding: '56px clamp(16px, 4vw, 40px)' }}>{inner}</div>
  if (state.status === 'loading') return frame(<div aria-busy="true" role="status"><span className="sr-only">Loading</span><div className="skel" style={{ height: 56, width: '50%' }} /></div>)
  if (state.status === 'mismatch') {
    return frame(state.kind === 'newer'
      ? <ErrorPanel problem={{ title: 'This page is out of date.', detail: 'The server is a newer version than this page. Reload to get the page that matches it.' }} onRetry={() => window.location.reload()} retryLabel="Reload the page" />
      : <ErrorPanel problem={{ title: 'The API is out of date.', detail: 'The server is older than this page, so some figures would be missing or wrong. Restart it with uvicorn api.main:app --port 8000, then try again.' }} onRetry={retry} retryLabel="Try again" />)
  }
  return frame(<ErrorPanel problem={state.problem} onRetry={retry} retryLabel="Try again" />)
}
