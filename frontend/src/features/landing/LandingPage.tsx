import clsx from 'clsx'
import { ReadingBuddy } from '@/components/ReadingBuddy'
import {
  ArrowRight,
  AudioLines,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  EyeOff,
  GraduationCap,
  HardDrive,
  Hand,
  LayoutDashboard,
  ListChecks,
  Menu,
  Mic,
  School,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useMe } from '@/api/hooks'
import { Logo, LogoMark } from '@/components/brand'
import { homeFor } from '@/features/auth/home'

/* ------------------------------------------------------------------ data */

type DemoState = 'idle' | 'correct' | 'misread' | 'skipped' | 'unsure'
const DEMO_WORDS: { w: string; final: DemoState; said?: string }[] = [
  { w: 'আমাদের', final: 'correct' },
  { w: 'গ্রামের', final: 'misread', said: 'গামের' },
  { w: 'নাম', final: 'correct' },
  { w: 'সোনাপুর।', final: 'correct' },
  { w: 'প্রতিদিন', final: 'misread', said: 'পতিদিন' },
  { w: 'সকালে', final: 'correct' },
  { w: 'আমি', final: 'correct' },
  { w: 'স্কুলে', final: 'unsure' },
  { w: 'যাই।', final: 'correct' },
  { w: 'বৃষ্টি', final: 'skipped' },
  { w: 'হলে', final: 'correct' },
  { w: 'ছাতা', final: 'correct' },
  { w: 'নিই।', final: 'correct' },
]

const WORD_CLS: Record<DemoState, string> = {
  idle: 'text-slate-400',
  correct: 'text-ink',
  misread: 'bg-rose-50 text-rose-900 underline decoration-rose-500 decoration-2 underline-offset-[7px]',
  skipped: 'bg-slate-100 text-slate-500 line-through decoration-slate-500 decoration-2',
  unsure: 'bg-amber-50 text-amber-900 underline decoration-amber-500 decoration-dotted decoration-2 underline-offset-[7px]',
}

type Kind = 'base' | 'kar' | 'fola' | 'ref' | 'sign' | 'hasant'
const KIND_META: Record<Kind, { label: string; bn: string; cls: string }> = {
  base: { label: 'Consonant', bn: 'ব্যঞ্জন', cls: 'bg-white text-ink ring-slate-200' },
  hasant: { label: 'Hasant (joins letters)', bn: 'হসন্ত', cls: 'bg-slate-100 text-slate-500 ring-slate-200' },
  kar: { label: 'Vowel sign', bn: 'কার', cls: 'bg-sky-50 text-sky-900 ring-sky-200' },
  fola: { label: 'Joined second letter', bn: 'ফলা / যুক্তবর্ণ', cls: 'bg-teal-50 text-teal-900 ring-teal-200' },
  ref: { label: 'Reph', bn: 'রেফ', cls: 'bg-violet-50 text-violet-900 ring-violet-200' },
  sign: { label: 'Nasal sign', bn: 'চন্দ্রবিন্দু', cls: 'bg-marigold-50 text-amber-900 ring-amber-200' },
}

type Unit = { text: string; tag: string; parts: { g: string; kind: Kind }[] }
const ENGINE_WORDS: { word: string; gloss: string; units: Unit[]; tip: string }[] = [
  {
    word: 'প্রথম',
    gloss: 'first',
    units: [
      { text: 'প্র', tag: 'র-ফলা conjunct', parts: [{ g: 'প', kind: 'base' }, { g: '্', kind: 'hasant' }, { g: 'র', kind: 'fola' }] },
      { text: 'থ', tag: 'consonant', parts: [{ g: 'থ', kind: 'base' }] },
      { text: 'ম', tag: 'consonant', parts: [{ g: 'ম', kind: 'base' }] },
    ],
    tip: 'If a child says “পথম”, the engine reports exactly one thing: the র-ফলা in প্র was dropped.',
  },
  {
    word: 'স্কুল',
    gloss: 'school',
    units: [
      { text: 'স্কু', tag: 'conjunct + উ-কার', parts: [{ g: 'স', kind: 'base' }, { g: '্', kind: 'hasant' }, { g: 'ক', kind: 'fola' }, { g: 'ু', kind: 'kar' }] },
      { text: 'ল', tag: 'consonant', parts: [{ g: 'ল', kind: 'base' }] },
    ],
    tip: '“ইস্কুল” or “সকুল” are told apart: an added vowel vs. a split conjunct are different teaching targets.',
  },
  {
    word: 'বৃষ্টি',
    gloss: 'rain',
    units: [
      { text: 'বৃ', tag: 'ঋ-কার', parts: [{ g: 'ব', kind: 'base' }, { g: 'ৃ', kind: 'kar' }] },
      { text: 'ষ্টি', tag: 'conjunct + ই-কার', parts: [{ g: 'ষ', kind: 'base' }, { g: '্', kind: 'hasant' }, { g: 'ট', kind: 'fola' }, { g: 'ি', kind: 'kar' }] },
    ],
    tip: 'ি is written before the letter but read after it. Segmenting by grapheme keeps the order right.',
  },
  {
    word: 'কর্ম',
    gloss: 'work',
    units: [
      { text: 'ক', tag: 'consonant', parts: [{ g: 'ক', kind: 'base' }] },
      { text: 'র্ম', tag: 'রেফ conjunct', parts: [{ g: 'র', kind: 'ref' }, { g: '্', kind: 'hasant' }, { g: 'ম', kind: 'base' }] },
    ],
    tip: 'The reph sits on top of ম but is spoken first. A missed reph is counted against রেফ, not ম.',
  },
  {
    word: 'চাঁদ',
    gloss: 'moon',
    units: [
      { text: 'চাঁ', tag: 'আ-কার + চন্দ্রবিন্দু', parts: [{ g: 'চ', kind: 'base' }, { g: 'া', kind: 'kar' }, { g: 'ঁ', kind: 'sign' }] },
      { text: 'দ', tag: 'consonant', parts: [{ g: 'দ', kind: 'base' }] },
    ],
    tip: 'Dropping the nasal sound (চাদ) is flagged on the চন্দ্রবিন্দু, a small mark that is easy to miss.',
  },
]

/* ------------------------------------------------------------- helpers */

function Section({ id, className, children }: { id?: string; className?: string; children: ReactNode }) {
  return (
    <section id={id} className={clsx('scroll-mt-20 px-5 sm:px-8', className)}>
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  )
}

function Eyebrow({ children, tone = 'teal' }: { children: ReactNode; tone?: 'teal' | 'light' }) {
  return (
    <div
      className={clsx(
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider ring-1 ring-inset',
        tone === 'teal' ? 'bg-teal-50 text-teal-800 ring-teal-200' : 'bg-white/10 text-teal-100 ring-white/20',
      )}
    >
      {children}
    </div>
  )
}

function SectionTitle({ eyebrow, title, bn, children, center }: { eyebrow: string; title: ReactNode; bn?: string; children?: ReactNode; center?: boolean }) {
  return (
    <div className={clsx('max-w-2xl', center && 'mx-auto text-center')}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-balance text-ink sm:text-4xl">{title}</h2>
      {bn && <p className="mt-2 font-bn-display text-xl text-teal-700">{bn}</p>}
      {children && <p className="mt-4 text-lg leading-relaxed text-slate-600">{children}</p>}
    </div>
  )
}

/* ------------------------------------------------------------- hero demo */

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex h-8 items-center gap-[3px]" aria-hidden="true">
      {Array.from({ length: 48 }, (_, i) => (
        <span
          key={i}
          className={clsx('w-[3px] origin-center rounded-full', active ? 'animate-wave bg-teal-600' : 'bg-slate-300')}
          style={{ height: `${30 + ((i * 37) % 70)}%`, animationDelay: `${(i % 7) * 0.11}s` }}
        />
      ))}
    </div>
  )
}

function HeroDemo() {
  // step 0..n-1: reading word by word; n: showing diagnosis; then loop
  const n = DEMO_WORDS.length
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setStep((s) => (s >= n + 6 ? 0 : s + 1)), step >= n ? 900 : 420)
    return () => clearTimeout(t)
  }, [step, n])
  const done = step >= n
  const counts = DEMO_WORDS.reduce(
    (a, w, i) => (i < step ? { ...a, [w.final]: (a[w.final] ?? 0) + 1 } : a),
    {} as Record<string, number>,
  )

  return (
    <div className="relative">
      <div className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-gradient-to-br from-teal-200/50 via-marigold/20 to-flag/10 blur-2xl" />
      <div className="overflow-hidden rounded-3xl bg-white shadow-2xl shadow-teal-900/10 ring-1 ring-slate-200">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-3">
          <div className="grid size-9 place-items-center rounded-full bg-teal-50 text-sm font-semibold text-teal-800">রি</div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="text-sm font-semibold text-ink">Roll 07 · Grade 3</div>
            <div className="font-bn text-xs text-slate-500">আমার গ্রাম · ১৩ শব্দ</div>
          </div>
          <span
            className={clsx(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold',
              done ? 'bg-teal-50 text-teal-800' : 'bg-flag/10 text-flag',
            )}
          >
            <span className={clsx('size-1.5 rounded-full', done ? 'bg-teal-600' : 'animate-pulse bg-flag')} />
            {done ? 'Marked' : 'Listening'}
          </span>
        </div>

        <div className="bg-ruled px-5 pt-5 pb-4">
          <p className="font-bn text-[22px] leading-[2.4rem]">
            {DEMO_WORDS.map((w, i) => (
              <span key={i}>
                <span className={clsx('rounded-md px-1 py-0.5 transition-all duration-300', WORD_CLS[i < step ? w.final : 'idle'], i === step && 'bg-teal-100/70 text-ink')}>
                  {w.w}
                </span>{' '}
              </span>
            ))}
          </p>
          <div className="mt-3">
            <Waveform active={!done} />
          </div>
        </div>

        <div className="grid grid-cols-4 divide-x divide-slate-100 border-t border-slate-100 text-center">
          {[
            ['Correct', counts.correct ?? 0, 'text-teal-700'],
            ['Misread', counts.misread ?? 0, 'text-rose-600'],
            ['Skipped', counts.skipped ?? 0, 'text-slate-600'],
            ['Unsure', counts.unsure ?? 0, 'text-amber-600'],
          ].map(([l, v, c]) => (
            <div key={l as string} className="py-2.5">
              <div className={clsx('text-xl font-semibold tabular-nums', c as string)}>{v}</div>
              <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{l}</div>
            </div>
          ))}
        </div>

        <div className={clsx('border-t border-slate-100 bg-slate-50/70 px-5 py-4 transition-opacity duration-500', done ? 'opacity-100' : 'opacity-40')}>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <ScanSearch className="size-3.5" /> Diagnosis
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-3 rounded-xl bg-white px-3 py-2 ring-1 ring-slate-200">
              <span className="font-bn text-lg text-ink">গ্রা → গা</span>
              <span className="font-bn text-lg text-ink">প্র → প</span>
              <span className="ml-auto rounded-md bg-rose-50 px-2 py-0.5 font-bn text-sm font-medium text-rose-800 ring-1 ring-rose-200">র-ফলা ×2</span>
            </div>
            <p className="text-sm text-slate-600">
              <span className="font-semibold text-teal-800">Teach next:</span> words with <span className="font-bn">র-ফলা</span> (প্র, গ্র, ক্র).
            </p>
          </div>
        </div>
      </div>

      <div className="absolute top-28 -left-10 hidden animate-float rounded-2xl bg-white px-4 py-3 shadow-xl ring-1 ring-slate-200 sm:block">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Speed</div>
        <div className="text-2xl font-semibold tabular-nums text-ink">
          46 <span className="text-sm font-medium text-slate-500">WCPM</span>
        </div>
      </div>
      <div className="absolute -right-4 bottom-4 hidden animate-float rounded-2xl bg-ink px-4 py-3 text-white shadow-xl sm:block" style={{ animationDelay: '1.5s' }}>
        <div className="flex items-center gap-2 text-sm font-medium">
          <Hand className="size-4 text-marigold" /> Teacher can change any mark
        </div>
      </div>
      <p className="mt-14 text-center text-xs text-slate-400">Illustration of a marked reading</p>
    </div>
  )
}

/* -------------------------------------------------------- engine explorer */

function EngineExplorer() {
  const [i, setI] = useState(0)
  const w = ENGINE_WORDS[i]
  const kinds = Array.from(new Set(w.units.flatMap((u) => u.parts.map((p) => p.kind))))
  return (
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
        {ENGINE_WORDS.map((x, k) => (
          <button
            key={x.word}
            onClick={() => setI(k)}
            className={clsx(
              'flex shrink-0 items-center justify-between gap-4 rounded-2xl px-4 py-3 text-left transition-all',
              k === i ? 'bg-ink text-white shadow-lg' : 'bg-white text-ink ring-1 ring-slate-200 hover:ring-teal-300',
            )}
          >
            <span className="font-bn-display text-2xl">{x.word}</span>
            <span className={clsx('text-sm', k === i ? 'text-teal-200' : 'text-slate-500')}>{x.gloss}</span>
          </button>
        ))}
      </div>

      <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
        <div className="flex flex-wrap items-baseline gap-4">
          <span className="font-bn-display text-6xl text-ink sm:text-7xl">{w.word}</span>
          <span className="text-slate-500">
            {w.units.length} reading units · “{w.gloss}”
          </span>
        </div>

        <div key={w.word} className="mt-8 flex flex-wrap items-stretch gap-4">
          {w.units.map((u, k) => (
            <div key={k} className="animate-fade-up rounded-2xl bg-paper p-4 ring-1 ring-paper-200" style={{ animationDelay: `${k * 0.12}s` }}>
              <div className="text-center font-bn-display text-4xl text-teal-800">{u.text}</div>
              <div className="mt-3 flex items-center justify-center gap-1.5">
                {u.parts.map((p, j) => (
                  <span key={j} title={KIND_META[p.kind].label} className={clsx('grid h-11 min-w-9 place-items-center rounded-lg px-2 font-bn text-xl ring-1 ring-inset', KIND_META[p.kind].cls)}>
                    {p.kind === 'hasant' || p.kind === 'kar' || p.kind === 'sign' ? `◌${p.g}` : p.g}
                  </span>
                ))}
              </div>
              <div className="mt-2 text-center font-bn text-xs text-slate-500">{u.tag}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {kinds.map((k) => (
            <span key={k} className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset', KIND_META[k].cls)}>
              <span className="font-bn">{KIND_META[k].bn}</span> · {KIND_META[k].label}
            </span>
          ))}
        </div>

        <div className="mt-6 flex gap-3 rounded-2xl bg-teal-50 p-4 text-teal-900">
          <Sparkles className="mt-0.5 size-5 shrink-0 text-teal-700" />
          <p className="font-bn text-[15px] leading-relaxed">{w.tip}</p>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ page */

const NAV_LINKS = [
  ['#how', 'How it works'],
  ['#engine', 'Bangla engine'],
  ['#teachers', 'For teachers'],
  ['#trust', 'Principles'],
]

export function LandingPage() {
  const { data: me } = useMe()
  const [menu, setMenu] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8)
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [])

  const primaryCta = me ? (
    <Link to={homeFor(me.role)} className="btn-cta">
      <LayoutDashboard className="size-5" /> Open {me.role === 'teacher' ? 'dashboard' : 'my reading'}
    </Link>
  ) : (
    <Link to="/login" state={{ role: 'teacher' }} className="btn-cta">
      <School className="size-5" /> Start as a teacher <ArrowRight className="size-4" />
    </Link>
  )

  return (
    <div className="min-h-full bg-paper text-ink">
      {/* ---------------------------------------------------------- nav */}
      <header className={clsx('sticky top-0 z-40 transition-all', scrolled ? 'border-b border-paper-200 bg-paper/85 backdrop-blur-md' : 'bg-transparent')}>
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5 sm:px-8">
          <Logo />
          <nav className="ml-6 hidden items-center gap-1 md:flex">
            {NAV_LINKS.map(([h, l]) => (
              <a key={h} href={h} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-white hover:text-ink">
                {l}
              </a>
            ))}
          </nav>
          <div className="ml-auto hidden items-center gap-2 md:flex">
            {me ? (
              <Link to={homeFor(me.role)} className="inline-flex h-10 items-center gap-2 rounded-xl bg-ink px-4 text-sm font-semibold text-white hover:bg-teal-900">
                <LayoutDashboard className="size-4" /> Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" state={{ role: 'student' }} className="inline-flex h-10 items-center rounded-xl px-4 text-sm font-semibold text-slate-700 hover:bg-white">
                  Student login
                </Link>
                <Link to="/login" state={{ role: 'teacher' }} className="inline-flex h-10 items-center gap-2 rounded-xl bg-ink px-4 text-sm font-semibold text-white hover:bg-teal-900">
                  Teacher login <ArrowRight className="size-4" />
                </Link>
              </>
            )}
          </div>
          <button className="ml-auto rounded-lg p-2 md:hidden" onClick={() => setMenu((m) => !m)} aria-label="Menu" aria-expanded={menu}>
            {menu ? <X className="size-6" /> : <Menu className="size-6" />}
          </button>
        </div>
        {menu && (
          <div className="border-t border-paper-200 bg-paper px-5 pb-5 md:hidden">
            {NAV_LINKS.map(([h, l]) => (
              <a key={h} href={h} onClick={() => setMenu(false)} className="block border-b border-paper-200 py-3 font-medium">
                {l}
              </a>
            ))}
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Link to="/login" state={{ role: 'student' }} className="rounded-xl bg-white py-3 text-center text-sm font-semibold ring-1 ring-slate-200">
                Student login
              </Link>
              <Link to={me ? homeFor(me.role) : '/login'} state={{ role: 'teacher' }} className="rounded-xl bg-ink py-3 text-center text-sm font-semibold text-white">
                {me ? 'Dashboard' : 'Teacher login'}
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* --------------------------------------------------------- hero */}
      <section className="relative overflow-hidden px-5 pt-10 pb-20 sm:px-8 lg:pt-16 lg:pb-28">
        <div className="bg-dots pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top_left,black_20%,transparent_65%)]" />
        <div aria-hidden="true" className="pointer-events-none absolute -top-10 right-[-4rem] select-none font-bn-display text-[22rem] leading-none text-teal-700/[0.04]">
          অ
        </div>
        <div className="relative mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[1.05fr_1fr]">
          <div className="animate-fade-up">
            <Eyebrow>
              <Mic className="size-3.5" /> AI reading diagnostician · Grades 1–5
            </Eyebrow>
            <h1 className="mt-6 font-display text-[2.6rem] leading-[1.05] font-semibold tracking-tight text-balance sm:text-6xl">
              Hear every child read. <span className="relative whitespace-nowrap text-teal-700">Know what to teach<svg aria-hidden="true" viewBox="0 0 300 12" className="absolute -bottom-2 left-0 h-3 w-full text-marigold" preserveAspectRatio="none"><path d="M2 9 C 80 2, 200 2, 298 7" stroke="currentColor" strokeWidth="4" fill="none" strokeLinecap="round" /></svg></span> next.
            </h1>
            <p className="mt-5 font-bn-display text-2xl text-teal-800">প্রতিটি শিশুর পড়া শুনুন, জানুন এরপর কী শেখাবেন।</p>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
              A child reads a short Bangla passage aloud. PoraBondhu marks every word, traces mistakes to the exact
              <span className="font-bn"> যুক্তাক্ষর</span> or <span className="font-bn">কার</span> behind them, and gives the teacher a clear next lesson. No more guessing in a class of sixty.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              {primaryCta}
              <a href="#how" className="inline-flex h-13 items-center gap-2 rounded-2xl bg-white px-6 font-semibold text-ink ring-1 ring-slate-200 hover:ring-teal-300">
                See how it works
              </a>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
              {[
                [HardDrive, 'Runs on the school computer'],
                [Hand, 'Teacher has the final say'],
                [BookOpenCheck, 'Bangla & English passages'],
              ].map(([I, t]) => {
                const Icon = I as typeof Mic
                return (
                  <li key={t as string} className="flex items-center gap-2">
                    <Icon className="size-4 text-teal-700" /> {t as string}
                  </li>
                )
              })}
            </ul>
          </div>
          <div className="animate-fade-up [animation-delay:0.15s]">
            <ReadingBuddy size={112} mood="cheer" say="এসো, একসাথে পড়ি! তুমি পারবে!" className="mb-5 justify-center" />
            <HeroDemo />
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------- stats */}
      <section className="bg-ink px-5 py-14 text-white sm:px-8">
        <div className="mx-auto grid max-w-6xl gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['~1 in 2', 'Grade 3 students below grade level in Bangla', 'National Student Assessment 2022'],
            ['51%', 'of late-primary children can’t read and understand a simple text', 'World Bank, Learning Poverty 2024'],
            ['60', 'students for one teacher, no time to hear each one read', 'Typical primary classroom'],
            ['2 min', 'to listen, mark and diagnose one child', 'With PoraBondhu'],
          ].map(([v, l, s], k) => (
            <div key={k} className={clsx(k === 3 && 'lg:border-l lg:border-white/15 lg:pl-10')}>
              <div className={clsx('font-display text-5xl font-semibold tracking-tight', k === 3 ? 'text-marigold' : 'text-white')}>{v}</div>
              <div className="mt-3 text-[15px] leading-snug text-teal-50">{l}</div>
              <div className="mt-2 text-xs text-teal-200/60">{s}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------ problem */}
      <Section className="py-24">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <SectionTitle eyebrow="The problem" title="A score is not a diagnosis." bn="নম্বর জানায় কে পিছিয়ে, কিন্তু কেন — তা নয়।">
            A teacher may know a child reads poorly, but not why. The difficulty is usually specific: a set of conjuncts, a vowel sign, a sound. Weak readers stay quiet or memorise the text, and go unnoticed for years.
          </SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              [Users, 'Large classes', 'One teacher cannot hear 50–60 children read aloud, one by one.'],
              [EyeOff, 'Hidden weak readers', 'Children who can’t read stay silent or recite from memory.'],
              [Target, 'No “why”', 'A low mark doesn’t say which letters or signs are the problem.'],
              [ClipboardCheck, 'Slow manual tests', 'Oral reading tests need a trained adult for minutes per child.'],
            ].map(([I, t, d], k) => {
              const Icon = I as typeof Mic
              return (
                <div key={k} className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
                  <div className="grid size-10 place-items-center rounded-xl bg-flag/10 text-flag">
                    <Icon className="size-5" />
                  </div>
                  <div className="mt-4 font-semibold">{t as string}</div>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">{d as string}</p>
                </div>
              )
            })}
          </div>
        </div>
      </Section>

      {/* ------------------------------------------------- how it works */}
      <Section id="how" className="bg-white py-24">
        <SectionTitle center eyebrow="How it works" title="From one reading to the next lesson" bn="শোনা → চিহ্নিত করা → কারণ খোঁজা → শিক্ষককে জানানো">
          Four steps, about two minutes per child. Everything runs on the school's own computer.
        </SectionTitle>
        <ol className="relative mt-16 grid gap-6 md:grid-cols-4">
          <div aria-hidden="true" className="absolute top-8 right-[12%] left-[12%] hidden border-t-2 border-dashed border-teal-200 md:block" />
          {[
            [AudioLines, 'Listen', 'শোনা', 'The child reads a passage on screen. A quality check asks for a re-read if the room is too noisy.'],
            [ListChecks, 'Mark', 'চিহ্নিত', 'Each word is marked correct, misread, skipped or unsure, with speed in words-correct-per-minute.'],
            [ScanSearch, 'Diagnose', 'কারণ', 'Errors are traced to the grapheme unit: র-ফলা, ি-কার, রেফ. Repeats become weak patterns.'],
            [GraduationCap, 'Inform', 'জানানো', 'The teacher sees who needs help with what, and confirms or changes any mark in one tap.'],
          ].map(([I, t, bn, d], k) => {
            const Icon = I as typeof Mic
            return (
              <li key={k} className="relative text-center">
                <div className="relative mx-auto grid size-16 place-items-center rounded-2xl bg-teal-700 text-white shadow-lg shadow-teal-900/20">
                  <Icon className="size-7" />
                  <span className="absolute -top-2 -right-2 grid size-6 place-items-center rounded-full bg-marigold text-xs font-bold text-ink">{k + 1}</span>
                </div>
                <div className="mt-5 font-display text-xl font-semibold">{t as string}</div>
                <div className="font-bn text-sm text-teal-700">{bn as string}</div>
                <p className="mx-auto mt-2 max-w-60 text-sm leading-relaxed text-slate-600">{d as string}</p>
              </li>
            )
          })}
        </ol>
      </Section>

      {/* ------------------------------------------------------- engine */}
      <Section id="engine" className="py-24">
        <div className="mb-12 flex flex-wrap items-end justify-between gap-6">
          <SectionTitle eyebrow="Built for Bangla script" title="It reads Bangla the way a teacher does: unit by unit." bn="যুক্তাক্ষর, কার, ফলা, রেফ — আলাদা করে বোঝে।">
            Our own grapheme engine splits every word into the units children actually learn. Pick a word to see it.
          </SectionTitle>
        </div>
        <EngineExplorer />
      </Section>

      {/* ------------------------------------------- error preserving */}
      <Section className="bg-teal-950 py-24 text-white">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <Eyebrow tone="light">Error-preserving speech AI</Eyebrow>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl">Most speech AI fixes children’s mistakes. We keep them.</h2>
            <p className="mt-4 text-lg leading-relaxed text-teal-100/80">
              General speech recognisers use language context to guess the most likely word, so a misread word often comes out “correct”. PoraBondhu uses a character-level Bangla model with no language model, so the child’s real attempt survives — and when the AI isn’t sure, it says <em>unsure</em> instead of guessing.
            </p>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl bg-white/5 p-5 ring-1 ring-white/10">
              <div className="text-xs font-semibold uppercase tracking-wider text-teal-200/70">Passage says</div>
              <div className="mt-1 font-bn-display text-3xl">প্রথম</div>
              <div className="mt-3 text-xs font-semibold uppercase tracking-wider text-teal-200/70">Child says</div>
              <div className="mt-1 font-bn-display text-3xl text-marigold">পথম</div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-white/5 p-5 ring-1 ring-white/10">
                <div className="text-sm text-teal-100/70">Typical speech-to-text</div>
                <div className="mt-2 font-bn text-2xl">প্রথম</div>
                <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-xs text-teal-50">
                  <EyeOff className="size-3.5" /> Mistake hidden
                </div>
              </div>
              <div className="rounded-2xl bg-white p-5 text-ink">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <LogoMark className="size-5" /> PoraBondhu
                </div>
                <div className="mt-2 font-bn text-2xl">
                  <span className="rounded bg-rose-50 px-1 text-rose-800 underline decoration-rose-500 decoration-2 underline-offset-4">প</span>থম
                </div>
                <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 font-bn text-xs font-medium text-rose-800">র-ফলা dropped</div>
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------- teachers/students */}
      <Section id="teachers" className="py-24">
        <SectionTitle center eyebrow="Made for the classroom" title="One tool, two simple views" bn="শিক্ষকের জন্য ড্যাশবোর্ড, শিক্ষার্থীর জন্য সহজ পড়ার পাতা" />
        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <div className="flex flex-col rounded-3xl bg-white p-8 ring-1 ring-slate-200">
            <div className="flex items-center gap-3">
              <div className="grid size-12 place-items-center rounded-2xl bg-teal-700 text-white">
                <School className="size-6" />
              </div>
              <div>
                <div className="font-display text-2xl font-semibold">For teachers</div>
                <div className="font-bn text-sm text-slate-500">শিক্ষক</div>
              </div>
            </div>
            <ul className="mt-6 flex-1 space-y-3">
              {[
                'Class map of weak patterns: see which conjuncts the whole class struggles with',
                'Each child’s speed, accuracy, mark out of 10 and progress over time',
                'Marked passage with audio playback; change any mark in one tap',
                'Ready-made graded passages, or add your own',
                'Suggested next lessons per child, grouped by pattern',
              ].map((t) => (
                <li key={t} className="flex gap-3 text-slate-700">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-teal-600" /> {t}
                </li>
              ))}
            </ul>
            <Link to={me?.role === 'teacher' ? homeFor('teacher') : '/login'} state={{ role: 'teacher' }} className="mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-teal-700 font-semibold text-white hover:bg-teal-800">
              {me?.role === 'teacher' ? 'Open dashboard' : 'Teacher login'} <ArrowRight className="size-4" />
            </Link>
          </div>

          <div className="relative flex flex-col overflow-hidden rounded-3xl bg-marigold-50 p-8 ring-1 ring-amber-200">
            <div aria-hidden="true" className="absolute -right-6 -bottom-16 font-bn-display text-[14rem] leading-none text-amber-500/10">ক</div>
            <div className="relative flex items-center gap-3">
              <div className="grid size-12 place-items-center rounded-2xl bg-marigold text-ink">
                <GraduationCap className="size-6" />
              </div>
              <div>
                <div className="font-display text-2xl font-semibold">For students</div>
                <div className="font-bn text-sm text-slate-500">শিক্ষার্থী</div>
              </div>
            </div>
            <ul className="relative mt-6 flex-1 space-y-3">
              {[
                'Big, clear Bangla text and one large record button',
                'Listen first: hear the passage read aloud, word by word, at normal or slow speed',
                'Play back their own reading and compare it with the correct one',
                'A friendly mark out of 10 after every reading',
                'Tap a hard word to hear it said correctly, then hear themselves',
                'Practise English passages too',
                'Login created by the teacher, no email or phone needed',
              ].map((t) => (
                <li key={t} className="flex gap-3 text-slate-700">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-amber-600" /> {t}
                </li>
              ))}
            </ul>
            <Link to={me?.role === 'student' ? homeFor('student') : '/login'} state={{ role: 'student' }} className="relative mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-ink font-semibold text-white hover:bg-teal-900">
              {me?.role === 'student' ? 'Go to my reading' : 'Student login'} <ArrowRight className="size-4" />
            </Link>
          </div>
        </div>
      </Section>

      {/* ------------------------------------------------------ trust */}
      <Section id="trust" className="bg-white py-24">
        <SectionTitle center eyebrow="Our principles" title="Careful AI for children" bn="শিশুদের জন্য দায়িত্বশীল AI" />
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[
            [Hand, 'Teacher decides', 'Every mark is a suggestion. The teacher confirms or changes it, and the final call is theirs.'],
            [ShieldCheck, '“Unsure” is never an error', 'When the AI isn’t confident, the word is shown as unsure and never counted against the child.'],
            [HardDrive, 'Private by design', 'Children’s voices and results stay on the school computer. Only passage text is sent out, to make the model reading.'],
            [Target, 'Patterns, not slips', 'A unit becomes a weak pattern only after repeated errors, never from a single slip.'],
          ].map(([I, t, d], k) => {
            const Icon = I as typeof Mic
            return (
              <div key={k} className="rounded-2xl bg-paper p-6 ring-1 ring-paper-200">
                <Icon className="size-6 text-teal-700" />
                <div className="mt-4 font-semibold">{t as string}</div>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{d as string}</p>
              </div>
            )
          })}
        </div>
      </Section>

      {/* -------------------------------------------------------- CTA */}
      <Section className="py-24">
        <div className="relative overflow-hidden rounded-[2rem] bg-teal-700 px-8 py-14 text-center text-white sm:px-14">
          <div className="bg-dots pointer-events-none absolute inset-0 opacity-30 [filter:invert(1)]" />
          <div aria-hidden="true" className="absolute top-1/2 -left-10 size-56 -translate-y-1/2 rounded-full bg-flag/90" />
          <div className="relative">
            <h2 className="font-display text-3xl font-semibold tracking-tight text-balance sm:text-5xl">Every child heard. Every teacher knows what’s next.</h2>
            <p className="mt-4 font-bn-display text-xl text-teal-100">আজই আপনার ক্লাসের পড়া যাচাই শুরু করুন।</p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link to={me ? homeFor(me.role) : '/login'} state={{ role: 'teacher' }} className="inline-flex h-13 items-center gap-2 rounded-2xl bg-white px-6 font-semibold text-teal-800 hover:bg-teal-50">
                {me ? 'Open dashboard' : 'Get started'} <ArrowRight className="size-4" />
              </Link>
              {!me && (
                <Link to="/login" state={{ role: 'student' }} className="inline-flex h-13 items-center gap-2 rounded-2xl bg-white/10 px-6 font-semibold text-white ring-1 ring-white/30 hover:bg-white/20">
                  I’m a student
                </Link>
              )}
            </div>
          </div>
        </div>
      </Section>

      <footer className="border-t border-paper-200 px-5 py-10 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <Logo />
          <p className="max-w-md text-sm text-slate-500">A teacher’s aid for Bangla reading, not an official test. Built by Team TwinLogic for the CoU AI Hackathon 2026.</p>
        </div>
      </footer>
    </div>
  )
}
