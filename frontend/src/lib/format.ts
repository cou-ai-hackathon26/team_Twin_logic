import type { WordStatus } from '@/api/types'

export const pct = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? '—' : `${(v * 100).toFixed(digits)}%`

export const num = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? '—' : v.toFixed(digits)

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

export const dateShort = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

export const secs = (s: number | null | undefined) => {
  if (s === null || s === undefined) return '—'
  const m = Math.floor(s / 60)
  const r = Math.round(s % 60)
  return m ? `${m}m ${r}s` : `${r}s`
}

export const STATUS_META: Record<WordStatus, { label: string; bn: string; dot: string; chip: string }> = {
  correct: { label: 'Correct', bn: 'সঠিক', dot: 'bg-emerald-500', chip: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  misread: { label: 'Misread', bn: 'ভুল', dot: 'bg-rose-500', chip: 'bg-rose-50 text-rose-800 ring-rose-200' },
  skipped: { label: 'Skipped', bn: 'বাদ', dot: 'bg-slate-500', chip: 'bg-slate-100 text-slate-700 ring-slate-300' },
  unsure: { label: 'Unsure', bn: 'অনিশ্চিত', dot: 'bg-amber-500', chip: 'bg-amber-50 text-amber-800 ring-amber-200' },
  not_reached: { label: 'Not reached', bn: 'পৌঁছায়নি', dot: 'bg-slate-300', chip: 'bg-slate-50 text-slate-500 ring-slate-200' },
}

export const FLAG_META: Record<string, { label: string; icon: string }> = {
  repeated: { label: 'Repeated', icon: '↻' },
  hesitation: { label: 'Hesitated (3 s+ pause before)', icon: '⏸' },
  partial_attempt: { label: 'Partial attempt first', icon: '…' },
  extra_word: { label: 'Extra word inserted', icon: '+' },
  spelling_only: { label: 'Same sound, different spelling', icon: '≈' },
  accepted_variant: { label: 'Accepted variant', icon: '✓' },
  accent: { label: 'Possible regional pronunciation: left to you, not counted as an error', icon: '♪' },
  noisy: { label: 'Background noise over this word: left to you', icon: '〰' },
  odd_word: { label: 'Odd word the AI is unreliable on: left to you', icon: '⚑' },
}

/** Words-correct-per-minute bands used only to colour numbers (not a norm). */
export const wcpmTone = (wcpm: number | null | undefined) => {
  if (wcpm === null || wcpm === undefined) return 'text-slate-400'
  if (wcpm >= 60) return 'text-emerald-700'
  if (wcpm >= 35) return 'text-amber-700'
  return 'text-rose-700'
}

export const accTone = (acc: number | null | undefined) => {
  if (acc === null || acc === undefined) return 'text-slate-400'
  if (acc >= 0.9) return 'text-emerald-700'
  if (acc >= 0.75) return 'text-amber-700'
  return 'text-rose-700'
}

/** Mark out of 10 for one reading test (words read correctly ÷ passage words × 10). */
export const mark10 = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${Number.isInteger(v) ? v : v.toFixed(1)}/10`)

export const markTone = (v: number | null | undefined) => {
  if (v === null || v === undefined) return 'text-slate-400'
  if (v >= 8) return 'text-emerald-700'
  if (v >= 5) return 'text-amber-700'
  return 'text-rose-700'
}

export const LANG_LABEL = { bn: 'বাংলা', en: 'English' } as const
/** Font for passage text: Bangla font for Bangla, the normal sans font for English. */
export const langFont = (lang: 'bn' | 'en' | undefined) => (lang === 'en' ? 'font-sans' : 'font-bn')
