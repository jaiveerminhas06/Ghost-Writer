import styles from './Button.module.css'
import { Spinner } from './Icons'

/**
 * @typedef {object} ButtonProps
 * @property {'primary'|'secondary'|'quiet'|'icon'} [variant]
 * @property {boolean} [busy]
 * @property {boolean} [done]
 * @property {'hover'|'pressed'|'focus'} [force]
 * @property {any} [as]
 * @property {string} [className]
 * @property {boolean} [disabled]
 * @property {(e: any) => void} [onClick]
 * @property {any} [children]
 */
/** One button for the whole app.
 *  variant: primary (the one main action on a screen) | secondary | quiet (text-only) | icon (44 px square, needs aria-label).
 *  busy: shows the working state (spinner on primary) and ignores clicks. done: the icon button's "Copied" state.
 *  as: render a router <Link> or <a> with the button's look.
 *  force: draws hover | pressed | focus without the pointer, for the /components sheet only. */
/** @param {ButtonProps & Record<string, any>} props */
export default function Button({ variant = 'secondary', busy = false, done = false, force, as: Tag = 'button', className = '', children, onClick, disabled, ...rest }) {
  const isButton = Tag === 'button'
  const cls = [styles.btn, styles[variant], done && styles.done, className].filter(Boolean).join(' ')
  return (
    <Tag className={cls} data-force={force} aria-busy={busy || undefined} disabled={isButton ? disabled : undefined}
         aria-disabled={!isButton && disabled ? true : undefined} type={isButton ? 'button' : undefined}
         onClick={busy || disabled ? (e) => e.preventDefault() : onClick} {...rest}>
      {busy && variant === 'primary' && <Spinner />}
      {children}
    </Tag>
  )
}
