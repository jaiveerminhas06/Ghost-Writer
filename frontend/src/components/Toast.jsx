import { useCallback, useEffect, useRef, useState } from 'react'
import styles from './Toast.module.css'
import { Alert, Close } from './Icons'
import { ToastContext } from '../lib/toast'

/** What a toast looks like. kind "status" (dark, role=status) confirms an action; kind "error" (paper, brick icon, role=alert)
 *  says something failed. Toasts never carry a verdict. */
/** @param {{ kind?: 'status'|'error', message: string, action?: string, onAction?: () => void, onDismiss?: () => void } & Record<string, any>} props */
export function ToastView({ kind = 'status', message, action, onAction, onDismiss, ...rest }) {
  const error = kind === 'error'
  return (
    <div role={error ? 'alert' : 'status'} className={`${styles.toast} ${error ? styles.error : styles.status}`} {...rest}>
      {error && <span className={styles.icon}><Alert /></span>}
      <p className={styles.message}>{message}</p>
      {action && <button type="button" className={styles.action} onClick={onAction}>{action}</button>}
      {!error && onDismiss && (
        <button type="button" className={styles.dismiss} aria-label="Dismiss" onClick={onDismiss}><Close /></button>
      )}
    </div>
  )
}

const DURATION = 6000          // stays 6 s, paused while the pointer is over it or focus is inside it

/** Toasts need a home near the top of the app: <ToastProvider> wraps the pages, and any component calls useToast().show({...}) (lib/toast.js). */
/** @param {{ children: any }} props */
export function ToastProvider({ children }) {
  const [items, setItems] = useState(/** @type {any[]} */ ([]))
  const seq = useRef(0)
  const show = useCallback((t) => {
    const id = ++seq.current
    setItems((list) => [...list.slice(-2), { id, open: true, ...t }])      // at most three at once
    return id
  }, [])
  const dismiss = useCallback((id) => setItems((list) => list.map((x) => (x.id === id ? { ...x, open: false } : x))), [])
  const remove = useCallback((id) => setItems((list) => list.filter((x) => x.id !== id)), [])
  return (
    <ToastContext.Provider value={{ show, dismiss }}>
      {children}
      <div className={styles.region}>
        {items.map((t) => <ToastItem key={t.id} item={t} dismiss={dismiss} remove={remove} />)}
      </div>
    </ToastContext.Provider>
  )
}

/** @param {{ item: any, dismiss: (id: number) => void, remove: (id: number) => void }} props */
function ToastItem({ item, dismiss, remove }) {
  const [paused, setPaused] = useState(false)
  const left = useRef(DURATION)
  useEffect(() => {
    if (paused || !item.open) return
    const started = Date.now()
    const timer = setTimeout(() => dismiss(item.id), left.current)
    return () => { clearTimeout(timer); left.current -= Date.now() - started }     // pause: remember how much time is left
  }, [paused, item.open, item.id, dismiss])
  return (
    <div className={styles.item} data-state={item.open ? 'open' : 'closed'}
         onAnimationEnd={() => { if (!item.open) remove(item.id) }}
         onPointerEnter={() => setPaused(true)} onPointerLeave={() => setPaused(false)}
         onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <ToastView kind={item.kind} message={item.message} action={item.action}
                 onAction={() => { item.onAction?.(); dismiss(item.id) }} onDismiss={() => dismiss(item.id)} />
    </div>
  )
}
