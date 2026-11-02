import { useEffect } from 'react'
import styles from './Popover.module.css'
import { useExit } from '../lib/useExit'

/** The floating card itself: used on its own on the /components sheet, and inside <Popover> in the app. */
/** @param {{ label: string, children: any } & Record<string, any>} props */
export function PopoverCard({ label, children, ...rest }) {
  return <div role="dialog" aria-label={label} className={styles.card} {...rest}>{children}</div>
}

/** A popover opened by a button. It is not modal: the rest of the page stays usable. Esc or a click outside closes it, and
 *  focus goes back to the button that opened it. Enter 180 ms (fade and scale .96 to 1), exit 120 ms. Put it inside a
 *  position: relative wrapper next to its trigger; it opens above and right-aligned. */
/** @param {{ open: boolean, onClose: () => void, triggerRef: { current: HTMLElement | null }, label: string, id?: string, children: any }} props */
export default function Popover({ open, onClose, triggerRef, label, id, children }) {
  const exit = useExit(open)

  useEffect(() => {
    if (!open) return
    const close = () => { onClose(); triggerRef.current?.focus() }
    const onKey = (e) => { if (e.key === 'Escape') close() }
    const onDown = (e) => {
      if (e.target.closest?.('[data-popover]') || triggerRef.current?.contains(e.target)) return
      close()
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('pointerdown', onDown) }
  }, [open, onClose, triggerRef])

  if (!exit.render) return null
  return (
    <div id={id} data-popover className={styles.anchor} data-state={exit.state} onAnimationEnd={exit.onAnimationEnd}>
      <PopoverCard label={label}>{children}</PopoverCard>
    </div>
  )
}
