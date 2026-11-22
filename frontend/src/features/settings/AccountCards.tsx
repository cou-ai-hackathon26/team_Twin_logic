import { KeyRound, RotateCcw, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useChangePassword, useDemoReset } from '@/api/practice'
import type { SystemInfo } from '@/api/types'
import { Button, Card, CardHeader, ErrorBox, Input, Label, Modal } from '@/components/ui/primitives'

export function PasswordCard() {
  const change = useChangePassword()
  const [cur, setCur] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const mismatch = again.length > 0 && next !== again
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <KeyRound className="size-4 text-teal-700" /> Change my password
          </span>
        }
        subtitle="Do this before using PoraBondhu with real children: the demo password is public."
      />
      <form
        className="grid gap-3 p-5 sm:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault()
          change.mutate({ current_password: cur, new_password: next }, { onSuccess: () => (setCur(''), setNext(''), setAgain('')) })
        }}
      >
        <div>
          <Label htmlFor="pw-cur">Current password</Label>
          <Input id="pw-cur" type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="pw-new">New password (8+ characters)</Label>
          <Input id="pw-new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="pw-again">Repeat new password</Label>
          <Input id="pw-again" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-3 sm:col-span-3">
          <Button type="submit" disabled={!cur || next.length < 8 || next !== again} loading={change.isPending}>
            Save new password
          </Button>
          {mismatch && <span className="text-sm text-rose-700">The new passwords do not match.</span>}
          {change.isSuccess && <span className="text-sm text-teal-700">Password changed.</span>}
          <ErrorBox error={change.error} />
        </div>
      </form>
    </Card>
  )
}

export function PrivacyCard({ settings }: { settings: SystemInfo['settings'] }) {
  const reset = useDemoReset()
  const [confirm, setConfirm] = useState(false)
  const days = settings.audio_retention_days ?? 0
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-teal-700" /> Privacy and safety
          </span>
        }
      />
      <ul className="space-y-2 px-5 py-4 text-sm text-slate-700">
        <li>
          • Recordings are deleted when you finalise a review
          {days > 0 ? `, and automatically ${days} days after recording` : ''} unless you tick “keep audio”.
          {days === 0 && <span className="text-slate-500"> Automatic deletion is off; set PB_AUDIO_RETENTION_DAYS (we recommend 14).</span>}
        </li>
        <li>• Children see their mark and practice words only after you have checked the reading.</li>
        <li>
          • A login is locked for {settings.lockout_minutes ?? 10} minutes after {settings.max_failed_logins ?? 5} wrong passwords in a row.
        </li>
      </ul>
      {settings.demo_mode && (
        <div className="border-t border-slate-100 px-5 py-4">
          <p className="mb-3 text-sm text-slate-600">
            <b>Demo server.</b> Reset deletes every reading recorded here (and its audio) and all assigned practice, so the next visitor never hears
            someone else&apos;s voice. The simulated history stays.
          </p>
          <Button variant="secondary" onClick={() => setConfirm(true)}>
            <RotateCcw className="size-4" /> Reset demo recordings
          </Button>
          {reset.data && (
            <span className="ml-3 text-sm text-teal-700">
              Deleted {reset.data.readings_deleted} recordings and {reset.data.assignments_deleted} assignments.
            </span>
          )}
          <ErrorBox error={reset.error} className="mt-2" />
          <Modal
            open={confirm}
            onClose={() => setConfirm(false)}
            title="Reset the demo?"
            footer={
              <>
                <Button variant="ghost" onClick={() => setConfirm(false)}>
                  Cancel
                </Button>
                <Button onClick={() => reset.mutate(undefined, { onSettled: () => setConfirm(false) })} loading={reset.isPending}>
                  Delete recordings
                </Button>
              </>
            }
          >
            This permanently deletes every real reading recorded on this demo server, its audio and all assigned practice. It cannot be undone.
          </Modal>
        </div>
      )}
    </Card>
  )
}
