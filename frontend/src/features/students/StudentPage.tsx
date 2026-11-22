import { ArrowLeft, BookOpen, KeyRound, Mic, Pencil, Printer, Send, Trash2 } from 'lucide-react'
import { useStudentAssignments } from '@/api/practice'
import { AssignModal, AssignmentList } from '@/features/practice/Assign'
import type { PatternLabel } from '@/api/types'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDeleteStudent, useDeleteStudentAccount, useSetStudentAccount, useStudent, useUpdateStudent } from '@/api/hooks'
import type { PatternStat, StudentDetail } from '@/api/types'
import { LanguageBadge, MarkBadge, PatternChip, ReadingStatusBadge } from '@/components/domain'
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, Input, Label, Modal, PageHeader, PageLoader, ProgressBar, Stat } from '@/components/ui/primitives'
import { dateShort, dateTime, langFont, mark10, markTone, num, wcpmTone } from '@/lib/format'

function ProgressChart({ data }: { data: StudentDetail['progress'] }) {
  if (data.length < 2) return <EmptyState title="Progress appears after two readings" />
  const rows = data.map((d) => ({ ...d, label: dateShort(d.date) }))
  return (
    <div className="h-64 px-2 py-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis yAxisId="w" tick={{ fontSize: 12, fill: '#64748b' }} width={36} />
          <YAxis yAxisId="a" orientation="right" domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} tick={{ fontSize: 12, fill: '#64748b' }} width={28} />
          <Tooltip
            formatter={(v, name) => (name === 'Mark' ? `${v}/10` : v)}
            labelFormatter={(_l, p) => (p?.[0]?.payload as { passage?: string })?.passage ?? ''}
          />
          <Line yAxisId="w" type="monotone" dataKey="wcpm" name="WCPM" stroke="#0f766e" strokeWidth={2.5} dot={{ r: 3 }} />
          <Line yAxisId="a" type="monotone" dataKey="score" name="Mark" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function PatternTable({ items }: { items: PatternStat[] }) {
  const shown = items.filter((p) => p.key !== 'skip')
  if (!shown.length) return <EmptyState title="No errors recorded yet" />
  return (
    <ul className="divide-y divide-slate-100">
      {shown.slice(0, 12).map((p) => (
        <li key={p.key} className="px-5 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <PatternChip p={p} strong={p.candidate} />
              {p.candidate && <Badge className="bg-rose-600 text-white ring-rose-600">Candidate weak pattern</Badge>}
            </div>
            <div className="text-sm tabular-nums text-slate-600">
              {p.errors} errors / {p.opportunities} seen · {p.readings_with_error} reading{p.readings_with_error === 1 ? '' : 's'}
            </div>
          </div>
          <ProgressBar className="mt-2" value={p.error_rate ?? 0} tone={p.candidate ? 'bg-rose-500' : 'bg-slate-400'} />
          {p.examples.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-bn text-sm text-slate-600">
              {p.examples.slice(0, 4).map((e, i) => (
                <Link key={i} to={`/readings/${e.reading_id}`} className="hover:text-teal-700">
                  {e.expected} <span className="text-slate-400">→</span> <span className="text-rose-700">{e.heard || '—'}</span>
                </Link>
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}

function EditStudent({ s, open, onClose }: { s: StudentDetail; open: boolean; onClose: () => void }) {
  const upd = useUpdateStudent(s.id)
  const [code, setCode] = useState(s.code)
  const [nickname, setNickname] = useState(s.nickname ?? '')
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit student"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={upd.isPending} onClick={() => upd.mutate({ code, nickname }, { onSuccess: onClose })}>
            Save
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Roll / code</Label>
          <Input value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <div>
          <Label>Nickname</Label>
          <Input value={nickname} onChange={(e) => setNickname(e.target.value)} />
        </div>
      </div>
      <ErrorBox className="mt-3" error={upd.error} />
    </Modal>
  )
}

function StudentLogin({ s }: { s: StudentDetail }) {
  const save = useSetStudentAccount(s.id)
  const remove = useDeleteStudentAccount(s.id)
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const show = () => {
    setUsername(s.username ?? '')
    setPassword('')
    save.reset()
    setOpen(true)
  }
  return (
    <Card>
      <CardHeader
        title="Student login"
        subtitle="The student can log in to take reading tests and see their own marks"
        actions={
          <Button size="sm" variant="secondary" onClick={show}>
            <KeyRound className="size-4" /> {s.username ? 'Change' : 'Create login'}
          </Button>
        }
      />
      <div className="px-5 py-4 text-sm">
        {s.username ? (
          <div className="flex items-center justify-between gap-3">
            <span>
              Username: <span className="font-mono font-medium text-slate-900">{s.username}</span>
            </span>
            <Button size="sm" variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()}>
              Remove login
            </Button>
          </div>
        ) : (
          <span className="text-slate-500">No login yet. Only the teacher can record this student.</span>
        )}
        <ErrorBox className="mt-2" error={remove.error} />
      </div>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={s.username ? 'Change student login' : 'Create student login'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={save.isPending}
              disabled={username.trim().length < 3 || password.length < 4}
              onClick={() => save.mutate({ username: username.trim(), password }, { onSuccess: () => setOpen(false) })}
            >
              Save login
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Username</Label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. c3r07" autoComplete="off" />
          </div>
          <div>
            <Label>{s.username ? 'New password' : 'Password'}</Label>
            <Input type="text" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">Letters, numbers, dot, dash or underscore; at least 3 characters. Password at least 4 characters.</p>
        <ErrorBox className="mt-3" error={save.error} />
      </Modal>
    </Card>
  )
}

export function StudentPage() {
  const id = Number(useParams().id)
  const { data, isLoading, error } = useStudent(id)
  const del = useDeleteStudent()
  const nav = useNavigate()
  const [editing, setEditing] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const [assigning, setAssigning] = useState<{ pattern: PatternLabel | null } | null>(null)
  const assignments = useStudentAssignments(id)
  if (isLoading) return <PageLoader />
  if (error || !data) return <ErrorBox error={error ?? 'Student not found'} />
  const latest = data.latest
  const candidates = data.patterns.filter((p) => p.candidate)

  return (
    <>
      <PageHeader
        back={
          <Link to={`/classes/${data.classroom.id}`} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
            <ArrowLeft className="size-4" /> {data.classroom.name}
          </Link>
        }
        title={
          <span>
            {data.code} {data.nickname && <span className="font-normal text-slate-500">· {data.nickname}</span>}
          </span>
        }
        subtitle={`Grade ${data.classroom.grade} · ${data.readings} reading${data.readings === 1 ? '' : 's'}`}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmDel(true)} aria-label="Delete student">
              <Trash2 className="size-4" />
            </Button>
            <Button variant="secondary" onClick={() => window.print()} title="Print or save as PDF for the parent meeting">
              <Printer className="size-4" /> Report
            </Button>
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil className="size-4" /> Edit
            </Button>
            <Link to={`/assess?student=${id}`}>
              <Button>
                <Mic className="size-4" /> New reading
              </Button>
            </Link>
          </>
        }
      />
      {editing && <EditStudent s={data} open onClose={() => setEditing(false)} />}
      <Modal
        open={confirmDel}
        onClose={() => setConfirmDel(false)}
        title="Delete this student?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDel(false)}>
              Keep
            </Button>
            <Button
              variant="danger"
              loading={del.isPending}
              onClick={() => del.mutate({ id, classroom_id: data.classroom.id }, { onSuccess: () => nav(`/classes/${data.classroom.id}`) })}
            >
              Delete student and readings
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">All readings and stored audio of this student are deleted permanently.</p>
      </Modal>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Latest mark" value={mark10(latest?.score)} tone={markTone(latest?.score)} hint={latest?.passage_title} />
        <Stat label="Average mark" value={mark10(data.mean_score)} tone={markTone(data.mean_score)} hint="out of 10" />
        <Stat label="Latest WCPM" value={num(latest?.wcpm)} tone={wcpmTone(latest?.wcpm)} hint="words correct per minute" />
        <Stat label="Weak patterns" value={candidates.length} hint="repeated across readings" />
        <Stat label="To review" value={data.unreviewed} />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Progress" subtitle="Mark out of 10 and words correct per minute over time" />
          <ProgressChart data={data.progress} />
        </Card>
        <Card>
          <CardHeader title="What to teach next" subtitle="Practice for each candidate weak pattern, from the passage bank" />
          {!data.recommendations.length ? (
            <EmptyState icon={<BookOpen className="size-10" />} title="No candidate weak patterns yet">
              A unit becomes a weak pattern only after repeated errors across more than one reading, never after a single slip.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recommendations.map((r) => (
                <li key={r.pattern.key} className="space-y-2 px-5 py-4">
                  <div className="flex items-center justify-between gap-2">
                    <PatternChip p={r.pattern} strong />
                    <Button size="sm" variant="secondary" onClick={() => setAssigning({ pattern: r.pattern })}>
                      <Send className="size-3.5" /> Assign practice
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {r.practice_words.map((w) => (
                      <span key={w} className="rounded-md bg-teal-50 px-2 py-0.5 font-bn text-base text-teal-900">
                        {w}
                      </span>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {r.passages.map((p) => (
                      <Link key={p.id} to={`/assess?student=${id}&passage=${p.id}`} className="rounded-md border border-slate-200 px-2 py-1 hover:border-teal-600 hover:text-teal-800">
                        <span className="font-bn">{p.title}</span>{' '}
                        <span className="text-xs text-slate-500">
                          G{p.grade} · {p.occurrences}×
                        </span>
                      </Link>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader
            title="Practice given"
            subtitle="Shown to the child under “From your teacher”; done when they read the passage or tick the words"
            actions={
              <Button size="sm" variant="secondary" onClick={() => setAssigning({ pattern: null })}>
                <Send className="size-3.5" /> Assign a passage
              </Button>
            }
          />
          <AssignmentList items={assignments.data ?? []} />
        </Card>
        <AssignModal
          open={!!assigning}
          onClose={() => setAssigning(null)}
          studentIds={[id]}
          who={data.code}
          grade={data.classroom.grade}
          pattern={assigning?.pattern}
        />
        <StudentLogin s={data} />
        <Card>
          <CardHeader title="Grapheme patterns" subtitle="Confirmed errors per Bangla unit (transparent counts)" />
          <PatternTable items={data.patterns} />
        </Card>
        <Card>
          <CardHeader title="Readings" />
          {!data.history.length ? (
            <EmptyState title="No readings yet" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.history.map((r) => (
                <li key={r.id}>
                  <Link to={`/readings/${r.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 hover:bg-slate-50">
                    <MarkBadge score={r.score} />
                    <span className={`min-w-0 flex-1 truncate ${langFont(r.language)}`}>{r.passage_title}</span>
                    <LanguageBadge language={r.language} />
                    <span className={`text-sm tabular-nums ${wcpmTone(r.wcpm)}`}>{num(r.wcpm)} WCPM</span>
                    <span className="text-sm text-slate-500">{dateTime(r.created_at)}</span>
                    <ReadingStatusBadge status={r.status} reviewed={r.reviewed} simulated={r.simulated} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
