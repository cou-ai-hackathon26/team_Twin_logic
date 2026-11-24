import clsx from 'clsx'
import { DemoNotice } from '@/components/DemoNotice'
import { ArrowLeft, Mic, RotateCcw, Square, Star } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useReading } from '@/api/hooks'
import type { Language, Reading } from '@/api/types'
import { ListenAlong } from '@/components/audio'
import { MarkBadge } from '@/components/domain'
import { Button, ErrorBox, Spinner } from '@/components/ui/primitives'
import { langFont } from '@/lib/format'
import { startRecording, type RecorderHandle } from '@/lib/recorder'
import { ProcessingProgress } from './ProcessingProgress'

type Phase = 'ready' | 'recording' | 'uploading' | 'waiting'
const MAX_SECONDS = 180

const PROMPTS = {
  bn: {
    wait: 'একটু অপেক্ষা করো…',
    again: 'চলো আরেকবার পড়ি!',
    retry: 'আবার পড়ো',
    great: 'খুব সুন্দর পড়েছ!',
    mark: 'তোমার নম্বর',
    checking: 'AI তোমার ফলাফল এখনই দেখাবে, আর শিক্ষকও যাচাই করবেন।',
    start: 'বোতাম চাপো, তারপর জোরে জোরে পড়ো',
    stop: 'পড়া শেষ হলে থামাও',
  },
  en: {
    wait: 'Please wait…',
    again: 'Let us read it once more!',
    retry: 'Read again',
    great: 'Well done!',
    mark: 'Your mark',
    checking: 'The AI shows your result now, and your teacher will also check it.',
    start: 'Press the button, then read aloud',
    stop: 'Press stop when you finish',
  },
} as const

function LevelMeter({ rec }: { rec: RecorderHandle }) {
  const [lvl, setLvl] = useState(0)
  useEffect(() => {
    let raf = 0
    const tick = () => {
      setLvl(rec.level())
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [rec])
  return (
    <div className="flex h-8 items-end gap-1" aria-hidden>
      {Array.from({ length: 12 }).map((_, i) => (
        <div
          key={i}
          className={clsx('w-2 rounded-sm transition-all', lvl * 12 > i ? (i > 9 ? 'bg-amber-400' : 'bg-teal-500') : 'bg-slate-200')}
          style={{ height: `${30 + i * 6}%` }}
        />
      ))}
    </div>
  )
}

function WaitingForResult({
  readingId,
  language,
  asStudent,
  onRetry,
  doneActions,
}: {
  readingId: number
  language: Language
  asStudent: boolean
  onRetry: () => void
  doneActions: ReactNode
}) {
  const { data } = useReading(readingId, asStudent)
  const t = PROMPTS[language]
  if (!data || data.status === 'queued' || data.status === 'processing')
    return <ProcessingProgress progress={data?.progress} language={language} child={asStudent} />
  if (data.status === 'rejected')
    return (
      <div className="flex max-w-xl flex-col items-center gap-4 text-center">
        <p className={clsx('text-2xl text-slate-800', langFont(language))}>{t.again}</p>
        <p className="font-bn text-lg text-slate-600">{data.quality?.message_bn}</p>
        <p className="text-sm text-slate-500">{data.quality?.message_en}</p>
        <Button size="xl" onClick={onRetry}>
          <RotateCcw className="size-6" /> {t.retry}
        </Button>
      </div>
    )
  if (data.status === 'failed')
    return (
      <div className="flex max-w-xl flex-col items-center gap-4 text-center">
        {/* this screen faces the child: a calm message, never the raw technical error (the teacher sees it on the review page) */}
        <p className={clsx('text-2xl text-slate-800', langFont(language))}>{t.again}</p>
        <p className="font-bn text-slate-600">কিছু একটা ঠিকমতো কাজ করেনি। আরেকবার পড়ো, অথবা শিক্ষককে বলো।</p>
        <p className="text-sm text-slate-500">Something went wrong while checking. Please read again, or ask your teacher.</p>
        <Button size="xl" onClick={onRetry}>
          <RotateCcw className="size-6" /> {t.retry}
        </Button>
      </div>
    )
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="flex gap-2 text-amber-400">
        {[0, 1, 2].map((i) => (
          <Star key={i} className="size-14 fill-current" style={{ animation: `bounce 1s ${i * 0.15}s 2` }} />
        ))}
      </div>
      <p className={clsx('text-4xl font-semibold text-teal-800', langFont(language))}>{t.great}</p>
      {data.reviewed && data.score !== null ? (
        <div className="flex flex-col items-center gap-2">
          <span className={clsx('text-lg text-slate-600', langFont(language))}>{t.mark}</span>
          <MarkBadge score={data.score} size="lg" />
        </div>
      ) : (
        // the AI's marks are suggestions until the teacher checks them, so the child sees no mark yet
        <p className={clsx('max-w-md text-lg text-slate-600', langFont(language))}>{t.checking}</p>
      )}
      <div className="flex flex-wrap justify-center gap-3">{doneActions}</div>
    </div>
  )
}

export interface SessionPassage {
  title: string
  text: string
  language: Language
}

/** Full-screen reading test: show the passage, record, upload, wait for the mark. */
export function ReadingSession({
  passage,
  who,
  backTo,
  upload,
  asStudent,
  doneActions,
}: {
  passage: SessionPassage
  who: ReactNode
  backTo: string
  upload: (wav: Blob) => Promise<Reading>
  asStudent: boolean
  doneActions: (readingId: number) => ReactNode
}) {
  const [phase, setPhase] = useState<Phase>('ready')
  const [rec, setRec] = useState<RecorderHandle | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [err, setErr] = useState<unknown>(null)
  const [readingId, setReadingId] = useState<number | null>(null)
  const startedAt = useRef(0)
  const uploadRef = useRef(upload)
  useEffect(() => {
    uploadRef.current = upload
  }, [upload])
  const lang = passage.language ?? 'bn'
  const t = PROMPTS[lang]

  const stop = useCallback(async () => {
    if (!rec) return
    setPhase('uploading')
    const wav = await rec.stop()
    setRec(null)
    try {
      const r = await uploadRef.current(wav)
      setReadingId(r.id)
      setPhase('waiting')
    } catch (e) {
      setErr(e)
      setPhase('ready')
    }
  }, [rec])

  useEffect(() => {
    if (phase !== 'recording') return
    const iv = setInterval(() => {
      const s = (performance.now() - startedAt.current) / 1000
      setElapsed(s)
      if (s >= MAX_SECONDS) void stop()
    }, 200)
    return () => clearInterval(iv)
  }, [phase, stop])

  useEffect(() => () => rec?.cancel(), [rec])

  const start = async () => {
    setErr(null)
    try {
      const r = await startRecording()
      setRec(r)
      startedAt.current = performance.now()
      setElapsed(0)
      setPhase('recording')
    } catch (e) {
      setErr(e instanceof Error ? new Error(`Microphone: ${e.message}`) : e)
    }
  }

  const retry = () => {
    setReadingId(null)
    setPhase('ready')
  }

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-teal-50 to-paper">
      <header className="flex items-center justify-between px-6 py-3">
        <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" /> Back
        </Link>
        <div className="text-sm text-slate-500">{who}</div>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col items-center gap-5 px-4 pb-12 sm:px-6">
        {phase === 'waiting' && readingId ? (
          <div className="flex flex-1 items-center justify-center py-10">
            <WaitingForResult readingId={readingId} language={lang} asStudent={asStudent} onRetry={retry} doneActions={doneActions(readingId)} />
          </div>
        ) : (
          <>
            {/* record controls stay at the top (and stick while scrolling) so the child never has to look for them */}
            <div
              className={clsx(
                'sticky top-3 z-20 flex w-full items-center gap-4 rounded-3xl px-4 py-3 shadow-lg ring-1 backdrop-blur sm:gap-5 sm:px-5',
                phase === 'recording' ? 'bg-rose-50/95 ring-rose-200' : 'bg-white/95 ring-slate-200',
              )}
            >
              {phase === 'ready' && (
                <>
                  <button
                    onClick={start}
                    className="grid size-16 shrink-0 place-items-center rounded-full bg-teal-600 text-white shadow-lg ring-4 ring-teal-100 transition hover:scale-105 hover:bg-teal-700 focus:outline-none focus-visible:ring-teal-300 sm:size-20"
                    aria-label="Start recording"
                  >
                    <Mic className="size-8 sm:size-9" />
                  </button>
                  <div className="min-w-0">
                    <p className={clsx('text-lg font-semibold text-ink sm:text-xl', langFont(lang))}>{t.start}</p>
                    <p className="text-xs text-slate-500">Listen first if you like, then record. Use a headset microphone in a noisy room.</p>
                  </div>
                </>
              )}
              {phase === 'recording' && rec && (
                <>
                  <button
                    onClick={() => void stop()}
                    className="grid size-16 shrink-0 place-items-center rounded-full bg-rose-600 text-white shadow-lg ring-4 ring-rose-100 transition hover:bg-rose-700 sm:size-20"
                    aria-label="Stop recording"
                  >
                    <Square className="size-7 fill-current" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className={clsx('flex items-center gap-2 text-lg font-semibold text-rose-900 sm:text-xl', langFont(lang))}>
                      <span className="size-2.5 animate-pulse rounded-full bg-rose-600" /> {t.stop}
                    </p>
                    <p className="text-xs text-rose-800/70">Recording… read the passage below aloud</p>
                  </div>
                  <div className="ml-auto hidden sm:block">
                    <LevelMeter rec={rec} />
                  </div>
                  <div className="font-mono text-2xl tabular-nums text-rose-900">
                    {Math.floor(elapsed / 60)}:{String(Math.floor(elapsed % 60)).padStart(2, '0')}
                  </div>
                </>
              )}
              {phase === 'uploading' && (
                <div className="flex items-center gap-3 py-4 text-slate-600">
                  <Spinner /> Saving…
                </div>
              )}
            </div>
            {phase === 'ready' && <DemoNotice className="w-full" />}
            {!window.isSecureContext && (
              <div className="w-full rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
                Browsers allow the microphone only on secure (https://) pages. Open the https:// link of this demo to record, or go back and use <b>Upload a recording</b>.
              </div>
            )}
            <ErrorBox error={err} className="w-full" />

            <div className="w-full rounded-3xl bg-white p-6 shadow-lg ring-1 ring-slate-100 sm:p-10">
              <h1 className={clsx('mb-5 text-center text-3xl font-semibold text-teal-800', langFont(lang))}>{passage.title}</h1>
              <ListenAlong
                text={passage.text}
                language={lang}
                disabled={phase !== 'ready'}
                textClassName={clsx(
                  'text-slate-900',
                  lang === 'en' ? 'font-sans text-2xl leading-[2] sm:text-3xl sm:leading-[2]' : 'font-bn text-3xl leading-[2.2] sm:text-4xl sm:leading-[2.2]',
                )}
              />
            </div>
          </>
        )}
      </main>
    </div>
  )
}

