import { ArrowLeft, Mic, Printer, Trash2, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAddStudent, useAddStudentsBulk, useClassroom, useDeleteClassroom } from '@/api/hooks'
import type { ClassPattern } from '@/api/types'
import { GradeBadge, MarkBadge, PatternChip } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Input, Label, Modal, PageHeader, PageLoader, ProgressBar, Stat } from '@/components/ui/primitives'
import { dateShort, mark10, markTone, num, wcpmTone } from '@/lib/format'

function AddStudentsModal({ classroomId, open, onClose }: { classroomId: number; open: boolean; onClose: () => void }) {
  const one = useAddStudent(classroomId)
  const bulk = useAddStudentsBulk(classroomId)
  const [mode, setMode] = useState<'one' | 'bulk'>('bulk')
  const [code, setCode] = useState('')
  const [nickname, setNickname] = useState('')
  const [count, setCount] = useState(30)
  const [prefix, setPrefix] = useState('Roll ')
  const [start, setStart] = useState(1)
  const busy = one.isPending || bulk.isPending
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'one') one.mutate({ code, nickname: nickname || null }, { onSuccess: () => (setCode(''), setNickname(''), onClose()) })
    else bulk.mutate({ count, prefix, start }, { onSuccess: onClose })
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add students"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="add-students" loading={busy} disabled={mode === 'one' && !code.trim()}>
            Add
          </Button>
        </>
      }
    >
      <div className="mb-4 inline-flex rounded-lg bg-slate-100 p-1 text-sm">
        {(['bulk', 'one'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-md px-3 py-1.5 font-medium ${mode === m ? 'bg-white shadow-sm' : 'text-slate-600'}`}
          >
            {m === 'bulk' ? 'Roll numbers' : 'One student'}
          </button>
        ))}
      </div>
      <form id="add-students" onSubmit={submit} className="space-y-4">
        {mode === 'one' ? (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Roll / code</Label>
              <Input autoFocus value={code} onChange={(e) => setCode(e.target.value)} placeholder="Roll 07" />
            </div>
            <div>
              <Label>Nickname (optional)</Label>
              <Input value={nickname} onChange={(e) => setNickname(e.target.value)} />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label>How many</Label>
              <Input type="number" min={1} max={120} value={count} onChange={(e) => setCount(Number(e.target.value))} />
            </div>
            <div>
              <Label>Prefix</Label>
              <Input value={prefix} onChange={(e) => setPrefix(e.target.value)} />
            </div>
            <div>
              <Label>Start at</Label>
              <Input type="number" min={0} value={start} onChange={(e) => setStart(Number(e.target.value))} />
            </div>
          </div>
        )}
        <p className="text-xs text-slate-500">
          Privacy: PoraBondhu stores only a roll code and an optional nickname, never a full name or photo.
        </p>
        <ErrorBox error={one.error || bulk.error} />
      </form>
    </Modal>
  )
}

function PatternMap({ items, students }: { items: ClassPattern[]; students: number }) {
  if (!items.length)
    return (
      <EmptyState title="No error patterns yet">Patterns appear after children have read and their errors repeat across readings.</EmptyState>
    )
  const max = Math.max(...items.map((p) => p.errors), 1)
  return (
    <ul className="divide-y divide-slate-100">
      {items.slice(0, 12).map((p) => (
        <li key={p.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-5 py-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <PatternChip p={p} strong={p.students_candidate > 0} />
              <span className="text-xs text-slate-500">{p.category_en}</span>
            </div>
            <ProgressBar className="mt-2" value={p.errors / max} tone={p.students_candidate ? 'bg-rose-500' : 'bg-slate-400'} />
            {p.students.length > 0 && <div className="mt-1 truncate text-xs text-slate-500">Weak for: {p.students.join(', ')}</div>}
          </div>
          <div className="text-right text-sm">
            <div className="font-semibold tabular-nums text-slate-800">
              {p.students_candidate}/{students}
            </div>
            <div className="text-xs text-slate-500">{p.errors} errors</div>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function ClassPage() {
  const id = Number(useParams().id)
  const { data, isLoading, error } = useClassroom(id)
  const del = useDeleteClassroom()
  const nav = useNavigate()
  const [adding, setAdding] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)

  if (isLoading) return <PageLoader />
  if (error || !data) return <ErrorBox error={error ?? 'Class not found'} />

  return (
    <>
      <PageHeader
        back={
          <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
            <ArrowLeft className="size-4" /> Classes
          </Link>
        }
        title={
          <span className="flex items-center gap-3">
            {data.name} <GradeBadge grade={data.grade} />
          </span>
        }
        subtitle={data.school}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmDel(true)} aria-label="Delete class">
              <Trash2 className="size-4" />
            </Button>
            <Button variant="secondary" onClick={() => window.print()} title="Print or save the class report as PDF">
              <Printer className="size-4" /> Report
            </Button>
            <Button variant="secondary" onClick={() => setAdding(true)}>
              <UserPlus className="size-4" /> Add students
            </Button>
            <Link to={`/assess?classroom=${id}`}>
              <Button>
                <Mic className="size-4" /> Assess a child
              </Button>
            </Link>
          </>
        }
      />
      <AddStudentsModal classroomId={id} open={adding} onClose={() => setAdding(false)} />
      <Modal
        open={confirmDel}
        onClose={() => setConfirmDel(false)}
        title="Delete this class?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDel(false)}>
              Keep it
            </Button>
            <Button variant="danger" loading={del.isPending} onClick={() => del.mutate(id, { onSuccess: () => nav('/dashboard') })}>
              Delete class and all readings
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">All students, readings and stored audio of this class are deleted permanently.</p>
      </Modal>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Assessed" value={`${data.stats.assessed}/${data.stats.students}`} hint="children with at least one reading" />
        <Stat label="Mean WCPM" value={num(data.stats.mean_wcpm)} tone={wcpmTone(data.stats.mean_wcpm)} hint="words correct per minute" />
        <Stat label="Average mark" value={mark10(data.stats.mean_score)} tone={markTone(data.stats.mean_score)} hint="out of 10, all reading tests" />
        <Stat label="To review" value={data.stats.unreviewed} hint="readings waiting for the teacher" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Students" subtitle="Latest reading and candidate weak patterns per child" />
          {!data.students.length ? (
            <EmptyState icon={<Users className="size-10" />} title="No students yet">
              <Button className="mt-3" onClick={() => setAdding(true)}>
                <UserPlus className="size-4" /> Add students
              </Button>
            </EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-2 font-medium">Student</th>
                    <th className="px-3 py-2 font-medium">Latest mark</th>
                    <th className="px-3 py-2 font-medium">Average</th>
                    <th className="px-3 py-2 font-medium">WCPM</th>
                    <th className="px-3 py-2 font-medium">Weak patterns</th>
                    <th className="px-3 py-2 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.students.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-5 py-3">
                        <Link to={`/students/${s.id}`} className="font-medium text-slate-900 hover:text-teal-700">
                          {s.code}
                        </Link>
                        {s.nickname && <span className="ml-2 text-slate-500">{s.nickname}</span>}
                        <div className="text-xs text-slate-500">
                          {s.readings} reading{s.readings === 1 ? '' : 's'}
                          {s.latest && ` · last ${dateShort(s.latest.created_at)}`}
                          {s.unreviewed > 0 && <span className="ml-1 font-medium text-indigo-700">· {s.unreviewed} to review</span>}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <MarkBadge score={s.latest?.score} />
                      </td>
                      <td className={`px-3 py-3 font-semibold tabular-nums ${markTone(s.mean_score)}`}>{mark10(s.mean_score)}</td>
                      <td className={`px-3 py-3 tabular-nums ${wcpmTone(s.latest?.wcpm)}`}>{num(s.latest?.wcpm)}</td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          {s.candidate_patterns.slice(0, 3).map((p) => (
                            <PatternChip key={p.key} p={p} strong />
                          ))}
                          {!s.candidate_patterns.length && <span className="text-xs text-slate-400">—</span>}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-right">
                        <Link to={`/assess?student=${s.id}`}>
                          <Button size="sm" variant="secondary">
                            <Mic className="size-3.5" /> Assess
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Class pattern map" subtitle="Which Bangla units the class misreads most. Number = children with it as a weak pattern." />
          <PatternMap items={data.pattern_map} students={data.stats.students} />
        </Card>
      </div>
    </>
  )
}
