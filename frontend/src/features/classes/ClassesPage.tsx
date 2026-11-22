import { ChevronRight, Mic, Plus, School, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useClassrooms, useCreateClassroom, useMe, useRecentReadings } from '@/api/hooks'
import type { ClassroomSummary } from '@/api/types'
import { GradeBadge, LanguageBadge, MarkBadge, ReadingStatusBadge } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Input, Label, Modal, PageHeader, PageLoader, ProgressBar, Select } from '@/components/ui/primitives'
import { dateTime, langFont, mark10, markTone, num, wcpmTone } from '@/lib/format'

function NewClassModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateClassroom()
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [grade, setGrade] = useState(2)
  const [school, setSchool] = useState('')
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    create.mutate(
      { name, grade, school: school || null },
      { onSuccess: (c) => (onClose(), nav(`/classes/${c.id}`)) },
    )
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New class"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button form="new-class" type="submit" loading={create.isPending} disabled={!name.trim()}>
            Create class
          </Button>
        </>
      }
    >
      <form id="new-class" onSubmit={submit} className="space-y-4">
        <div>
          <Label htmlFor="cname">Class name</Label>
          <Input id="cname" autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Class 3 - Section A" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="cgrade">Grade</Label>
            <Select id="cgrade" value={grade} onChange={(e) => setGrade(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="cschool">School (optional)</Label>
            <Input id="cschool" value={school} onChange={(e) => setSchool(e.target.value)} />
          </div>
        </div>
        <ErrorBox error={create.error} />
      </form>
    </Modal>
  )
}

const BN_DIGITS = '০১২৩৪৫৬৭৮৯'
const bnNum = (n: number) => String(n).replace(/\d/g, (d) => BN_DIGITS[Number(d)])

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? ['Good morning', 'শুভ সকাল'] : h < 17 ? ['Good afternoon', 'শুভ অপরাহ্ন'] : ['Good evening', 'শুভ সন্ধ্যা']
}

function WelcomeBanner({ classes }: { classes: ClassroomSummary[] | undefined }) {
  const { data: me } = useMe()
  const [en, bn] = greeting()
  const t = (classes ?? []).reduce(
    (a, c) => ({
      students: a.students + c.stats.students,
      assessed: a.assessed + c.stats.assessed,
      readings: a.readings + c.stats.readings,
      unreviewed: a.unreviewed + c.stats.unreviewed,
      simulated: a.simulated + (c.stats.simulated ?? 0),
    }),
    { students: 0, assessed: 0, readings: 0, unreviewed: 0, simulated: 0 },
  )
  const loading = classes === undefined
  const coverage = t.students ? t.assessed / t.students : 0
  const message = loading
    ? 'Loading your classes…'
    : t.unreviewed > 0
      ? `${t.unreviewed} reading${t.unreviewed > 1 ? 's are' : ' is'} waiting for your review.`
      : t.students
        ? `${t.students - t.assessed} of ${t.students} children still to hear reading.`
        : 'Create a class to start hearing every child read.'
  return (
    <div className="relative mb-10 overflow-hidden rounded-3xl bg-teal-800 p-6 text-white shadow-lg shadow-teal-900/10 sm:p-8">
      <div className="bg-dots pointer-events-none absolute inset-0 opacity-20 [filter:invert(1)]" />
      <div aria-hidden="true" className="pointer-events-none absolute -right-6 -bottom-20 select-none font-bn-display text-[15rem] leading-none text-white/[0.06]">
        পড়া
      </div>
      <div className="relative flex flex-wrap items-end justify-between gap-6">
        <div>
          <div className="font-bn text-sm text-teal-200">{bn}</div>
          <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {en}, {me?.display_name?.split(' ')[0] ?? 'teacher'}
          </h1>
          <p className="mt-2 max-w-lg text-teal-100/80">{message}</p>
        </div>
        <Link to="/assess">
          <Button size="lg" className="rounded-xl !bg-marigold !text-ink shadow-lg hover:!bg-amber-400">
            <Mic className="size-5" /> Start an assessment
          </Button>
        </Link>
      </div>
      <div className="relative mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(
          [
            ['Classes', classes?.length ?? 0],
            ['Students', t.students],
            ['Readings', t.readings],
            ['To review', t.unreviewed],
          ] as const
        ).map(([l, v]) => (
          <div key={l} className="rounded-2xl bg-white/10 px-4 py-3 ring-1 ring-white/15 backdrop-blur">
            <div className="text-xs font-medium uppercase tracking-wide text-teal-100/70">{l}</div>
            <div className={clsx('mt-1 text-2xl font-semibold tabular-nums', l === 'To review' && v > 0 && 'text-marigold')}>
              {loading ? <span className="inline-block h-7 w-10 animate-pulse rounded bg-white/20 align-middle" /> : v}
            </div>
          </div>
        ))}
      </div>
      {t.simulated > 0 && (
        <div className="relative mt-5 rounded-xl bg-white/10 px-4 py-2.5 text-sm text-teal-50 ring-1 ring-white/15">
          <span className="mr-2 rounded bg-white px-1.5 py-0.5 text-[11px] font-bold text-ink">DEMO</span>
          {t.simulated} of {t.readings} readings are <b>simulated</b> practice history (scripted errors run through the real
          marking engine, no audio), so the dashboards are not empty. Every reading you record now is marked live by the models.
        </div>
      )}
      {t.students > 0 && (
        <div className="relative mt-5">
          <div className="mb-1.5 flex justify-between text-xs text-teal-100/80">
            <span>Children heard reading at least once</span>
            <span className="tabular-nums">{Math.round(coverage * 100)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/15">
            <div className="h-full rounded-full bg-marigold transition-all" style={{ width: `${coverage * 100}%` }} />
          </div>
        </div>
      )}
    </div>
  )
}

export function ClassesPage() {
  const { data, isLoading, error } = useClassrooms()
  const recent = useRecentReadings()
  const [open, setOpen] = useState(false)

  return (
    <>
      <WelcomeBanner classes={data} />
      <PageHeader
        title="Your classes"
        subtitle="Open a class to see each child's marks and the class's weak patterns."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="size-4" /> New class
          </Button>
        }
      />
      <NewClassModal open={open} onClose={() => setOpen(false)} />
      <ErrorBox error={error} />
      {isLoading ? (
        <PageLoader />
      ) : !data?.length ? (
        <Card>
          <EmptyState icon={<School className="size-12" />} title="No classes yet">
            Create a class, add students by roll number, then record each child reading a short passage.
            <div className="mt-4">
              <Button onClick={() => setOpen(true)}>
                <Plus className="size-4" /> Create your first class
              </Button>
            </div>
          </EmptyState>
        </Card>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((c) => {
            const cov = c.stats.students ? c.stats.assessed / c.stats.students : 0
            return (
              <Link key={c.id} to={`/classes/${c.id}`} className="group">
                <Card className="h-full overflow-hidden transition-all group-hover:-translate-y-0.5 group-hover:shadow-lg">
                  <div className="flex items-start gap-4 p-5">
                    <div className="grid size-14 shrink-0 place-items-center rounded-2xl bg-teal-50 font-bn-display text-3xl text-teal-800 ring-1 ring-teal-100" title={`Grade ${c.grade}`}>
                      {bnNum(c.grade)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-semibold text-ink">{c.name}</div>
                      <div className="truncate text-sm text-slate-500">{c.school || 'No school set'}</div>
                      <div className="mt-1.5">
                        <GradeBadge grade={c.grade} />
                      </div>
                    </div>
                    {c.stats.unreviewed > 0 && (
                      <span className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200">{c.stats.unreviewed} to review</span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 border-y border-slate-100 bg-slate-50/50 px-5 py-4 text-center">
                    <div>
                      <div className="text-xl font-semibold tabular-nums">
                        {c.stats.assessed}
                        <span className="text-sm text-slate-400">/{c.stats.students}</span>
                      </div>
                      <div className="text-xs text-slate-500">assessed</div>
                    </div>
                    <div>
                      <div className={`text-xl font-semibold tabular-nums ${markTone(c.stats.mean_score)}`}>{mark10(c.stats.mean_score)}</div>
                      <div className="text-xs text-slate-500">average mark</div>
                    </div>
                    <div>
                      <div className={`text-xl font-semibold tabular-nums ${wcpmTone(c.stats.mean_wcpm)}`}>{num(c.stats.mean_wcpm)}</div>
                      <div className="text-xs text-slate-500">mean WCPM</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 px-5 py-3.5 text-sm">
                    <ProgressBar value={cov} className="flex-1" />
                    <span className="flex items-center gap-1.5 text-slate-500" title="Readings">
                      <Users className="size-4" /> {c.stats.readings}
                    </span>
                    <ChevronRight className="size-4 text-slate-400 transition-transform group-hover:translate-x-0.5 group-hover:text-teal-700" />
                  </div>
                </Card>
              </Link>
            )
          })}
        </div>
      )}

      {!!recent.data?.length && (
        <Card className="mt-8">
          <CardHeader title="Recent readings" subtitle="Newest first. Open one to review the marks." />
          <ul className="divide-y divide-slate-100">
            {recent.data.map((r) => (
              <li key={r.id}>
                <Link to={`/readings/${r.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 hover:bg-slate-50">
                  <span className="w-28 font-medium text-slate-800">{r.student_code}</span>
                  <MarkBadge score={r.score} />
                  <span className={`min-w-0 flex-1 truncate text-slate-700 ${langFont(r.language)}`}>{r.passage_title}</span>
                  <LanguageBadge language={r.language} />
                  <span className={`w-20 text-sm tabular-nums ${wcpmTone(r.wcpm)}`}>{num(r.wcpm)} WCPM</span>
                  <span className="w-32 text-sm text-slate-500">{dateTime(r.created_at)}</span>
                  <ReadingStatusBadge status={r.status} reviewed={r.reviewed} simulated={r.simulated} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
