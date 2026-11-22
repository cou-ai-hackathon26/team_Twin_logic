import clsx from 'clsx'
import { BookOpenText, CornerDownLeft, FlaskConical, Inbox, LayoutDashboard, Mic, School, Search, Settings, Sparkles, User } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearch } from '@/api/hooks'

type Item = { id: string; group: string; label: ReactNode; hint?: ReactNode; icon: ReactNode; to: string; bn?: boolean }

const ACTIONS: Item[] = [
  { id: 'a-assess', group: 'Actions', label: 'Start a new assessment', icon: <Mic className="size-4" />, to: '/assess' },
  { id: 'a-review', group: 'Actions', label: 'Open review queue', icon: <Inbox className="size-4" />, to: '/review' },
  { id: 'a-dash', group: 'Actions', label: 'Dashboard', icon: <LayoutDashboard className="size-4" />, to: '/dashboard' },
  { id: 'a-pass', group: 'Actions', label: 'Passages library', icon: <BookOpenText className="size-4" />, to: '/passages' },
  { id: 'a-eng', group: 'Actions', label: 'Grapheme engine playground', icon: <Sparkles className="size-4" />, to: '/engine' },
  { id: 'a-bench', group: 'Actions', label: 'Benchmark report', icon: <FlaskConical className="size-4" />, to: '/benchmark' },
  { id: 'a-set', group: 'Actions', label: 'Settings', icon: <Settings className="size-4" />, to: '/settings' },
]

/** Ctrl/⌘+K palette: jump to any student, class, passage or page. */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const nav = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const { data, isFetching } = useSearch(open ? q : '')

  useEffect(() => {
    if (open) {
      setQ('')
      setActive(0)
      setTimeout(() => input.current?.focus(), 0)
    }
  }, [open])

  const items = useMemo<Item[]>(() => {
    const term = q.trim().toLowerCase()
    const acts = ACTIONS.filter((a) => !term || String(a.label).toLowerCase().includes(term))
    const students: Item[] = (data?.students ?? []).map((s) => ({
      id: `s${s.id}`,
      group: 'Students',
      label: (
        <>
          {s.code} {s.nickname && <span className="text-slate-500">· {s.nickname}</span>}
        </>
      ),
      hint: s.classroom,
      icon: <User className="size-4" />,
      to: `/students/${s.id}`,
    }))
    const classes: Item[] = (data?.classes ?? []).map((c) => ({
      id: `c${c.id}`,
      group: 'Classes',
      label: c.name,
      hint: `Grade ${c.grade}`,
      icon: <School className="size-4" />,
      to: `/classes/${c.id}`,
    }))
    const passages: Item[] = (data?.passages ?? []).map((p) => ({
      id: `p${p.id}`,
      group: 'Passages',
      label: p.title,
      hint: `Grade ${p.grade} · ${p.language === 'bn' ? 'বাংলা' : 'English'}`,
      icon: <BookOpenText className="size-4" />,
      to: `/passages`,
      bn: p.language === 'bn',
    }))
    return term ? [...students, ...classes, ...passages, ...acts] : [...acts, ...classes]
  }, [q, data])

  useEffect(() => setActive(0), [q])

  if (!open) return null
  const go = (it: Item | undefined) => {
    if (!it) return
    onClose()
    nav(it.to)
  }
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(items.length - 1, a + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(0, a - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      go(items[active])
    } else if (e.key === 'Escape') onClose()
  }

  let lastGroup = ''
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-ink/40 p-4 pt-[12vh] backdrop-blur-sm" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Search" className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-100 px-4">
          <Search className="size-5 text-slate-400" />
          <input
            ref={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="Search students, classes, passages… (e.g. Nusrat, Roll 03, পদ্মা)"
            className="h-14 flex-1 bg-transparent text-[15px] outline-none placeholder:text-slate-400"
          />
          {isFetching && <span className="size-2 animate-pulse rounded-full bg-teal-500" />}
          <kbd className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-500">Esc</kbd>
        </div>
        <ul className="max-h-[55vh] overflow-y-auto p-2">
          {!items.length && <li className="px-3 py-8 text-center text-sm text-slate-500">Nothing found for “{q}”.</li>}
          {items.map((it, i) => {
            const head = it.group !== lastGroup
            lastGroup = it.group
            return (
              <li key={it.id}>
                {head && <div className="px-3 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{it.group}</div>}
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(it)}
                  className={clsx('flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm', i === active ? 'bg-teal-50 text-teal-900' : 'text-slate-700')}
                >
                  <span className={clsx('grid size-8 place-items-center rounded-lg', i === active ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-500')}>{it.icon}</span>
                  <span className={clsx('min-w-0 flex-1 truncate font-medium', it.bn && 'font-bn')}>{it.label}</span>
                  {it.hint && <span className="shrink-0 text-xs text-slate-400">{it.hint}</span>}
                  {i === active && <CornerDownLeft className="size-3.5 shrink-0 text-teal-600" />}
                </button>
              </li>
            )
          })}
        </ul>
        <div className="flex items-center gap-4 border-t border-slate-100 bg-slate-50 px-4 py-2 text-[11px] text-slate-500">
          <span>
            <kbd className="font-sans">↑↓</kbd> move
          </span>
          <span>
            <kbd className="font-sans">Enter</kbd> open
          </span>
          <span className="ml-auto">
            <kbd className="font-sans">Ctrl K</kbd> anywhere
          </span>
        </div>
      </div>
    </div>
  )
}
