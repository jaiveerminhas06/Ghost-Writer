import { Outlet } from 'react-router-dom'
import styles from './App.module.css'
import ErrorBoundary from './components/ErrorBoundary'
import Header from './components/Header'
import { ToastProvider } from './components/Toast'
import { MetaProvider } from './state/MetaContext'
import { useMetaState } from './state/contexts'
import { EssayProvider } from './state/EssayContext'
import { ClassProvider } from './state/ClassContext'

/** The frame around every page: a skip link for keyboard users, the header, the page itself, and the place toasts appear.
 *  The data every page shares (the server's figures, the essay) is provided here. */
export default function App() {
  return (
    <ToastProvider>
      <MetaProvider>
        <EssayState>
          <a href="#main" className={styles.skip}>Skip to the page</a>
          <Header />
          <main id="main" tabIndex={-1} className={styles.main}><ErrorBoundary><Outlet /></ErrorBoundary></main>
        </EssayState>
      </MetaProvider>
    </ToastProvider>
  )
}

/** The essay's state needs the flag lines from /api/meta (highlights are fetched for any essay flagged in at least one setting). */
function EssayState({ children }) {
  const { state } = useMetaState()
  const lowest = state.status === 'ready' ? Math.min(...Object.values(state.meta.thresholds)) : null
  const maxFileBytes = state.status === 'ready' ? state.meta.limits?.max_file_bytes : undefined
  return (
    <EssayProvider lowestFlagLine={lowest}>
      <ClassProvider maxFileBytes={maxFileBytes}>{children}</ClassProvider>
    </EssayProvider>
  )
}
