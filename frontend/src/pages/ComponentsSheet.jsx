import { useRef, useState } from 'react'
import styles from './ComponentsSheet.module.css'
import tab from '../components/Header.module.css'
import Button from '../components/Button'
import Segmented from '../components/Segmented'
import Field, { SelectField } from '../components/Field'
import MethodCards from '../components/MethodCards'
import EssayRow from '../components/EssayRow'
import Popover, { PopoverCard } from '../components/Popover'
import { ToastView } from '../components/Toast'
import { useToast } from '../lib/toast'
import { Copy, Check, Info } from '../components/Icons'
import { wordCountText } from '../lib/format'
import PenCompare from './PenCompare'

/* The /components page: every component in every state it can be in, next to the others, so it can be compared with
   design/artboards/Components.dc.html. The sample values here are for drawing states; they do not come from the model. */
const STATES = ['Rest', 'Hover (pointer)', 'Pressed, 0.97', 'Keyboard focus', 'Working', 'Disabled']

/** @param {{ id: string, title: string, note?: string, children: any }} props */
function Section({ id, title, note, children }) {
  return (
    <section aria-labelledby={id} className={styles.section}>
      <div className={styles.side}>
        <h2 id={id} className="t-section">{title}</h2>
        {note && <p className={styles.sideNote}>{note}</p>}
      </div>
      <div className={styles.body}>{children}</div>
    </section>
  )
}

const METHODS = [
  { id: 'typos5', title: 'Typos in 5% of words', cost: 'Instant, on this machine', desc: 'Swaps or doubles letters in one word in twenty.', result: 'Last run: +9.1 to +3.3' },
  { id: 'typos10', title: 'Typos in 10% of words', cost: 'Instant, on this machine', desc: 'One word in ten. In testing, 98.9% of AI essays were still caught.', result: 'Not run yet' },
  { id: 't5', title: 'Paraphrase with T5', cost: 'Slower: runs the T5 model', desc: 'Rewrites each sentence with a pretrained paraphraser. Check it still says what the student meant.', result: 'Not run yet' },
  { id: 't5_heavy', title: 'Heavy T5 paraphrase', cost: 'Slower: runs the T5 model', desc: 'Rewrites about 43% of the words. The rewrite that moved the most verdicts in notebook 13: 96.4% of AI essays were still caught, down from 99.6%.', result: 'Not run yet' },
]
const T5_MISSING = "Paraphrasing needs the T5 model, which isn't loaded on this machine. Typos still work."

export default function ComponentsSheet() {
  const [strict, setStrict] = useState('strict')
  const [method, setMethod] = useState('typos5')
  const [t5Missing, setT5Missing] = useState(false)
  const [popover, setPopover] = useState(false)
  const [copied, setCopied] = useState(false)
  const trigger = useRef(null)
  const toast = useToast()
  const cards = METHODS.map((m) => (t5Missing && m.id.startsWith('t5') ? { ...m, unavailable: T5_MISSING } : m))

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <h1 className="t-display">Components</h1>
        <p>Each state is drawn, not described. Hover exists only on pointer devices; on touch, the pressed state shows while the finger is down. Every target is at least 44 px tall, including icon buttons whose glyph is 18 px. Sample values on this page are for drawing states; they do not come from the model.</p>
      </div>

      <PenCompare />

      <Section id="buttons" title="Buttons">
        <div className={styles.scroll}>
          <div className={styles.buttons}>
            <span />{STATES.map((s) => <span key={s} className={styles.colhead}>{s}</span>)}
            <span className={styles.rowhead}>Primary</span>
            <Button variant="primary">Score essay</Button>
            <Button variant="primary" force="hover">Score essay</Button>
            <Button variant="primary" force="pressed">Score essay</Button>
            <Button variant="primary" force="focus">Score essay</Button>
            <Button variant="primary" busy>Scoring…</Button>
            <Button variant="primary" disabled>Score essay</Button>
            <span className={styles.rowhead}>Secondary</span>
            <Button>Edit essay</Button>
            <Button force="hover">Edit essay</Button>
            <Button force="pressed">Edit essay</Button>
            <Button force="focus">Edit essay</Button>
            <Button busy>Saving…</Button>
            <Button disabled>Edit essay</Button>
            <span className={styles.rowhead}>Icon</span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copy essay"><Copy /></Button></span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copy essay" force="hover"><Copy /></Button></span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copy essay" force="pressed"><Copy /></Button></span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copy essay" force="focus"><Copy /></Button></span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copied" done><Check /></Button></span>
            <span className={styles.cell}><Button variant="icon" aria-label="Copy essay" disabled><Copy /></Button></span>
          </div>
        </div>
        <p className={styles.caption}>Optical alignment: the copy glyph's two squares put its visual weight low and right, so it is nudged 0.5 px down and right inside its 44 px box. The info icon in the verdict panel sits 1 px low so its circle lines up with the label's x-height, not its cap height.</p>
        <div className={styles.live}>
          <Button variant="icon" aria-label={copied ? 'Copied' : 'Copy essay'} done={copied} onClick={() => { setCopied(true); setTimeout(() => setCopied(false), 1600) }}>{copied ? <Check /> : <Copy />}</Button>
          <span className={styles.caption}>Live: press to see the "Copied" state for 1.6 s.</span>
        </div>
      </Section>

      <Section id="inputs" title="Inputs">
        <div className={styles.inputs}>
          <Field label="Essay" value="" onChange={() => {}} rows={5} placeholder="Paste an essay of at least 40 words" hint={wordCountText(0, 40)} />
          <Field label="Essay" force="focus" rows={5} value="A driverless car is a scary concept. Some say that it is" onChange={() => {}} hint={wordCountText(12, 40)} />
          <Field label="Essay" rows={5} value="Ceci est un essai en français sur les voitures sans conducteur." onChange={() => {}}
                 error="This looks like French. The detector was only trained on English essays, so its score would mean nothing." />
          <SelectField label="Rewrite with" disabled hint={T5_MISSING}><option>Paraphrase with T5</option></SelectField>
        </div>
      </Section>

      <Section id="nav" title="Navigation and segments">
        <nav aria-label="Example navigation" className={styles.examplenav}>
          <a href="#nav" aria-current="page" className={tab.tab}>Check an essay</a>
          <a href="#nav" className={tab.tab} style={{ color: 'var(--ink)' }}>Try to fool it <span className={styles.inlineNote}>(hover: ink)</span></a>
          <a href="#nav" className={tab.tab} style={{ outline: '2px solid var(--pen)', outlineOffset: -2, borderRadius: 6, paddingInline: 8 }}>Check a class</a>
        </nav>
        <div className={styles.segrow}>
          <Segmented label="How strict" value={strict} onChange={setStrict} options={[{ value: 'strict', label: 'Strict' }, { value: 'standard', label: 'Standard' }]} />
          <p className={styles.caption}>The selected segment is the only raised thing in the track: paper, sh-1, weight 600. The track is a well (desk 2 with an inset hairline), so the two levels never compete.</p>
        </div>
      </Section>

      <Section id="cards" title="Method cards" note="Siblings share a subgrid, so titles, results and buttons line up even when descriptions differ in length.">
        <MethodCards label="Rewrite method" methods={cards} value={method} onChange={setMethod} />
        <div className={styles.live}>
          <Button aria-pressed={t5Missing} onClick={() => setT5Missing((v) => !v)}>{t5Missing ? 'Pretend T5 is installed' : "Pretend T5 isn't installed"}</Button>
          <span className={styles.caption}>Live: shows the unavailable state. Arrow keys move the choice.</span>
        </div>
      </Section>

      <Section id="rows" title="Essay rows" note="One row per essay in a class check. Long file names end in an ellipsis; the full name is in the detail panel. Names are made-up examples.">
        <div className={styles.rows}>
          <EssayRow label="Rest" name="essay_17_martin.docx" score="−6.2" result="Not flagged" />
          <EssayRow label="Hover (pointer)" force="hover" tone="flagged" name="essay_04_okafor.docx" score="+8.4" result="Flagged, strict" />
          <EssayRow label="Selected" tone="selected" name="essay_22_nguyen.txt" score="+5.1" result="Flagged, standard only" />
          <EssayRow label="Queued (optimistic)" tone="queued" name="final_draft_FINAL_v3_really_final_essay_on_the_electoral_college_mehta.pdf" score="…" result="Waiting to score" />
          <EssayRow label="Error" tone="error" name="scan_0007.jpg" score="–" result="No text found in image" />
        </div>
      </Section>

      <Section id="overlays" title="Popover and toast" note="Both float on sh-3 with a translucent hairline. Toasts never carry a verdict; they confirm actions.">
        <div className={styles.overlays}>
          <PopoverCard label="What is the flag line?">
            <p>The flag line is a choice, not a fact</p>
            <p>It is the score that about 0.5% (strict) or 1% (standard) of student essays reached in validation. On new topics, more honest essays cross it.</p>
            <a href="#overlays">How it was chosen (notebook 09)</a>
          </PopoverCard>
          <div className={styles.toasts}>
            <ToastView message="Rewrite saved as attempt 3." action="Undo" onAction={() => {}} onDismiss={() => {}} />
            <ToastView kind="error" message="3 files couldn't be read. They're marked in the list." action="Show" onAction={() => {}} />
          </div>
        </div>
        <div className={styles.live}>
          <div className={styles.anchor}>
            <Button variant="quiet" ref={trigger} aria-expanded={popover} aria-controls="demo-pop" onClick={() => setPopover((o) => !o)}>
              <Info />What is the flag line?
            </Button>
            <Popover id="demo-pop" open={popover} onClose={() => setPopover(false)} triggerRef={trigger} label="What is the flag line?">
              <p>The flag line is a choice, not a fact</p>
              <p>Esc or a click outside closes this, and focus returns to the button.</p>
            </Popover>
          </div>
          <Button onClick={() => toast.show({ message: 'Rewrite saved as attempt 3.', action: 'Undo', onAction: () => toast.show({ message: 'Undone.' }) })}>Show a toast</Button>
          <Button onClick={() => toast.show({ kind: 'error', message: "2 files couldn't be scored. They're at the end of the list.", action: 'Show' })}>Show an error toast</Button>
        </div>
      </Section>
    </div>
  )
}
