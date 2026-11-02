import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import styles from './Header.module.css'
import { Logo, Menu, Close } from './Icons'

export const REPO = 'https://github.com/jaiveerminhas06/Ghost-Writer'
const PAGES = [
  { to: '/', label: 'Check an essay', end: true },
  { to: '/fool', label: 'Try to fool it' },
  { to: '/class', label: 'Check a class' },
]

/** Brand, the three pages as text tabs (the current one has a pen underline and aria-current="page", which NavLink sets),
 *  and the model card. Under 640 px the tabs fold into a menu button, as drawn in Phone.dc.html. */
export default function Header() {
  const [open, setOpen] = useState(false)
  const button = useRef(/** @type {HTMLButtonElement | null} */ (null))
  const { pathname } = useLocation()
  const [seen, setSeen] = useState(pathname)
  if (seen !== pathname) { setSeen(pathname); setOpen(false) }       // going to another page closes the menu

  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') { setOpen(false); button.current?.focus() } }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const tabs = PAGES.map((p) => (
    <NavLink key={p.to} to={p.to} end={p.end} className={styles.tab}>{p.label}</NavLink>
  ))
  return (
    <header className={styles.header}>
      <div className={`wrap ${styles.bar}`}>
        <Link to="/" className={styles.brand}><Logo />Ghost Writer</Link>
        <nav aria-label="Main" className={styles.tabs}>{tabs}</nav>
        <a href={`${REPO}/blob/main/MODEL_CARD.md`} className={styles.card}>Model card</a>
        <button ref={button} type="button" className={styles.menu} aria-label={open ? 'Close menu' : 'Menu'} aria-expanded={open}
                aria-controls="mobile-menu" onClick={() => setOpen((o) => !o)}>
          {open ? <Close /> : <Menu />}
        </button>
      </div>
      {open && (
        <nav id="mobile-menu" aria-label="Main" className={styles.sheet}>
          {tabs}
          <a href={`${REPO}/blob/main/MODEL_CARD.md`} className={styles.sheetLink}>Model card</a>
        </nav>
      )}
    </header>
  )
}
