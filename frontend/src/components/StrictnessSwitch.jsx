import Segmented from './Segmented'
import { useEssay } from '../state/contexts'

/** The Strict / Standard choice. It reads and writes the one shared setting (in the essay state), so changing it on any page
 *  changes every page: the flag line, the verdict, the both-sides sentence, the class count.
 *  Nothing is sent to the server: the score is the same, only the line it is compared with moves. */
export default function StrictnessSwitch() {
  const { state, setStrictness } = useEssay()
  return <Segmented label="How strict" value={state.strictness} onChange={(v) => setStrictness(v === 'standard' ? 'standard' : 'strict')} options={[{ value: 'strict', label: 'Strict' }, { value: 'standard', label: 'Standard' }]} />
}
