import { useCallback, useEffect, useState } from 'react'
import * as api from '../api'
import { MetaContext } from './contexts'

/** Fetches /api/meta once: the flag lines, the false-flag rates, the examples. Nothing on the page can be scored before this
 *  arrives, because the flag line comes from it. */
export function MetaProvider({ children }) {
  const [state, setState] = useState(/** @type {import('./contexts').MetaState} */ ({ status: 'loading' }))
  const load = useCallback(() => {
    api.getMeta().then((meta) => setState({ status: 'ready', meta }), (problem) => setState({ status: 'error', problem }))
  }, [])
  useEffect(() => { load() }, [load])
  const retry = useCallback(() => { setState({ status: 'loading' }); load() }, [load])
  return <MetaContext.Provider value={{ state, retry }}>{children}</MetaContext.Provider>
}
