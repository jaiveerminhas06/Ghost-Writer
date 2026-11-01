import { useState } from 'react'
import styles from './DropZone.module.css'
import Button from './Button'
import { Upload } from './Icons'

/** Where essays are added: drag files onto it, or press "Choose files". The file input is the page's (so other buttons can open
 *  it too); this only listens. While files are dragged over it, it takes the tint used for drop targets.
 *  @param {{ inputRef: { current: HTMLInputElement | null }, onFiles: (files: File[]) => void, hasFiles: boolean, accept: string[] }} props */
export default function DropZone({ inputRef, onFiles, hasFiles, accept }) {
  const [over, setOver] = useState(false)
  const types = accept.join(', ').replace(/, ([^,]*)$/, ' or $1')
  return (
    <div className={`${styles.zone} ${over ? styles.over : ''}`}
         onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
         onDrop={(e) => { e.preventDefault(); setOver(false); onFiles([...e.dataTransfer.files]) }}>
      <span className={styles.icon}><Upload /></span>
      <p>{hasFiles ? 'Drop more essays here' : 'Drop essays here'}: {types}</p>
      <input ref={inputRef} type="file" multiple accept={accept.join(',')} className="sr-only" tabIndex={-1} aria-label="Choose essay files"
             onChange={(e) => { onFiles([...(e.target.files ?? [])]); e.target.value = '' }} />
      <Button onClick={() => inputRef.current?.click()}>Choose files</Button>
    </div>
  )
}
