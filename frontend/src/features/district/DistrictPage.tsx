import clsx from 'clsx'
import { ArrowLeft, BookOpenText, Building2, Download, EyeOff, LogOut, ShieldCheck, TrendingUp } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { useLogout, useMe } from '@/api/hooks'
import { Logo } from '@/components/brand'
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, PageLoader, Stat } from '@/components/ui/primitives'

interface Cell {
  hidden: boolean
  children: number
  children_with_errors?: number
  errors?: number
  opportunities?: number
  error_rate?: number | null
}
interface Practice {
  id: number
  code: string | null
  title: string
  grade: number
  occurrences: number
}
interface Unit extends Cell {
  key: string
  category: string
  bn: string
  en: string
  glyph: string
  practice?: Practice[]
}
interface SchoolRow {
  id: number
  name: string
  upazila: string | null
  district: string | null
  classes: number
  children: number
  assessed: number
  hidden: boolean
  reviewed_readings?: number
  median_wcpm?: number | null
  categories?: Record<string, Cell>
  weakest?: Unit[]
}
interface Summary {
  generated: string
  min_group: number
  categories: { key: string; bn: string; en: string }[]
  totals: {
    schools: number
    children: number
    assessed: number
    reviewed_readings: number
    simulated_readings: number
    median_wcpm: number | null
    categories: Record<string, Cell>
    weakest: Unit[]
  }
  schools: SchoolRow[]
  trend: {
    week: string
    children: number
    hidden: boolean
    median_wcpm: number | null
  }[]
  unassigned_classes: number
}

const pct = (x?: number | null) => (x == null ? '–' : `${(x * 100).toFixed(1)}%`)

/** Error rate -> background: calm teal for low, amber, then rose for the hardest units. */
function heat(rate?: number | null) {
  if (rate == null) return undefined
  const t = Math.min(1, rate / 0.35)
  const hue = 165 - 165 * t // 165 teal -> 0 red
  return { backgroundColor: `hsl(${hue} 70% ${92 - 22 * t}%)` }
}

function useSignOut() {
  const logout = useLogout()
  const nav = useNavigate()
  return () => logout.mutate(undefined, { onSettled: () => nav('/login') })
}

/** District officer view: which written units children struggle with, school by school. Counts only. */
export function DistrictPage() {
  const { data: me } = useMe()
  const out = useSignOut()
  const q = useQuery({
    queryKey: ['district', 'summary'],
    queryFn: () => api.get<Summary>('/district/summary'),
  })
  const d = q.data

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-10">
          <Logo to={me?.role === 'admin' ? '/dashboard' : '/district'} />
          <div className="hidden leading-tight sm:block">
            <div className="text-sm font-semibold text-ink">District view</div>
            <div className="font-bn text-xs text-slate-500">জেলা সারাংশ · শুধু সংখ্যা</div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {me?.role === 'admin' && (
              <Link to="/admin/schools">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="size-4" /> Schools
                </Button>
              </Link>
            )}
            <span className="hidden text-sm text-slate-600 md:inline">{me?.display_name}</span>
            <Button variant="secondary" size="sm" onClick={out}>
              <LogOut className="size-4" /> Log out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-[1.75rem] leading-tight font-semibold tracking-tight text-ink">Where children need help with reading</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Which written units (যুক্তাক্ষর, কার, ফলা, রেফ…) children misread most, school by school, from readings their teachers have checked. Use it to plan
              teacher support and practice; it is not a ranking of schools or teachers.
            </p>
          </div>
          <a href="/api/district/summary.csv" download>
            <Button variant="secondary">
              <Download className="size-4" /> Download CSV
            </Button>
          </a>
        </div>

        <div className="flex items-start gap-2 rounded-2xl bg-teal-50 px-4 py-3 text-sm text-teal-900 ring-1 ring-teal-200">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" />
          <span>
            <b>Counts only.</b> No child, roll number, recording or single reading is shown. Only teacher-checked readings are counted, and any group of fewer
            than {d?.min_group ?? 5} children is hidden. <span className="font-bn">শিশুর নাম বা কণ্ঠ এখানে দেখা যায় না।</span>
          </span>
        </div>

        {q.isLoading ? (
          <PageLoader />
        ) : !d ? (
          <ErrorBox error={q.error} />
        ) : (
          <>
            {d.totals.simulated_readings > 0 && (
              <div className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
                <b>DEMO · simulated.</b> {d.totals.simulated_readings} of {d.totals.reviewed_readings} counted readings are simulated practice history on
                fictional demo schools, so these numbers show how the view works, not real results.
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <Stat label="Schools" value={d.totals.schools} hint={d.unassigned_classes ? `${d.unassigned_classes} class(es) not in a school` : undefined} />
              <Stat label="Children" value={d.totals.children} />
              <Stat label="Assessed" value={d.totals.assessed} hint="with a checked reading" />
              <Stat label="Checked readings" value={d.totals.reviewed_readings} />
              <Stat label="Median WCPM" value={d.totals.median_wcpm ?? '–'} hint="words correct per minute" />
            </div>

            {!d.schools.length ? (
              <Card>
                <EmptyState icon={<Building2 className="size-6" />} title="No schools yet">
                  An admin adds schools and places teachers in them on the Schools page.
                </EmptyState>
              </Card>
            ) : (
              <>
                <Card>
                  <CardHeader
                    title="Hardest written units across the district"
                    subtitle="Error rate = misread ÷ times read, over every checked reading. Each unit links to passages that practise it."
                  />
                  <UnitList units={d.totals.weakest} />
                </Card>

                <Card>
                  <CardHeader title="School × unit" subtitle="Error rate per kind of written unit. Darker = more errors. – = too few children to show." />
                  <div className="overflow-x-auto px-5 pb-5">
                    <table className="w-full min-w-[760px] border-separate border-spacing-1 text-sm">
                      <thead>
                        <tr>
                          <th className="px-2 py-1 text-left text-xs font-medium tracking-wide text-slate-500 uppercase">School</th>
                          <th className="px-2 py-1 text-right text-xs font-medium tracking-wide text-slate-500 uppercase">WCPM</th>
                          {d.categories.map((c) => (
                            <th key={c.key} className="px-2 py-1 text-center text-xs font-medium text-slate-600">
                              <div className="font-bn text-sm text-ink">{c.bn}</div>
                              <div className="text-[11px] font-normal text-slate-500">{c.en}</div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {d.schools.map((s) => (
                          <tr key={s.id}>
                            <td className="px-2 py-1.5">
                              <div className="font-medium text-ink">{s.name}</div>
                              <div className="text-xs text-slate-500">
                                {s.assessed} of {s.children} children assessed
                              </div>
                            </td>
                            {s.hidden ? (
                              <td colSpan={d.categories.length + 1} className="rounded-lg bg-slate-50 px-3 text-xs text-slate-500">
                                <EyeOff className="mr-1 inline size-3.5" /> Too few assessed children to show (fewer than {d.min_group})
                              </td>
                            ) : (
                              <>
                                <td className="px-2 text-right font-semibold tabular-nums">{s.median_wcpm ?? '–'}</td>
                                {d.categories.map((c) => {
                                  const cell = s.categories?.[c.key]
                                  return (
                                    <td
                                      key={c.key}
                                      className={clsx('rounded-lg px-2 py-2 text-center tabular-nums', cell?.hidden && 'bg-slate-50 text-slate-400')}
                                      style={cell?.hidden ? undefined : heat(cell?.error_rate)}
                                      title={
                                        cell?.hidden
                                          ? `${cell.children} children read this kind of unit: too few to show`
                                          : `${cell?.errors} errors in ${cell?.opportunities} · ${cell?.children_with_errors} of ${cell?.children} children made at least one`
                                      }
                                    >
                                      {cell?.hidden ? '–' : pct(cell?.error_rate)}
                                    </td>
                                  )
                                })}
                              </>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                  {d.schools
                    .filter((s) => !s.hidden)
                    .map((s) => (
                      <Card key={s.id}>
                        <CardHeader
                          title={s.name}
                          subtitle={`${[s.upazila, s.district].filter(Boolean).join(' · ')} · ${s.classes} class${s.classes === 1 ? '' : 'es'} · ${s.reviewed_readings} checked readings · median WCPM ${s.median_wcpm ?? '–'}`}
                        />
                        <UnitList units={(s.weakest ?? []).slice(0, 3)} compact />
                      </Card>
                    ))}
                </div>

                <Card>
                  <CardHeader
                    title={
                      <span className="flex items-center gap-2">
                        <TrendingUp className="size-4 text-teal-700" /> Reading speed by week (all schools)
                      </span>
                    }
                    subtitle="Median words correct per minute of checked readings. Weeks with fewer children than the limit are hidden."
                  />
                  <Trend trend={d.trend} />
                </Card>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function UnitList({ units, compact }: { units: Unit[]; compact?: boolean }) {
  if (!units.length) return <p className="px-5 pb-5 text-sm text-slate-500">Not enough checked readings yet to rank units.</p>
  return (
    <ul className="divide-y divide-slate-100">
      {units.map((u, i) => (
        <li key={u.key} className="grid gap-3 px-5 py-3 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] md:items-center">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl font-bn text-xl text-ink ring-1 ring-black/5" style={heat(u.error_rate)}>
              {u.glyph}
            </span>
            <div className="min-w-0">
              <div className="font-bn font-semibold text-ink">
                {!compact && <span className="mr-1 text-slate-400">{i + 1}.</span>}
                {u.bn}
              </div>
              <div className="text-xs text-slate-500">
                {u.en} · <b className="text-slate-700">{pct(u.error_rate)}</b> misread · {u.children_with_errors} of {u.children} children
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <BookOpenText className="size-3.5 text-slate-400" />
            {u.practice?.length ? (
              u.practice.map((p) => (
                <Badge key={p.id} className="bg-white text-slate-700 ring-slate-200" title={`${p.occurrences} times in this passage · grade ${p.grade}`}>
                  {p.code ? <b className="mr-1">{p.code}</b> : null}
                  <span className="font-bn">{p.title}</span>
                </Badge>
              ))
            ) : (
              <span className="text-xs text-slate-400">No passage practises this yet</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Trend({ trend }: { trend: Summary['trend'] }) {
  const max = Math.max(1, ...trend.map((w) => w.median_wcpm ?? 0))
  return (
    <div className="flex h-48 items-end gap-2 px-5 pt-2 pb-5">
      {trend.map((w) => (
        <div key={w.week} className="flex flex-1 flex-col items-center gap-1">
          <div className={clsx('text-xs tabular-nums', w.hidden ? 'text-slate-400' : 'font-semibold text-slate-700')}>
            {w.hidden ? 'too few' : w.median_wcpm}
          </div>
          <div className="flex h-28 w-full items-end">
            <div
              className={clsx('w-full rounded-t-lg', w.hidden ? 'bg-slate-100' : 'bg-teal-600/80')}
              style={{
                height: w.hidden ? '6%' : `${Math.max(6, ((w.median_wcpm ?? 0) / max) * 100)}%`,
              }}
              title={w.hidden ? `${w.children} children: too few to show` : `${w.children} children`}
            />
          </div>
          <div className="text-[11px] text-slate-500">{w.week.slice(5)}</div>
        </div>
      ))}
    </div>
  )
}
