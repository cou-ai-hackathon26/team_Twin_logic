import clsx from 'clsx'
import { Award, BookOpen, Flame, Rocket, Star, Target, TrendingUp, Trophy, Zap } from 'lucide-react'
import { useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useMyOverview } from '@/api/hooks'
import { Card, CardHeader, EmptyState, ErrorBox, PageLoader } from '@/components/ui/primitives'
import { dateShort, mark10, markTone } from '@/lib/format'

/** Marks over time and badges earned, for the student. */
export function StudentProgress() {
  const { data: o, isLoading, error } = useMyOverview()
  const tests = useMemo(
    () => (o?.history ?? []).filter((h) => h.status === 'done' && h.score !== null).sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [o],
  )
  if (isLoading) return <PageLoader />
  if (error || !o) return <ErrorBox error={error ?? 'Not found'} />

  const points = tests.map((t, i) => ({
    n: i + 1,
    date: dateShort(t.created_at),
    bn: t.language === 'bn' ? t.score : null,
    en: t.language === 'en' ? t.score : null,
    wcpm: t.wcpm,
    title: t.passage_title,
  }))
  const first = tests[0]?.score ?? null
  const last = tests.at(-1)?.score ?? null
  const gain = first !== null && last !== null ? last - first : null
  const bestWcpm = Math.max(0, ...tests.map((t) => t.wcpm ?? 0))
  const perfect = tests.filter((t) => t.score === 10).length

  const BADGES = [
    { icon: BookOpen, name: 'First reading', bn: 'প্রথম পড়া', got: tests.length >= 1, hint: 'Take your first test' },
    { icon: Flame, name: 'Five tests', bn: 'পাঁচটি পড়া', got: tests.length >= 5, hint: `${Math.min(tests.length, 5)}/5 tests` },
    { icon: Star, name: 'Star reader', bn: 'তারকা পাঠক', got: tests.some((t) => (t.score ?? 0) >= 8), hint: 'Get 8/10 or more' },
    { icon: Trophy, name: 'Perfect 10', bn: 'পুরো দশ', got: perfect > 0, hint: 'Get 10/10' },
    { icon: TrendingUp, name: 'Getting better', bn: 'উন্নতি', got: (gain ?? 0) >= 1, hint: 'Improve your mark by 1' },
    { icon: Zap, name: 'Fast reader', bn: 'দ্রুত পাঠক', got: bestWcpm >= 60, hint: 'Read 60 words a minute' },
    { icon: Rocket, name: 'Both languages', bn: 'দুই ভাষা', got: tests.some((t) => t.language === 'bn') && tests.some((t) => t.language === 'en'), hint: 'Read Bangla and English' },
    { icon: Target, name: 'Ten tests', bn: 'দশটি পড়া', got: tests.length >= 10, hint: `${Math.min(tests.length, 10)}/10 tests` },
  ]
  const earned = BADGES.filter((b) => b.got).length

  return (
    <>
      <div className="mb-6">
        <div className="font-bn text-teal-700">আমার অগ্রগতি</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">My progress</h1>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { l: 'Checked tests', v: String(tests.length), t: 'text-ink' },
          { l: 'First mark', v: mark10(first), t: markTone(first) },
          { l: 'Latest mark', v: mark10(last), t: markTone(last) },
          { l: 'Change', v: gain === null ? '—' : `${gain >= 0 ? '+' : ''}${Number.isInteger(gain) ? gain : gain.toFixed(1)}`, t: gain === null ? 'text-slate-400' : gain >= 0 ? 'text-emerald-700' : 'text-rose-700' },
        ].map((s) => (
          <div key={s.l} className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3.5 shadow-sm">
            <div className="text-xs font-medium tracking-wide text-slate-500 uppercase">{s.l}</div>
            <div className={clsx('mt-1 text-2xl font-semibold tabular-nums', s.t)}>{s.v}</div>
          </div>
        ))}
      </div>

      <Card className="mb-6">
        <CardHeader title="My marks over time" subtitle="Each dot is one reading test, out of 10" />
        {points.length < 2 ? (
          <EmptyState title="Take two or more tests to see your line grow." />
        ) : (
          <div className="h-72 px-2 py-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={{ top: 10, right: 40, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#eef2f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} width={30} />
                <ReferenceLine y={8} stroke="#f4a62a" strokeDasharray="4 4" label={{ value: '★ 8', position: 'right', fontSize: 11, fill: '#b45309' }} />
                <Tooltip
                  formatter={(v, name) => [`${v}/10`, name === 'bn' ? 'বাংলা' : 'English']}
                  labelFormatter={(_, p) => (p?.[0]?.payload as { title?: string } | undefined)?.title ?? ''}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                />
                <Line type="monotone" dataKey="bn" name="bn" stroke="#006a4e" strokeWidth={3} dot={{ r: 5, fill: '#006a4e' }} connectNulls />
                <Line type="monotone" dataKey="en" name="en" stroke="#e23a4e" strokeWidth={3} dot={{ r: 5, fill: '#e23a4e' }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-5 text-xs text-slate-600">
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-teal-700" /> <span className="font-bn">বাংলা</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-flag" /> English
              </span>
            </div>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <Award className="size-4 text-marigold" /> My badges
            </span>
          }
          subtitle={`${earned} of ${BADGES.length} earned`}
        />
        <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-4">
          {BADGES.map((b) => (
            <div key={b.name} className={clsx('flex flex-col items-center rounded-2xl p-4 text-center ring-1', b.got ? 'bg-marigold-50 ring-amber-200' : 'bg-slate-50 ring-slate-200')}>
              <div className={clsx('grid size-14 place-items-center rounded-full', b.got ? 'bg-marigold text-ink shadow-md' : 'bg-slate-200 text-slate-400')}>
                <b.icon className="size-7" />
              </div>
              <div className={clsx('mt-3 text-sm font-semibold', b.got ? 'text-ink' : 'text-slate-500')}>{b.name}</div>
              <div className="font-bn text-xs text-slate-500">{b.bn}</div>
              {!b.got && <div className="mt-1 text-[11px] text-slate-400">{b.hint}</div>}
            </div>
          ))}
        </div>
      </Card>
    </>
  )
}
