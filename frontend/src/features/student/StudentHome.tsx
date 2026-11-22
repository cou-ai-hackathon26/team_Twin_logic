import clsx from 'clsx'
import { BookOpen, CheckCircle2, Mic } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMyOverview, useMyPassages } from '@/api/hooks'
import type { Language } from '@/api/types'
import { LanguageBadge, MarkBadge, ReadingStatusBadge, SimulatedBadge } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, PageLoader } from '@/components/ui/primitives'
import { dateTime, langFont, mark10, markTone } from '@/lib/format'

const LANG_TABS: { lang: Language; label: string; sub: string }[] = [
  { lang: 'bn', label: 'বাংলা', sub: 'Bangla reading' },
  { lang: 'en', label: 'English', sub: 'Learn English' },
]

export function StudentHome() {
  const overview = useMyOverview()
  const passages = useMyPassages()
  const [lang, setLang] = useState<Language>('bn')
  const shown = useMemo(() => (passages.data ?? []).filter((p) => p.language === lang), [passages.data, lang])

  if (overview.isLoading) return <PageLoader />
  if (overview.error || !overview.data) return <ErrorBox error={overview.error ?? 'Not found'} />
  const o = overview.data
  const marked = o.history.filter((h) => h.score !== null)

  return (
    <>
      <div className="relative mb-8 overflow-hidden rounded-3xl bg-marigold-50 p-6 ring-1 ring-amber-200 sm:p-8">
        <div aria-hidden="true" className="pointer-events-none absolute -right-4 -bottom-16 select-none font-bn-display text-[13rem] leading-none text-amber-500/10">অআ</div>
        <div className="relative flex flex-wrap items-center gap-6">
          <div className="grid size-20 shrink-0 animate-float place-items-center rounded-3xl bg-white text-4xl shadow-lg ring-1 ring-amber-200" aria-hidden="true">
            📖
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-bn text-amber-800">শুভেচ্ছা!</div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Hello, {o.nickname || o.code}!</h1>
            <p className="mt-1 text-slate-600">
              {o.classroom.name} · Grade {o.classroom.grade}. Pick a passage below and read it aloud.
            </p>
          </div>
        </div>
        <div className="relative mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { l: 'Tests taken', v: String(marked.length), t: 'text-ink', h: undefined as string | undefined },
            { l: 'Latest mark', v: mark10(marked[0]?.score), t: markTone(marked[0]?.score), h: marked[0]?.passage_title },
            { l: 'Average mark', v: mark10(o.mean_score), t: markTone(o.mean_score), h: undefined },
            { l: 'Best mark', v: mark10(o.best_score), t: markTone(o.best_score), h: undefined },
          ].map((x) => (
            <div key={x.l} className="rounded-2xl bg-white/80 px-4 py-3 ring-1 ring-amber-100 backdrop-blur">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{x.l}</div>
              <div className={clsx('mt-1 text-2xl font-semibold tabular-nums', x.t)}>{x.v}</div>
              {x.h && <div className={clsx('truncate text-xs text-slate-500', langFont(marked[0]?.language))}>{x.h}</div>}
            </div>
          ))}
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader
          title="Reading tests"
          subtitle="Every test gets a mark out of 10"
          actions={
            <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm" role="tablist">
              {LANG_TABS.map((t) => (
                <button
                  key={t.lang}
                  role="tab"
                  aria-selected={lang === t.lang}
                  onClick={() => setLang(t.lang)}
                  className={clsx('rounded-md px-3 py-1.5 font-medium', lang === t.lang ? 'bg-white shadow-sm' : 'text-slate-600', t.lang === 'bn' && 'font-bn')}
                >
                  {t.label}
                </button>
              ))}
            </div>
          }
        />
        {passages.isLoading ? (
          <PageLoader />
        ) : !shown.length ? (
          <EmptyState icon={<BookOpen className="size-10" />} title="No passages for your class yet" />
        ) : (
          <div className="grid gap-3 p-5 md:grid-cols-2">
            {shown.map((p) => (
              <div key={p.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={clsx('text-lg font-semibold', langFont(p.language))}>{p.title}</span>
                    <LanguageBadge language={p.language} />
                  </div>
                  {p.attempted && <MarkBadge score={p.best_score} />}
                </div>
                <p className={clsx('mt-2 line-clamp-2 flex-1 text-sm text-slate-600', langFont(p.language))}>{p.text}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    {p.attempted ? (
                      <>
                        <CheckCircle2 className="size-3.5 text-teal-600" /> Best mark so far
                      </>
                    ) : (
                      `${p.word_count} words`
                    )}
                  </span>
                  <Link to={`/me/read/${p.id}`}>
                    <Button size="sm">
                      <Mic className="size-4" /> {p.attempted ? 'Try again' : 'Start test'}
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="My results" subtitle="Newest first" />
        {!o.history.length ? (
          <EmptyState title="No tests yet">Your marks appear here after your first reading test.</EmptyState>
        ) : (
          <ul className="divide-y divide-slate-100">
            {o.history.map((r) => (
              <li key={r.id}>
                <Link to={`/me/readings/${r.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 hover:bg-slate-50">
                  <MarkBadge score={r.score} />
                  <span className={clsx('min-w-0 flex-1 truncate', langFont(r.language))}>{r.passage_title}</span>
                  <LanguageBadge language={r.language} />
                  {r.correct !== null && r.total_words !== null && (
                    <span className="text-sm tabular-nums text-slate-500">
                      {r.correct}/{r.total_words} words
                    </span>
                  )}
                  <span className="text-sm text-slate-500">{dateTime(r.created_at)}</span>
                  {r.status !== 'done' && <ReadingStatusBadge status={r.status} />}
                  {r.simulated && <SimulatedBadge />}
                  {r.status === 'done' && r.reviewed && <span className="text-xs font-medium text-teal-700">Checked by teacher</span>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
