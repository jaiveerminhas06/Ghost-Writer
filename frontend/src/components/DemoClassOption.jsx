import styles from './ExampleList.module.css'

/** "Demo classes": one option for each held-out topic, named by the topic and styled like the examples on Check an essay. The one that is
 *  on the page is selected. Choosing one replaces whatever class is there.
 *  @param {{ classes: { id: string, name: string, essays: number }[], selected: string | null, disabled: boolean, onLoad: (id: string) => void }} props */
export default function DemoClassOption({ classes, selected, disabled, onLoad }) {
  return (
    <div className={styles.field}>
      <p id="demo-class" className={styles.label}>Load the demo class</p>
      <div role="group" aria-labelledby="demo-class" className={styles.list}>
        {classes.map((c) => (
          <button key={c.id} type="button" className={styles.option} aria-pressed={selected === c.id} disabled={disabled} onClick={() => onLoad(c.id)}>
            <span>{c.name}</span><span className={`${styles.words} num`}>{c.essays} essays</span>
          </button>
        ))}
      </div>
      <p className={styles.words} style={{ fontSize: 'var(--fs-caption)' }}>Student and AI essays on a topic the model never saw, with the real authors known.</p>
    </div>
  )
}
