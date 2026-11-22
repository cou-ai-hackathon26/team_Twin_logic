import { useCallback, useSyncExternalStore } from 'react'
import { useMe } from '@/api/hooks'

/** Words a student has ticked as "I can read it now" (kept on this device, per student). */
const listeners = new Set<() => void>()
const cache = new Map<string, { raw: string; set: Set<string> }>()

function read(key: string): Set<string> {
  const raw = localStorage.getItem(key) ?? '[]'
  const hit = cache.get(key)
  if (hit && hit.raw === raw) return hit.set
  let set: Set<string>
  try {
    set = new Set(JSON.parse(raw) as string[])
  } catch {
    set = new Set()
  }
  cache.set(key, { raw, set })
  return set
}

export function useLearned() {
  const { data: me } = useMe()
  const key = `pb-learned-${me?.username ?? 'anon'}`
  const learned = useSyncExternalStore(
    (cb) => (listeners.add(cb), () => listeners.delete(cb)),
    () => read(key),
  )
  const toggle = useCallback(
    (word: string) => {
      const next = new Set(read(key))
      if (next.has(word)) next.delete(word)
      else next.add(word)
      localStorage.setItem(key, JSON.stringify([...next]))
      listeners.forEach((l) => l())
    },
    [key],
  )
  return { learned, toggle }
}
