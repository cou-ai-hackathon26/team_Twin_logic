import clsx from 'clsx'
import type { Language, WordMark } from '@/api/types'
import { FLAG_META, langFont, STATUS_META } from '@/lib/format'

export function MarkedPassage({
  marks,
  selected,
  onSelect,
  statusOf = (m) => m.final_status,
  language = 'bn',
}: {
  marks: WordMark[]
  selected: number | null
  onSelect: (index: number) => void
  statusOf?: (m: WordMark) => WordMark['final_status']
  language?: Language
}) {
  return (
    <p className={clsx('text-2xl leading-[2.4] text-slate-900', langFont(language))}>
      {marks.map((m) => {
        const st = statusOf(m)
        const flags = m.flags.filter((f) => f === 'hesitation' || f === 'repeated' || f === 'partial_attempt' || f === 'extra_word')
        return (
          <span key={m.index}>
            <button
              type="button"
              onClick={() => onSelect(m.index)}
              title={`${STATUS_META[st].label}${m.heard ? ` · heard: ${m.heard}` : ''}`}
              className={clsx('word', `word-${st}`, selected === m.index && 'word-selected', m.teacher_status && 'word-teacher')}
            >
              {flags.length > 0 && (
                <sup className="mr-0.5 font-sans text-xs text-indigo-600" aria-label={flags.map((f) => FLAG_META[f]?.label).join(', ')}>
                  {flags.map((f) => FLAG_META[f]?.icon).join('')}
                </sup>
              )}
              {m.display}
            </button>{' '}
          </span>
        )
      })}
    </p>
  )
}

export function Legend() {
  const items: [string, string][] = [
    ['word-correct', 'Correct'],
    ['word-misread', 'Misread'],
    ['word-skipped', 'Skipped'],
    ['word-unsure', 'Unsure: check'],
    ['word-not_reached', 'Not reached'],
  ]
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-600">
      {items.map(([cls, label]) => (
        <span key={cls} className="flex items-center gap-1.5">
          <span className={clsx('word font-bn !cursor-default text-base', cls)}>শব্দ</span>
          {label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="text-indigo-600">⏸</span> hesitation
      </span>
      <span className="flex items-center gap-1.5">
        <span className="text-indigo-600">↻</span> repeated
      </span>
      <span className="flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-teal-600" /> changed by teacher
      </span>
    </div>
  )
}
