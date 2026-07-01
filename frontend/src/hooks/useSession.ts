import { useEffect, useState } from 'react'
import { AUTH_CHANGED_EVENT, getSession } from '../api/client'
import type { Session } from '../api/client'

/** Current session, kept in sync with sessionStorage across the app. */
export function useSession(): Session | null {
  const [session, setSession] = useState<Session | null>(() => getSession())
  useEffect(() => {
    const sync = () => setSession(getSession())
    window.addEventListener(AUTH_CHANGED_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])
  return session
}
