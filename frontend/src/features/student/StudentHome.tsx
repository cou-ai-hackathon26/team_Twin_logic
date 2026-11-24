import clsx from 'clsx'
import { BookOpen, CheckCircle2, Clock, Mic } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMyOverview, useMyPassages } from '@/api/hooks'
import { FromTeacher } from './FromTeacher'
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
            { l: 'Readings done', bn: 'পড়া শেষ', v: String(o.tests_done), t: 'text-ink' },
            { l: 'Latest mark', bn: 'শেষ নম্বর', v: mark10(o.history.find((h) => h.score !== null)?.score), t: markTone(o.history.find((h) => h.score !== null)?.score) },
            { l: 'Best mark', bn: 'সেরা নম্বর', v: mark10(o.best_score), t: markTone(o.best_score) },
            { l: 'Words read right', bn: 'ঠিক পড়া শব্দ', v: String(o.words_read_correctly), t: 'text-teal-700' },
          ].map((x) => (
            <div key={x.l} className="rounded-2xl bg-white/80 px-4 py-3 ring-1 ring-amber-100 backdrop-blur">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {x.l} <span className="font-bn normal-case tracking-normal">· {x.bn}</span>
              </div>
              <div className={clsx('mt-1 text-2xl font-semibold tabular-nums', x.t)}>{x.v}</div>
            </div>
          ))}
        </div>
      </div>

      <FromTeacher />

      <Card className="mb-6">
        <CardHeader
          title="Read aloud"
          subtitle="Read a passage aloud. The AI shows your mark out of 10 at once, then your teacher checks it."
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
                  {p.best_score !== null && <MarkBadge score={p.best_score} />}
                </div>
                <p className={clsx('mt-2 line-clamp-2 flex-1 text-sm text-slate-600', langFont(p.language))}>{p.text}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    {p.attempted ? (
                      <>
                        <CheckCircle2 className="size-3.5 text-teal-600" /> You have read this
                      </>
                    ) : (
                      `${p.word_count} words`
                    )}
                  </span>
                  <Link to={`/me/read/${p.id}`}>
                    <Button size="sm">
                      <Mic className="size-4" /> {p.attempted ? 'Read again' : 'Start reading'}
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="My readings" subtitle="Newest first" />
        {!o.history.length ? (
          <EmptyState title="No readings yet">Your readings appear here. The AI marks each one at once, then your teacher checks it.</EmptyState>
        ) : (
          <ul className="divide-y divide-slate-100">
            {o.history.map((r) => (
              <li key={r.id}>
                <Link to={`/me/readings/${r.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 hover:bg-slate-50">
                  {r.status === 'done' && <MarkBadge score={r.score} />}
                  <span className={clsx('min-w-0 flex-1 truncate', langFont(r.language))}>{r.passage_title}</span>
                  <LanguageBadge language={r.language} />
                  {r.status === 'done' && r.correct !== null && (
                    <span className="text-sm tabular-nums text-teal-700">{r.correct} words read right</span>
                  )}
                  {r.pending_review && (
                    <span className="flex items-center gap-1 text-sm text-slate-500">
                      <Clock className="size-3.5" /> AI result · teacher will check
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
