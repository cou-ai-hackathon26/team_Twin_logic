import clsx from 'clsx'
import { BookOpenCheck, Check, Mic } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useFinishAssignment, useMyAssignments } from '@/api/practice'
import { useSayWord } from '@/components/audio'
import { Button, Card, CardHeader } from '@/components/ui/primitives'
import { langFont } from '@/lib/format'
import { WordCheck } from './WordCheck'

function Word({ w }: { w: string }) {
  const { say } = useSayWord('bn')
  return (
    <div className="rounded-2xl bg-white p-3 text-center ring-1 ring-slate-200">
      <button type="button" onClick={() => void say(w)} className="font-bn text-2xl font-semibold text-ink hover:text-teal-700" title="Hear it">
        {w}
      </button>
      <WordCheck word={w} />
    </div>
  )
}

/** Practice the teacher assigned, on the student's home page. */
export function FromTeacher() {
  const { data } = useMyAssignments()
  const finish = useFinishAssignment()
  const open = (data ?? []).filter((a) => !a.done)
  if (!open.length) return null
  return (
    <Card className="mb-6 ring-2 ring-teal-200">
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <BookOpenCheck className="size-5 text-teal-700" /> From your teacher <span className="font-bn text-sm font-normal text-slate-500">· শিক্ষকের দেওয়া কাজ</span>
          </span>
        }
        subtitle="Tap a word to hear it, then say it yourself."
      />
      <ul className="divide-y divide-slate-100">
        {open.map((a) => (
          <li key={a.id} className="space-y-3 px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              {a.pattern && <span className="rounded-md bg-rose-50 px-2 py-0.5 font-bn text-rose-800 ring-1 ring-rose-200">{a.pattern.bn}</span>}
              {a.note && <span className="font-bn text-slate-700">{a.note}</span>}
            </div>
            {a.words.length > 0 && (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {a.words.slice(0, 8).map((w) => (
                  <Word key={w} w={w} />
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {a.passage && (
                <Link to={`/me/read/${a.passage.id}`}>
                  <Button size="sm">
                    <Mic className="size-4" /> Read <span className={clsx('ml-1', langFont(a.passage.language))}>{a.passage.title}</span>
                  </Button>
                </Link>
              )}
              {a.words.length > 0 && (
                <Button size="sm" variant="secondary" onClick={() => finish.mutate(a.id)} loading={finish.isPending}>
                  <Check className="size-4" /> I practised these words
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
