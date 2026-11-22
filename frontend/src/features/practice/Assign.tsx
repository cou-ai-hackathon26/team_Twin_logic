import clsx from 'clsx'
import { BookOpenCheck, CheckCircle2, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useAssign, useDeleteAssignment } from '@/api/practice'
import { usePassages } from '@/api/hooks'
import type { Assignment, PatternLabel } from '@/api/types'
import { Button, ErrorBox, Label, Modal, Select, Textarea } from '@/components/ui/primitives'
import { dateShort, langFont } from '@/lib/format'

/**
 * Give practice to one child, a weak-pattern group or a whole class.
 * With a weak pattern, the server picks practice words and a passage that contain that unit.
 */
export function AssignModal({
  open,
  onClose,
  studentIds,
  who,
  grade,
  pattern,
}: {
  open: boolean
  onClose: () => void
  studentIds: number[]
  who: string
  grade: number
  pattern?: PatternLabel | null
}) {
  const assign = useAssign()
  const { data: passages } = usePassages()
  const [passageId, setPassageId] = useState<number | ''>('')
  const [note, setNote] = useState('')
  const [done, setDone] = useState<string | null>(null)
  const nearby = (passages ?? []).filter((p) => Math.abs(p.grade - grade) <= 1 && (!pattern || p.language === 'bn'))

  const submit = () =>
    assign.mutate(
      { student_ids: studentIds, passage_id: passageId || null, pattern_key: pattern?.key ?? null, note },
      {
        onSuccess: (r) =>
          setDone(
            `Sent to ${r.created} child${r.created === 1 ? '' : 'ren'}${r.passage ? `: read “${r.passage}”` : ''}${r.words.length ? ` and practise ${r.words.slice(0, 5).join(', ')}` : ''}.`,
          ),
      },
    )
  const close = () => {
    setDone(null)
    setPassageId('')
    setNote('')
    assign.reset()
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title={pattern ? `Assign practice: ${pattern.bn}` : 'Assign a passage'}
      footer={
        done ? (
          <Button onClick={close}>Close</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={close}>
              Cancel
            </Button>
            <Button onClick={submit} loading={assign.isPending} disabled={!pattern && !passageId}>
              <Send className="size-4" /> Assign to {who}
            </Button>
          </>
        )
      }
    >
      {done ? (
        <p className="flex items-start gap-2 text-teal-800">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0" /> <span className="font-bn">{done}</span>
        </p>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            {pattern ? (
              <>
                Practice words containing <b className="font-bn">{pattern.bn}</b> and a passage that practises it are chosen from the passage bank.
                The {studentIds.length === 1 ? 'child sees' : `${studentIds.length} children see`} it on their home page.
              </>
            ) : (
              <>
                {studentIds.length === 1 ? 'The child sees' : `${studentIds.length} children see`} the passage under “From your teacher”. It is marked done
                when they read it.
              </>
            )}
          </p>
          <div>
            <Label htmlFor="as-passage">{pattern ? 'Passage (optional, otherwise chosen for you)' : 'Passage'}</Label>
            <Select id="as-passage" value={passageId} onChange={(e) => setPassageId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">{pattern ? 'Choose for me' : 'Select a passage'}</option>
              {nearby.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} · {p.title} (Grade {p.grade}, {p.language === 'bn' ? 'বাংলা' : 'English'})
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="as-note">Note to the child (optional)</Label>
            <Textarea id="as-note" rows={2} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} className="font-bn" placeholder="যেমন: র-ফলা ওয়ালা শব্দগুলো জোরে পড়ো" />
          </div>
          <ErrorBox error={assign.error} />
        </div>
      )}
    </Modal>
  )
}

/** Assignments already given (teacher view). */
export function AssignmentList({ items, showStudent }: { items: Assignment[]; showStudent?: boolean }) {
  const del = useDeleteAssignment()
  if (!items.length) return <p className="px-5 py-4 text-sm text-slate-500">No practice assigned yet.</p>
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((a) => (
        <li key={a.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-sm">
          {a.done ? <CheckCircle2 className="size-4 text-teal-600" /> : <BookOpenCheck className="size-4 text-amber-600" />}
          {showStudent && <span className="font-medium text-slate-700">{a.student_code}</span>}
          {a.pattern && <span className="rounded-md bg-rose-50 px-1.5 font-bn text-rose-800">{a.pattern.bn}</span>}
          {a.passage && <span className={clsx('text-slate-800', langFont(a.passage.language))}>{a.passage.title}</span>}
          {a.words.length > 0 && <span className="font-bn text-slate-500">{a.words.slice(0, 4).join(', ')}{a.words.length > 4 ? '…' : ''}</span>}
          <span className="ml-auto text-xs text-slate-500">
            {a.done ? `done ${dateShort(a.done_at ?? a.created_at)}` : `given ${dateShort(a.created_at)}`}
          </span>
          <button className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700" onClick={() => del.mutate(a.id)} aria-label="Remove assignment" title="Remove">
            <Trash2 className="size-3.5" />
          </button>
        </li>
      ))}
    </ul>
  )
}
