import clsx from 'clsx'
import { Check, Mic, Upload } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useClassroom, useClassrooms, usePassages, useStudent, useUploadReading } from '@/api/hooks'
import { GradeBadge, LanguageBadge, PatternChip } from '@/components/domain'
import type { Language } from '@/api/types'
import { langFont } from '@/lib/format'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Label, PageHeader, PageLoader, Select } from '@/components/ui/primitives'

export function AssessPage() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const presetStudent = Number(params.get('student')) || null
  const presetPassage = Number(params.get('passage')) || null
  const presetClass = Number(params.get('classroom')) || null

  const classes = useClassrooms()
  const preStudent = useStudent(presetStudent ?? 0)
  const [classId, setClassId] = useState<number | null>(presetClass)
  const [studentId, setStudentId] = useState<number | null>(presetStudent)
  const [passageId, setPassageId] = useState<number | null>(presetPassage)
  const [gradeFilter, setGradeFilter] = useState<number | 'all'>('all')
  const [langFilter, setLangFilter] = useState<Language | 'all'>('all')
  const fileRef = useRef<HTMLInputElement>(null)
  const upload = useUploadReading()

  useEffect(() => {
    if (preStudent.data && !classId) setClassId(preStudent.data.classroom.id)
  }, [preStudent.data, classId])
  useEffect(() => {
    if (!classId && classes.data?.length === 1) setClassId(classes.data[0].id)
  }, [classes.data, classId])

  const cls = useClassroom(classId ?? 0)
  const passages = usePassages()
  useEffect(() => {
    if (cls.data && gradeFilter === 'all' && !presetPassage) setGradeFilter(cls.data.grade)
    // only when the class changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cls.data?.id])

  const shownPassages = useMemo(
    () =>
      (passages.data ?? []).filter(
        (p) => (gradeFilter === 'all' || p.grade === gradeFilter) && (langFilter === 'all' || p.language === langFilter),
      ),
    [passages.data, gradeFilter, langFilter],
  )
  const ready = !!studentId && !!passageId

  const onFile = (f: File | undefined) => {
    if (!f || !studentId || !passageId) return
    upload.mutate({ studentId, passageId, audio: f, filename: f.name }, { onSuccess: (r) => nav(`/readings/${r.id}`) })
  }

  if (classes.isLoading) return <PageLoader />
  if (!classes.data?.length)
    return (
      <Card>
        <EmptyState title="Create a class first">Add a class and students before recording a reading.</EmptyState>
      </Card>
    )

  return (
    <>
      <PageHeader title="New assessment" subtitle="Choose the child and a passage, then hand the device to the child." />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Card className="self-start">
          <CardHeader title="1 · Child" />
          <div className="space-y-4 p-5">
            <div>
              <Label>Class</Label>
              <Select value={classId ?? ''} onChange={(e) => (setClassId(Number(e.target.value) || null), setStudentId(null))}>
                <option value="">Choose a class…</option>
                {classes.data.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} (Grade {c.grade})
                  </option>
                ))}
              </Select>
            </div>
            {cls.data && (
              <div>
                <Label>Student</Label>
                {cls.data.students.length ? (
                  <div className="grid max-h-80 grid-cols-2 gap-2 overflow-y-auto pr-1 sm:grid-cols-3 lg:grid-cols-2">
                    {cls.data.students.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => setStudentId(s.id)}
                        className={clsx(
                          'rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                          studentId === s.id ? 'border-teal-600 bg-teal-50 ring-1 ring-teal-600' : 'border-slate-200 hover:border-slate-300',
                        )}
                      >
                        <div className="font-medium">{s.code}</div>
                        <div className="text-xs text-slate-500">{s.nickname || `${s.readings} readings`}</div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">This class has no students yet.</p>
                )}
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="2 · Passage"
            actions={
              <div className="flex gap-2">
              <Select className="w-32" value={langFilter} onChange={(e) => setLangFilter(e.target.value as Language | 'all')}>
                <option value="all">All languages</option>
                <option value="bn">Bangla</option>
                <option value="en">English</option>
              </Select>
              <Select className="w-36" value={gradeFilter} onChange={(e) => setGradeFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}>
                <option value="all">All grades</option>
                {[1, 2, 3, 4, 5].map((g) => (
                  <option key={g} value={g}>
                    Grade {g}
                  </option>
                ))}
              </Select>
              </div>
            }
          />
          {passages.isLoading ? (
            <PageLoader />
          ) : (
            <div className="grid gap-3 p-5 md:grid-cols-2">
              {shownPassages.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPassageId(p.id)}
                  className={clsx(
                    'relative rounded-xl border p-4 text-left transition-colors',
                    passageId === p.id ? 'border-teal-600 bg-teal-50/60 ring-1 ring-teal-600' : 'border-slate-200 hover:border-slate-300',
                  )}
                >
                  {passageId === p.id && <Check className="absolute top-3 right-3 size-5 text-teal-700" />}
                  <div className="flex items-center gap-2">
                    <span className={`text-lg font-semibold ${langFont(p.language)}`}>{p.title}</span>
                    <GradeBadge grade={p.grade} />
                    <LanguageBadge language={p.language} />
                  </div>
                  <p className={`mt-2 line-clamp-2 text-sm text-slate-600 ${langFont(p.language)}`}>{p.text}</p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {p.patterns?.slice(0, 4).map((pt) => (
                      <PatternChip key={pt.key} p={pt} count={pt.count} />
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="sticky bottom-0 z-10 -mx-4 mt-6 border-t border-slate-200 bg-white/90 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div className="flex flex-wrap items-center justify-end gap-3">
          <ErrorBox error={upload.error} className="mr-auto" />
          <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          <Button variant="secondary" size="lg" disabled={!ready} loading={upload.isPending} onClick={() => fileRef.current?.click()}>
            <Upload className="size-5" /> Upload a recording
          </Button>
          <Button size="lg" disabled={!ready} onClick={() => nav(`/read/${studentId}/${passageId}`)}>
            <Mic className="size-5" /> Start reading
          </Button>
        </div>
      </div>
    </>
  )
}
