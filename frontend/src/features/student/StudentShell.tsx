import clsx from 'clsx'
import { BookOpen, Dumbbell, LogOut, Star, TrendingUp } from 'lucide-react'
import { NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from 'react-router-dom'
import { useLogout, useMe, useMyOverview, useMyPractice } from '@/api/hooks'
import { Logo } from '@/components/brand'
import { useLearned } from './practiceStore'

const TABS = [
  { to: '/me', label: 'My tests', bn: 'পড়া', icon: BookOpen, end: true },
  { to: '/me/practice', label: 'Practice', bn: 'অনুশীলন', icon: Dumbbell, badge: true },
  { to: '/me/progress', label: 'Progress', bn: 'অগ্রগতি', icon: TrendingUp },
]

/** Top-bar layout for the student role. The reading screen is full-screen. */
export function StudentShell() {
  const { data: me } = useMe()
  const overview = useMyOverview()
  const practice = useMyPractice()
  const logout = useLogout()
  const nav = useNavigate()
  const loc = useLocation()
  const { learned } = useLearned()
  if (loc.pathname.startsWith('/me/read/')) return <Outlet />

  // stars: one per test marked 8/10 or better
  const stars = (overview.data?.history ?? []).filter((h) => (h.score ?? 0) >= 8).length
  const toPractise = (practice.data ?? []).filter((w) => !learned.has(w.expected)).length
  const name = overview.data?.nickname || me?.student?.code

  return (
    <div className="flex min-h-full flex-col">
      <ScrollRestoration />
      <header className="sticky top-0 z-30 border-b border-paper-200 bg-paper/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-4 px-4">
          <Logo to="/me" sub="আমার পড়া · My reading" />
          <nav className="ml-4 hidden items-center gap-1 rounded-2xl bg-paper-200/70 p-1 sm:flex">
            {TABS.map(({ to, label, bn, icon: Icon, end, badge }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  clsx(
                    'relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition-all',
                    isActive ? 'bg-white text-teal-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-ink',
                  )
                }
              >
                <Icon className="size-4" />
                <span>{label}</span>
                <span className="font-bn text-xs font-normal opacity-60">{bn}</span>
                {badge && toPractise > 0 && <span className="min-w-5 rounded-full bg-flag px-1.5 text-center text-[11px] leading-5 font-bold text-white">{toPractise}</span>}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-1.5 rounded-full bg-marigold-50 px-3 py-1.5 text-sm font-bold text-amber-800 ring-1 ring-amber-200" title="Stars: tests with 8/10 or more">
              <Star className="size-4 fill-marigold text-marigold" /> {stars}
            </div>
            <div className="hidden text-right text-sm leading-tight md:block">
              <div className="font-semibold text-ink">{name}</div>
              <div className="text-xs text-slate-500">{me?.student?.classroom}</div>
            </div>
            <button
              onClick={() => logout.mutate(undefined, { onSettled: () => nav('/login') })}
              className="grid size-10 place-items-center rounded-xl text-slate-500 hover:bg-white hover:text-ink"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 pb-28 sm:pb-6">
        <Outlet />
      </main>

      {/* mobile tabs */}
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur sm:hidden">
        {TABS.map(({ to, label, bn, icon: Icon, end, badge }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => clsx('flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold', isActive ? 'text-teal-700' : 'text-slate-500')}>
            <span className="relative">
              <Icon className="size-5" />
              {badge && toPractise > 0 && <span className="absolute -top-1.5 -right-3 min-w-4 rounded-full bg-flag px-1 text-center text-[9px] leading-4 text-white">{toPractise}</span>}
            </span>
            {label}
            <span className="font-bn text-[10px] font-normal opacity-70">{bn}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
