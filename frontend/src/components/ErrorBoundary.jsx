import { Component } from 'react'
import styles from './ErrorBoundary.module.css'
import Button from './Button'

/** If something in a page throws while it is drawing, show this instead of a blank screen. React only offers this as a class.
 *  Typical cause during development: the page and the server are different versions (the server sent a field the page expects
 *  and does not have). */
export default class ErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className={`wrap ${styles.box}`} role="alert">
        <h1 className="t-section">Something broke on this page.</h1>
        <p>Your essay is still saved in this tab. Reload the page to carry on. If it keeps happening, the page and the model server may be different versions: restart the server.</p>
        <div><Button variant="primary" onClick={() => window.location.reload()}>Reload the page</Button></div>
      </div>
    )
  }
}
