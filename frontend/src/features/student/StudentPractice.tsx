import clsx from 'clsx'
import { Check, Dumbbell, Ear, Loader2, PartyPopper, Volume2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMyPractice } from '@/api/hooks'
import type { PracticeWord } from '@/api/types'
import { useMyVoice, useSayWord } from '@/components/audio'
import { Button, Card, EmptyState, ErrorBox, PageLoader } from '@/components/ui/primitives'
import { dateShort, langFont } from '@/lib/format'
import { useLearned } from './practiceStore'
import { WordCheck } from './WordCheck'

function WordCard({ w, learned, onToggle }: { w: PracticeWord; learned: boolean; onToggle: () => void }) {
  const { say, busy } = useSayWord(w.language)
  const { playClip } = useMyVoice(`/api/my/readings/${w.reading_id}/audio`)
  return (
    <div
      className={clsx(
        'flex flex-col rounded-3xl border bg-white p-5 transition-all',
        learned ? 'border-teal-200 bg-teal-50/40' : 'border-slate-200 hover:-translate-y-0.5 hover:shadow-md',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {w.patterns.slice(0, 2).map((p) => (
            <span key={p.key} className="rounded-md bg-rose-50 px-1.5 py-0.5 font-bn text-xs text-rose-800 ring-1 ring-rose-200">
              {p.bn}
            </span>
          ))}
          {w.count > 1 && <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600">×{w.count}</span>}
        </div>
        {learned && <Check className="size-5 text-teal-600" />}
      </div>
      <button
        type="button"
        onClick={() => void say(w.word)}
        className={clsx('my-4 text-center text-4xl font-semibold text-ink transition-colors hover:text-teal-700 sm:text-5xl', langFont(w.language))}
        title="Hear it"
      >
        {w.word}
      </button>
      <div className="mb-4 text-center text-sm text-slate-500">
        {w.status === 'skipped' ? (
          'You skipped this word'
        ) : (
          <>
            You said <span className={clsx('font-semibold text-rose-700', langFont(w.language))}>{w.heard || '—'}</span>
          </>
        )}
        <div className={clsx('mt-0.5 truncate text-xs text-slate-400', langFont(w.language))}>
          {w.passage_title} · {dateShort(w.date)}
        </div>
      </div>
      <div className="mt-auto grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => void say(w.word)}
          className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Volume2 className="size-4" />} Correct
        </button>
        <button
          type="button"
          disabled={!w.clip}
          onClick={() => w.clip && void playClip(w.clip.start, w.clip.end)}
          title={w.clip ? 'Hear how you said it' : 'Your recording for this word is not stored'}
          className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl bg-white text-sm font-semibold text-slate-700 ring-1 ring-slate-200 hover:ring-teal-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Ear className="size-4" /> Me
        </button>
      </div>
      <button
        type="button"
        onClick={onToggle}
        className={clsx(
          'mt-2 inline-flex h-10 items-center justify-center gap-1.5 rounded-xl text-sm font-semibold transition-colors',
          learned ? 'text-teal-700 hover:bg-teal-50' : 'bg-marigold-50 text-amber-900 ring-1 ring-amber-200 hover:bg-amber-100',
        )}
      >
        <Check className="size-4" /> {learned ? 'Learned · undo' : 'I can read it now'}
      </button>
      {w.language === 'bn' && !learned && <WordCheck word={w.word} onRight={onToggle} />}
    </div>
  )
}

/** Personal word practice built from the student's own mistakes. */
export function StudentPractice() {
  const { data, isLoading, error } = useMyPractice()
  const { learned, toggle } = useLearned()
  const [tab, setTab] = useState<'todo' | 'done'>('todo')
  const words = useMemo(() => data ?? [], [data])
  const todo = words.filter((w) => !learned.has(w.expected))
  const done = words.filter((w) => learned.has(w.expected))
  const shown = tab === 'todo' ? todo : done
  const pct = words.length ? done.length / words.length : 0

  if (isLoading) return <PageLoader />
  if (error) return <ErrorBox error={error} />

  return (
    <>
      <div className="relative mb-8 overflow-hidden rounded-3xl bg-teal-800 p-6 text-white sm:p-8">
        <div aria-hidden="true" className="pointer-events-none absolute -right-4 -bottom-16 select-none font-bn-display text-[12rem] leading-none text-white/[0.06]">
          ক্ষ
        </div>
        <div className="relative flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="font-bn text-teal-200">শব্দ অনুশীলন</div>
            <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Word practice</h1>
            <p className="mt-2 max-w-md text-teal-100/80">These are words from your own readings. Hear each one, hear yourself, say it aloud, then tick it.</p>
          </div>
          <div className="w-full max-w-60">
            <div className="mb-1.5 flex justify-between text-sm">
              <span>Learned</span>
              <span className="font-semibold tabular-nums">
                {done.length}/{words.length}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-marigold transition-all duration-500" style={{ width: `${pct * 100}%` }} />
            </div>
          </div>
        </div>
      </div>

      {!words.length ? (
        <Card>
          <EmptyState icon={<Dumbbell className="size-12" />} title="No words to practise yet">
            Take a reading test. Words you find hard will appear here.
            <div className="mt-4">
              <Link to="/me">
                <Button>Go to my tests</Button>
              </Link>
            </div>
          </EmptyState>
        </Card>
      ) : (
        <>
          <div className="mb-5 inline-flex rounded-2xl bg-paper-200/70 p-1 text-sm" role="tablist">
            {(
              [
                ['todo', `To practise (${todo.length})`],
                ['done', `Learned (${done.length})`],
              ] as const
            ).map(([k, l]) => (
              <button
                key={k}
                role="tab"
                aria-selected={tab === k}
                onClick={() => setTab(k)}
                className={clsx('rounded-xl px-4 py-2 font-semibold', tab === k ? 'bg-white text-teal-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-500')}
              >
                {l}
              </button>
            ))}
          </div>
          {!shown.length ? (
            <Card>
              <EmptyState icon={<PartyPopper className="size-12 text-marigold" />} title={tab === 'todo' ? 'You have learned every word. Brilliant!' : 'Tick a word when you can read it.'} />
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {shown.map((w) => (
                <WordCard key={w.expected} w={w} learned={learned.has(w.expected)} onToggle={() => toggle(w.expected)} />
              ))}
            </div>
          )}
        </>
      )}
    </>
  )
}
