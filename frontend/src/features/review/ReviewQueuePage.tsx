import clsx from 'clsx'
import { ArrowRight, CheckCircle2, Clock, Inbox, PlayCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useReviewQueue } from '@/api/hooks'
import type { Language } from '@/api/types'
import { LanguageBadge, MarkBadge, SimulatedBadge } from '@/components/domain'
import { Button, Card, EmptyState, ErrorBox, PageHeader, PageLoader, Select } from '@/components/ui/primitives'
import { dateTime, langFont, num, wcpmTone } from '@/lib/format'

type Sort = 'help' | 'unsure' | 'oldest' | 'newest'
const SORTS: Record<Sort, string> = {
  help: 'Needs most help first',
  unsure: 'Most “unsure” words first',
  oldest: 'Waiting longest first',
  newest: 'Newest first',
}

/** Every finished reading the teacher hasn't checked yet, across all classes. */
export function ReviewQueuePage() {
  const { data, isLoading, error } = useReviewQueue()
  const [cls, setCls] = useState('all')
  const [lang, setLang] = useState<'all' | Language>('all')
  const [sort, setSort] = useState<Sort>('help')

  const classes = useMemo(() => {
    const m = new Map<string, number>()
    for (const r of data ?? []) m.set(r.classroom_name ?? '—', (m.get(r.classroom_name ?? '—') ?? 0) + 1)
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [data])

  const rows = useMemo(() => {
    const list = (data ?? []).filter((r) => (cls === 'all' || r.classroom_name === cls) && (lang === 'all' || r.language === lang))
    const by: Record<Sort, (a: (typeof list)[0], b: (typeof list)[0]) => number> = {
      help: (a, b) => (a.score ?? 11) - (b.score ?? 11),
      unsure: (a, b) => (b.unsure ?? 0) - (a.unsure ?? 0),
      oldest: (a, b) => a.created_at.localeCompare(b.created_at),
      newest: (a, b) => b.created_at.localeCompare(a.created_at),
    }
    return [...list].sort(by[sort])
  }, [data, cls, lang, sort])

  if (isLoading) return <PageLoader />
  const total = data?.length ?? 0
  const low = (data ?? []).filter((r) => (r.score ?? 10) < 5).length
  const unsureWords = (data ?? []).reduce((a, r) => a + (r.unsure ?? 0), 0)
  const oldest = (data ?? []).reduce<string | null>((a, r) => (!a || r.created_at < a ? r.created_at : a), null)

  return (
    <>
      <PageHeader
        title="Review queue"
        subtitle="AI marks are suggestions. Check each reading, change any mark, then finalise it."
        actions={
          rows[0] && (
            <Link to={`/readings/${rows[0].id}`}>
              <Button>
                <PlayCircle className="size-4" /> Start reviewing
              </Button>
            </Link>
          )
        }
      />
      <ErrorBox error={error} />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { l: 'Waiting', v: total, t: total ? 'text-indigo-700' : 'text-teal-700', h: 'readings to check' },
          { l: 'Below 5/10', v: low, t: low ? 'text-rose-700' : 'text-ink', h: 'children who may need help now' },
          { l: 'Unsure words', v: unsureWords, t: 'text-amber-700', h: 'the AI asks you to decide' },
          { l: 'Oldest', v: oldest ? dateTime(oldest) : '—', t: 'text-ink text-lg', h: 'waiting since' },
        ].map((s) => (
          <div key={s.l} className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3.5 shadow-sm">
            <div className="text-xs font-medium tracking-wide text-slate-500 uppercase">{s.l}</div>
            <div className={clsx('mt-1 text-2xl font-semibold tabular-nums', s.t)}>{s.v}</div>
            <div className="mt-0.5 text-xs text-slate-500">{s.h}</div>
          </div>
        ))}
      </div>

      {!total ? (
        <Card>
          <EmptyState icon={<CheckCircle2 className="size-12 text-teal-500" />} title="All caught up!">
            Every reading has been checked. New readings appear here as soon as they are marked.
          </EmptyState>
        </Card>
      ) : (
        <Card>
          <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-3">
            <div className="flex flex-wrap gap-1.5">
              <FilterChip active={cls === 'all'} onClick={() => setCls('all')}>
                All classes <span className="opacity-60">{total}</span>
              </FilterChip>
              {classes.map(([name, n]) => (
                <FilterChip key={name} active={cls === name} onClick={() => setCls(name)}>
                  {name} <span className="opacity-60">{n}</span>
                </FilterChip>
              ))}
            </div>
            <div className="ml-auto flex min-w-0 flex-wrap items-center gap-2">
              <Select value={lang} onChange={(e) => setLang(e.target.value as 'all' | Language)} className="h-9 !w-36" aria-label="Language">
                <option value="all">All languages</option>
                <option value="bn">বাংলা</option>
                <option value="en">English</option>
              </Select>
              <Select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className="h-9 !w-full sm:!w-64" aria-label="Sort">
                {Object.entries(SORTS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          {!rows.length ? (
            <EmptyState icon={<Inbox className="size-10" />} title="Nothing matches these filters" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {rows.map((r) => (
                <li key={r.id}>
                  <Link to={`/readings/${r.id}`} className="group flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3.5 hover:bg-teal-50/40">
                    <div className="flex w-44 items-center gap-3">
                      <div className="grid size-9 shrink-0 place-items-center rounded-full bg-teal-50 text-xs font-bold text-teal-800">{(r.student_nickname ?? r.student_code ?? '?').slice(0, 2)}</div>
                      <div className="min-w-0 leading-tight">
                        <div className="truncate font-semibold text-ink">{r.student_nickname ?? r.student_code}</div>
                        <div className="truncate text-xs text-slate-500">
                          {r.student_code} · {r.classroom_name}
                        </div>
                      </div>
                    </div>
                    <MarkBadge score={r.score} />
                    <div className="min-w-0 flex-1">
                      <div className={clsx('truncate text-slate-800', langFont(r.language))}>{r.passage_title}</div>
                      <div className="flex flex-wrap items-center gap-x-3 text-xs text-slate-500">
                        <span className={wcpmTone(r.wcpm)}>{num(r.wcpm)} WCPM</span>
                        <span>{r.errors ?? 0} errors</span>
                        {!!r.unsure && <span className="font-medium text-amber-700">{r.unsure} unsure</span>}
                      </div>
                    </div>
                    {r.simulated && <SimulatedBadge />}
                    <LanguageBadge language={r.language} />
                    <span className="flex w-36 items-center gap-1.5 text-sm text-slate-500">
                      <Clock className="size-3.5" /> {dateTime(r.created_at)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-teal-700 opacity-70 group-hover:opacity-100">
                      Review <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </>
  )
}

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-sm font-medium ring-1 transition-colors',
        active ? 'bg-teal-700 text-white ring-teal-700' : 'bg-white text-slate-600 ring-slate-200 hover:ring-teal-300',
      )}
    >
      {children}
    </button>
  )
}
