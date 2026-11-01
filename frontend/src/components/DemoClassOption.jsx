import styles from './ExampleList.module.css'

/** "Load the demo class": one option, styled like the examples on Check an essay. It is selected once the demo class is what is on
 *  the page. @param {{ count: number, selected: boolean, disabled: boolean, onLoad: () => void }} props */
export default function DemoClassOption({ count, selected, disabled, onLoad }) {
  return (
    <div className={styles.field}>
      <p id="demo-class" className={styles.label}>Demo class</p>
      <div role="group" aria-labelledby="demo-class" className={styles.list}>
        <button type="button" className={styles.option} aria-pressed={selected} disabled={disabled} onClick={onLoad}>
          <span>Load the demo class</span><span className={`${styles.words} num`}>{count} essays</span>
        </button>
      </div>
      <p className={styles.words} style={{ fontSize: 'var(--fs-caption)' }}>Student and AI essays on a topic the model never saw, with the real authors known.</p>
    </div>
  )
}
