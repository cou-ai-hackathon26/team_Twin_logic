import clsx from 'clsx'
import { Bell, BookOpenText, ExternalLink, FlaskConical, HardDrive, Inbox, LayoutDashboard, LogOut, Mic, Search, Settings, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from 'react-router-dom'
import { useClassrooms, useLogout, useMe, useReviewQueue, useSystem } from '@/api/hooks'
import { Logo } from '@/components/brand'
import { CommandPalette } from './CommandPalette'

const BN_DIGITS = '০১২৩৪৫৬৭৮৯'
const bnNum = (n: number) => String(n).replace(/\d/g, (d) => BN_DIGITS[Number(d)])

type NavItem = { to: string; label: string; short: string; icon: typeof Mic; end?: boolean; badge?: 'review' }
const GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Teaching',
    items: [
      { to: '/dashboard', label: 'Dashboard', short: 'Home', icon: LayoutDashboard, end: true },
      { to: '/assess', label: 'New assessment', short: 'Assess', icon: Mic },
      { to: '/review', label: 'Review queue', short: 'Review', icon: Inbox, badge: 'review' },
      { to: '/passages', label: 'Passages', short: 'Passages', icon: BookOpenText },
    ],
  },
  {
    title: 'AI lab',
    items: [
      { to: '/engine', label: 'Grapheme engine', short: 'Engine', icon: Sparkles },
      { to: '/benchmark', label: 'Benchmark', short: 'Bench', icon: FlaskConical },
    ],
  },
  { title: 'Account', items: [{ to: '/settings', label: 'Settings', short: 'Settings', icon: Settings }] },
]
const ALL = GROUPS.flatMap((g) => g.items)
const MOBILE = ALL.filter((i) => ['/dashboard', '/assess', '/review', '/passages', '/settings'].includes(i.to))

const TITLES: [RegExp, string, string][] = [
  [/^\/dashboard/, 'Dashboard', 'ড্যাশবোর্ড'],
  [/^\/assess/, 'New assessment', 'নতুন মূল্যায়ন'],
  [/^\/review/, 'Review queue', 'যাচাইয়ের তালিকা'],
  [/^\/readings\//, 'Reading review', 'পড়া যাচাই'],
  [/^\/classes\//, 'Class', 'শ্রেণি'],
  [/^\/students\//, 'Student', 'শিক্ষার্থী'],
  [/^\/passages/, 'Passages', 'পাঠ্যাংশ'],
  [/^\/engine/, 'Grapheme engine', 'বর্ণ বিশ্লেষণ'],
  [/^\/benchmark/, 'Benchmark', 'মূল্যায়ন ফলাফল'],
  [/^\/settings/, 'Settings', 'সেটিংস'],
]

function ModelPill() {
  const { data } = useSystem()
  const st = data?.models.ctc.state
  const map = {
    ready: ['bg-emerald-400', 'Speech model ready'],
    loading: ['bg-marigold animate-pulse', 'Speech model loading'],
    error: ['bg-flag', 'Speech model error'],
    not_loaded: ['bg-teal-200/40', 'Loads on first use'],
  } as const
  const [dot, label] = map[st ?? 'not_loaded']
  return (
    <div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2.5 text-xs text-teal-100/80 ring-1 ring-white/10">
      <span className={clsx('size-2 rounded-full', dot)} />
      <span>{label}</span>
      <span className="ml-auto flex items-center gap-1 text-teal-200/50">
        <HardDrive className="size-3" /> Local
      </span>
    </div>
  )
}

function useSignOut() {
  const logout = useLogout()
  const nav = useNavigate()
  return () => logout.mutate(undefined, { onSettled: () => nav('/login') })
}

function Count({ n, dark }: { n: number; dark?: boolean }) {
  if (!n) return null
  return (
    <span className={clsx('ml-auto min-w-5 rounded-full px-1.5 text-center text-[11px] leading-5 font-bold tabular-nums', dark ? 'bg-marigold text-ink' : 'bg-flag text-white')}>
      {n > 99 ? '99+' : n}
    </span>
  )
}

function UserBox() {
  const { data: me } = useMe()
  const out = useSignOut()
  return (
    <div className="mt-3 flex items-center gap-3 rounded-xl px-2 py-2">
      <div className="grid size-9 place-items-center rounded-full bg-marigold text-xs font-bold text-ink uppercase">{me?.username.slice(0, 2)}</div>
      <div className="min-w-0 flex-1 leading-tight">
        <div className="truncate text-sm font-semibold text-white">{me?.display_name}</div>
        <div className="font-bn text-xs text-teal-200/60">শিক্ষক · Teacher</div>
      </div>
      <button onClick={out} className="rounded-lg p-2 text-teal-200/70 hover:bg-white/10 hover:text-white" aria-label="Log out" title="Log out">
        <LogOut className="size-4" />
      </button>
    </div>
  )
}

function ClassLinks() {
  const { data } = useClassrooms()
  if (!data?.length) return null
  return (
    <div>
      <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-teal-200/40">My classes</div>
      <div className="flex flex-col gap-0.5">
        {data.map((c) => (
          <NavLink
            key={c.id}
            to={`/classes/${c.id}`}
            className={({ isActive }) =>
              clsx('flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors', isActive ? 'bg-white/10 text-white' : 'text-teal-100/70 hover:bg-white/5 hover:text-white')
            }
          >
            <span className="grid size-6 place-items-center rounded-md bg-white/10 font-bn text-xs text-teal-100">{bnNum(c.grade)}</span>
            <span className="min-w-0 flex-1 truncate">{c.name}</span>
            {c.stats.unreviewed > 0 && <span className="text-[11px] font-semibold tabular-nums text-marigold">{c.stats.unreviewed}</span>}
          </NavLink>
        ))}
      </div>
    </div>
  )
}

export function AppShell() {
  const loc = useLocation()
  const out = useSignOut()
  const queue = useReviewQueue()
  const pending = queue.data?.length ?? 0
  const [palette, setPalette] = useState(false)
  const childMode = loc.pathname.startsWith('/read/')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && (e.target.closest('input, textarea, select, [contenteditable]') !== null)
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
        e.preventDefault()
        setPalette(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  if (childMode) return <Outlet />
  const title = TITLES.find(([re]) => re.test(loc.pathname))
  const hour = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="flex min-h-full">
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
      <ScrollRestoration />
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-y-auto bg-teal-950 px-4 py-5 text-teal-50 md:flex">
        <Logo to="/dashboard" dark sub="শিক্ষকের ড্যাশবোর্ড" className="mb-6 px-2" />
        <button
          onClick={() => setPalette(true)}
          className="mb-6 flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2.5 text-sm text-teal-100/60 ring-1 ring-white/10 hover:bg-white/10 hover:text-white"
        >
          <Search className="size-4" /> Search…
          <kbd className="ml-auto rounded bg-white/10 px-1.5 text-[10px] font-medium">Ctrl K</kbd>
        </button>
        <nav className="flex flex-1 flex-col gap-6">
          {GROUPS.map((g, gi) => (
            <div key={g.title}>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-teal-200/40">{g.title}</div>
              <div className="flex flex-col gap-0.5">
                {g.items.map(({ to, label, icon: Icon, end, badge }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      clsx(
                        'relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                        isActive ? 'bg-white/10 text-white' : 'text-teal-100/70 hover:bg-white/5 hover:text-white',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && <span className="absolute top-2 bottom-2 -left-4 w-1 rounded-r-full bg-marigold" />}
                        <Icon className={clsx('size-[18px]', isActive && 'text-marigold')} />
                        {label}
                        {badge === 'review' && <Count n={pending} dark />}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
              {gi === 0 && (
                <div className="mt-6">
                  <ClassLinks />
                </div>
              )}
            </div>
          ))}
        </nav>
        <Link to="/" className="mt-6 mb-3 flex items-center gap-2 px-3 text-xs text-teal-200/50 hover:text-white">
          <ExternalLink className="size-3.5" /> About PoraBondhu
        </Link>
        <ModelPill />
        <UserBox />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="sticky top-0 z-30 border-b border-paper-200 bg-paper/85 backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 lg:px-10">
            <div className="md:hidden">
              <Logo to="/dashboard" sub="শিক্ষক" />
            </div>
            <div className="hidden min-w-0 md:block">
              <div className="flex items-baseline gap-2">
                <span className="font-display text-lg font-semibold text-ink">{title?.[1] ?? 'PoraBondhu'}</span>
                {title && <span className="font-bn text-sm text-teal-700">{title[2]}</span>}
              </div>
              <div className="text-xs text-slate-500">{hour}</div>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => setPalette(true)}
                className="hidden h-10 w-64 items-center gap-2 rounded-xl bg-white px-3 text-sm text-slate-400 ring-1 ring-slate-200 hover:ring-teal-300 lg:flex"
              >
                <Search className="size-4" /> Find a student, class…
                <kbd className="ml-auto rounded bg-slate-100 px-1.5 text-[10px] font-medium text-slate-500">Ctrl K</kbd>
              </button>
              <button onClick={() => setPalette(true)} className="grid size-10 place-items-center rounded-xl bg-white text-slate-600 ring-1 ring-slate-200 lg:hidden" aria-label="Search">
                <Search className="size-4" />
              </button>
              <Link
                to="/review"
                className="relative grid size-10 place-items-center rounded-xl bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-teal-300"
                aria-label={`${pending} readings to review`}
                title={`${pending} readings to review`}
              >
                <Bell className="size-4" />
                {pending > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-5 rounded-full bg-flag px-1 text-center text-[10px] leading-5 font-bold text-white ring-2 ring-paper">{pending > 99 ? '99+' : pending}</span>
                )}
              </Link>
              <Link to="/assess" className="hidden h-10 items-center gap-2 rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 sm:inline-flex">
                <Mic className="size-4" /> Assess
              </Link>
              <button onClick={out} className="grid size-10 place-items-center rounded-xl text-slate-500 hover:bg-white md:hidden" aria-label="Log out">
                <LogOut className="size-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 pb-28 sm:px-6 md:pb-6 lg:px-10 lg:py-8">
          <Outlet />
        </main>
        <footer className="hidden items-center justify-center gap-2 py-5 text-xs text-slate-400 md:flex">
          <HardDrive className="size-3.5" /> Runs fully on this computer. A teacher’s aid, not an official test.
        </footer>

        {/* mobile bottom tabs */}
        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
          {MOBILE.map(({ to, short, icon: Icon, end, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => clsx('flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium', isActive ? 'text-teal-700' : 'text-slate-500')}
            >
              {({ isActive }) => (
                <>
                  <span className={clsx('relative grid h-7 w-12 place-items-center rounded-full', isActive && 'bg-teal-50')}>
                    <Icon className="size-[18px]" />
                    {badge === 'review' && pending > 0 && (
                      <span className="absolute -top-1 right-1 min-w-4 rounded-full bg-flag px-1 text-center text-[9px] leading-4 font-bold text-white">{pending > 99 ? '99+' : pending}</span>
                    )}
                  </span>
                  {short}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
