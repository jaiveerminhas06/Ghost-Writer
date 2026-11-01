import { Outlet } from 'react-router-dom'
import styles from './App.module.css'
import Header from './components/Header'
import { ToastProvider } from './components/Toast'

/** The frame around every page: a skip link for keyboard users, the header, the page itself, and the place toasts appear. */
export default function App() {
  return (
    <ToastProvider>
      <a href="#main" className={styles.skip}>Skip to the page</a>
      <Header />
      <main id="main" tabIndex={-1} className={styles.main}><Outlet /></main>
    </ToastProvider>
  )
}
