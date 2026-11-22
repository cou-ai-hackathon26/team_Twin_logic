import clsx from 'clsx'
import { ArrowLeft, GraduationCap, Hand, KeyRound, LogIn, Mic, ScanSearch, School } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useLogin, useMe } from '@/api/hooks'
import type { Role } from '@/api/types'
import { Button, ErrorBox, Input, Label, PageLoader } from '@/components/ui/primitives'
import { Logo } from '@/components/brand'
import { homeFor } from './home'

const TABS: { role: Role; label: string; bn: string; icon: typeof School; hint: string }[] = [
  { role: 'teacher', label: 'Teacher', bn: 'শিক্ষক', icon: School, hint: 'Demo: teacher / teacher123' },
  { role: 'student', label: 'Student', bn: 'শিক্ষার্থী', icon: GraduationCap, hint: 'Demo: c3r01 / student123 (class 3, roll 01)' },
]

export function LoginPage() {
  const me = useMe()
  const login = useLogin()
  const nav = useNavigate()
  const navState = useLocation().state as { from?: string; role?: Role } | null
  const from = navState?.from
  const initialRole = navState?.role
  const [role, setRole] = useState<Role>(initialRole ?? 'teacher')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (me.isLoading) return <PageLoader />
  if (me.data) return <Navigate to={homeFor(me.data.role)} replace />

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    login.mutate(
      { username: username.trim(), password, role },
      { onSuccess: (u) => nav(from && u.role === 'teacher' && !from.startsWith('/me') ? from : homeFor(u.role), { replace: true }) },
    )
  }
  const tab = TABS.find((t) => t.role === role)!

  return (
    <div className="grid min-h-full lg:grid-cols-[1.05fr_1fr]">
      {/* brand panel */}
      <div className="relative hidden overflow-hidden bg-teal-950 p-12 text-white lg:flex lg:flex-col">
        <div className="bg-dots pointer-events-none absolute inset-0 opacity-25 [filter:invert(1)]" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-16 -bottom-24 select-none font-bn-display text-[26rem] leading-none text-white/[0.04]">
          পড়া
        </div>
        <div aria-hidden="true" className="absolute top-24 right-24 size-28 rounded-full bg-flag/90" />
        <Logo dark className="relative" />
        <div className="relative mt-auto max-w-lg">
          <h1 className="font-display text-5xl leading-[1.08] font-semibold tracking-tight">Every child heard reading.</h1>
          <p className="mt-3 font-bn-display text-2xl text-teal-200">প্রতিটি শিশুর পড়া শোনা হোক।</p>
          <ul className="mt-10 space-y-4 text-teal-50/90">
            {[
              [Mic, 'Record a child reading in under two minutes'],
              [ScanSearch, 'See the exact যুক্তাক্ষর and কার behind each mistake'],
              [Hand, 'You confirm or change every mark'],
            ].map(([I, t]) => {
              const Icon = I as typeof Mic
              return (
                <li key={t as string} className="flex items-center gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white/10 ring-1 ring-white/15">
                    <Icon className="size-4 text-marigold" />
                  </span>
                  <span className="font-bn">{t as string}</span>
                </li>
              )
            })}
          </ul>
        </div>
        <p className="relative mt-16 text-xs text-teal-200/50">Runs on this computer. Audio never leaves the school.</p>
      </div>

      {/* form */}
      <div className="flex flex-col px-5 py-8 sm:px-10">
        <div className="flex items-center justify-between">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-ink">
            <ArrowLeft className="size-4" /> Home
          </Link>
          <Logo className="lg:hidden" />
        </div>
        <div className="mx-auto my-auto w-full max-w-md py-10">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">Welcome back</h2>
          <p className="mt-1 font-bn text-slate-500">স্বাগতম! আপনার অ্যাকাউন্টে প্রবেশ করুন।</p>

          <div className="mt-8 grid grid-cols-2 gap-2 rounded-2xl bg-paper-200/70 p-1.5" role="tablist">
            {TABS.map(({ role: r, label, bn, icon: Icon }) => (
              <button
                key={r}
                role="tab"
                aria-selected={role === r}
                onClick={() => (setRole(r), login.reset())}
                className={clsx(
                  'flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-semibold transition-all',
                  role === r ? 'bg-white text-teal-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-ink',
                )}
              >
                <Icon className="size-4" /> {label} <span className="font-bn text-xs font-normal opacity-70">{bn}</span>
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-6 space-y-5">
            <div>
              <Label htmlFor="username">{role === 'student' ? 'Student username' : 'Username'}</Label>
              <Input id="username" className="h-12 rounded-xl" autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" className="h-12 rounded-xl" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <ErrorBox error={login.error} />
            <Button type="submit" size="lg" className="w-full rounded-xl" loading={login.isPending} disabled={!username.trim() || !password}>
              <LogIn className="size-5" /> Log in as {tab.label.toLowerCase()}
            </Button>
          </form>

          <div className="mt-6 flex items-start gap-3 rounded-xl bg-marigold-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
            <KeyRound className="mt-0.5 size-4 shrink-0" />
            <div>
              <div className="font-medium">Demo account</div>
              <div className="text-amber-800/80">{tab.hint.replace('Demo: ', '')}</div>
            </div>
          </div>
          <p className="mt-6 text-center text-sm text-slate-500">
            {role === 'student' ? 'No login yet? Ask your teacher to create one for you.' : 'Teachers can create student logins from each student’s page.'}
          </p>
        </div>
      </div>
    </div>
  )
}
