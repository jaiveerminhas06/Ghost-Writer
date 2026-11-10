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

/** The essay's state and the class's state; the class needs the file-size limit from /api/meta. */
function EssayState({ children }) {
  const { state } = useMetaState()
  const maxFileBytes = state.status === 'ready' ? state.meta.limits?.max_file_bytes : undefined
  return (
    <EssayProvider>
      <ClassProvider maxFileBytes={maxFileBytes}>{children}</ClassProvider>
    </EssayProvider>
  )
}
