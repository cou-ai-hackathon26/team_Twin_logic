import { KeyRound, ShieldCheck, Trash2, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { api } from '@/api/client'
import { useMe } from '@/api/hooks'
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, Input, Label, Modal, PageHeader, PageLoader } from '@/components/ui/primitives'
import { dateShort } from '@/lib/format'

interface TeacherRow {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'teacher'
  classes: number
  created_at: string
  locked: boolean
}

const KEY = ['admin', 'teachers']

/** Admin only: create teacher accounts, reset their passwords, remove them. Teachers then create student logins. */
export function TeachersPage() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const list = useQuery({ queryKey: KEY, queryFn: () => api.get<TeacherRow[]>('/admin/teachers'), enabled: me?.role === 'admin' })
  const refresh = () => qc.invalidateQueries({ queryKey: KEY })
  const create = useMutation({
    mutationFn: (b: { username: string; display_name: string; password: string }) => api.post<TeacherRow>('/admin/teachers', b),
    onSuccess: refresh,
  })
  const reset = useMutation({ mutationFn: (b: { id: number; password: string }) => api.put(`/admin/teachers/${b.id}/password`, { password: b.password }) })
  const remove = useMutation({ mutationFn: (id: number) => api.del(`/admin/teachers/${id}`), onSuccess: refresh })

  const [username, setUsername] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [resetFor, setResetFor] = useState<TeacherRow | null>(null)
  const [newPw, setNewPw] = useState('')
  const [removeFor, setRemoveFor] = useState<TeacherRow | null>(null)

  if (me && me.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (list.isLoading) return <PageLoader />

  return (
    <>
      <PageHeader
        title="Teachers"
        subtitle="As admin you create teacher accounts. Each teacher then adds students and creates their logins on the student's page."
      />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Accounts" subtitle="Admin sees every class; a teacher sees their own and shared classes." />
          <ErrorBox error={list.error ?? remove.error} className="mx-5 mt-3" />
          {!list.data?.length ? (
            <EmptyState title="No teacher accounts yet" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {list.data.map((u) => (
                <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3">
                  <div className="grid size-9 place-items-center rounded-full bg-teal-50 text-xs font-bold uppercase text-teal-800">{u.username.slice(0, 2)}</div>
                  <div className="min-w-0 flex-1 leading-tight">
                    <div className="font-semibold text-ink">
                      {u.display_name} <span className="font-mono text-xs font-normal text-slate-500">{u.username}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {u.role === 'admin' ? 'all classes' : `${u.classes} own class${u.classes === 1 ? '' : 'es'}`} · since {dateShort(u.created_at)}
                    </div>
                  </div>
                  {u.role === 'admin' ? (
                    <Badge className="bg-slate-800 text-white ring-slate-800">
                      <ShieldCheck className="mr-1 inline size-3" /> Admin
                    </Badge>
                  ) : (
                    <Badge className="bg-teal-50 text-teal-800 ring-teal-200">Teacher</Badge>
                  )}
                  {u.locked && <Badge className="bg-amber-50 text-amber-800 ring-amber-200">locked</Badge>}
                  {u.role === 'teacher' && (
                    <span className="flex gap-1">
                      <Button size="sm" variant="secondary" onClick={() => (setResetFor(u), setNewPw(''), reset.reset())}>
                        <KeyRound className="size-3.5" /> Password
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setRemoveFor(u)} aria-label={`Remove ${u.username}`}>
                        <Trash2 className="size-4" />
                      </Button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="h-fit">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <UserPlus className="size-4 text-teal-700" /> Add a teacher
              </span>
            }
          />
          <form
            className="space-y-3 p-5"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate(
                { username, display_name: name, password },
                { onSuccess: () => (setUsername(''), setName(''), setPassword('')) },
              )
            }}
          >
            <div>
              <Label htmlFor="t-user">Username (letters, numbers, . _ -)</Label>
              <Input id="t-user" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
            </div>
            <div>
              <Label htmlFor="t-name">Name shown in the app (optional)</Label>
              <Input id="t-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="t-pw">First password (8+ characters; the teacher should change it)</Label>
              <Input id="t-pw" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <Button type="submit" disabled={username.trim().length < 3 || password.length < 8} loading={create.isPending}>
              <UserPlus className="size-4" /> Create teacher account
            </Button>
            {create.isSuccess && <p className="text-sm text-teal-700">Created. Share the username and first password with the teacher privately.</p>}
            <ErrorBox error={create.error} />
            <p className="text-xs text-slate-500">
              Students are not created here: a teacher adds them to a class, then uses <b>Create login</b> on the student's page.
            </p>
          </form>
        </Card>
      </div>

      <Modal
        open={!!resetFor}
        onClose={() => setResetFor(null)}
        title={`New password for ${resetFor?.username ?? ''}`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setResetFor(null)}>
              Cancel
            </Button>
            <Button
              disabled={newPw.length < 8}
              loading={reset.isPending}
              onClick={() => resetFor && reset.mutate({ id: resetFor.id, password: newPw }, { onSuccess: () => setResetFor(null) })}
            >
              Save password
            </Button>
          </>
        }
      >
        <Label htmlFor="t-newpw">New password (8+ characters). The teacher is logged out everywhere.</Label>
        <Input id="t-newpw" type="password" autoComplete="new-password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
        <ErrorBox error={reset.error} className="mt-2" />
      </Modal>

      <Modal
        open={!!removeFor}
        onClose={() => setRemoveFor(null)}
        title={`Remove ${removeFor?.username ?? ''}?`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setRemoveFor(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={remove.isPending} onClick={() => removeFor && remove.mutate(removeFor.id, { onSuccess: () => setRemoveFor(null) })}>
              Remove account
            </Button>
          </>
        }
      >
        Only the login is removed. The teacher's {removeFor?.classes ?? 0} class(es), students and readings stay and become shared with all teachers.
      </Modal>
    </>
  )
}
