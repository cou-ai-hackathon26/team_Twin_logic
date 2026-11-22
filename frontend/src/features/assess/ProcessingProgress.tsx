import clsx from 'clsx'
import { AudioLines, BookOpenCheck, Check, Cpu, Hourglass, Puzzle, ShieldCheck } from 'lucide-react'
import { useEffect, useRef, useState, type ComponentType } from 'react'
import type { Language, ProgressStage, ReadingProgress } from '@/api/types'
import { langFont } from '@/lib/format'

/** Pipeline stages, in order, with the share of the bar each one covers. */
const STEPS: {
  key: ProgressStage
  from: number
  to: number
  icon: ComponentType<{ className?: string }>
  bn: string
  en: string
  tech: string
}[] = [
  { key: 'queued', from: 0, to: 3, icon: Hourglass, bn: 'লাইনে আছে', en: 'In the queue', tech: 'waiting for the CPU worker' },
  { key: 'loading', from: 3, to: 12, icon: Cpu, bn: 'মডেল চালু হচ্ছে', en: 'Starting the speech model', tech: 'loading wav2vec2 (ONNX int8)' },
  { key: 'quality', from: 12, to: 16, icon: ShieldCheck, bn: 'শব্দ পরীক্ষা', en: 'Checking the sound', tech: 'loudness, clipping, noise' },
  { key: 'listening', from: 16, to: 82, icon: AudioLines, bn: 'মন দিয়ে শুনছে', en: 'Listening to every sound', tech: 'character-level CTC, no language model' },
  { key: 'aligning', from: 82, to: 93, icon: BookOpenCheck, bn: 'বইয়ের সাথে মেলাচ্ছে', en: 'Matching with the passage', tech: 'forced alignment, expected-text score' },
  { key: 'diagnosing', from: 93, to: 99, icon: Puzzle, bn: 'অক্ষর খুঁজে দেখছে', en: 'Finding letter patterns', tech: 'যুক্তাক্ষর, কার, ফলা diagnosis' },
]

/** Smooth percentage: the real stage from the server, the position inside it estimated from elapsed time. */
function usePercent(p: ReadingProgress | undefined) {
  const [pct, setPct] = useState(0)
  const anchor = useRef({ at: performance.now(), p })
  useEffect(() => {
    anchor.current = { at: performance.now(), p }
  }, [p])
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const { at, p: cur } = anchor.current
      const stage = cur?.stage ?? 'queued'
      const step = STEPS.find((s) => s.key === stage) ?? STEPS[0]
      const since = (cur?.stage_elapsed_sec ?? 0) + (performance.now() - at) / 1000
      // expected length of this stage: listening is most of the work
      const total = Math.max(cur?.estimated_sec ?? 10, 2)
      const share = stage === 'listening' ? 0.8 : stage === 'loading' ? 2 : 0.08
      const frac = 1 - Math.exp(-since / Math.max(total * share, 0.5)) // eases, never overshoots the stage
      const target = step.from + (step.to - step.from) * frac
      setPct((old) => Math.max(old, Math.min(99, target)))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])
  return pct
}

export function ProcessingProgress({ progress, language, child }: { progress?: ReadingProgress; language: Language; child: boolean }) {
  const pct = usePercent(progress)
  const stage = progress?.stage ?? 'queued'
  const idx = Math.max(0, STEPS.findIndex((s) => s.key === stage))
  const remaining = progress ? Math.max(0, Math.round(progress.estimated_sec - progress.elapsed_sec)) : null
  const visible = STEPS.filter((s) => s.key !== 'loading' || stage === 'loading')
  const current = STEPS[idx]
  const showBn = child ? language === 'bn' : false // teachers read the English label, Bangla shown beside it

  return (
    <div className="w-full max-w-xl" role="status" aria-live="polite">
      {/* reading buddy: an open book whose pages fill as the bar grows */}
      <div className="mx-auto mb-6 grid size-28 place-items-center rounded-full bg-white shadow-xl ring-8 ring-teal-100">
        <div className="relative">
          <current.icon className="size-12 text-teal-700" />
          <span className="absolute -right-3 -bottom-2 rounded-full bg-marigold px-2 py-0.5 text-xs font-bold text-ink shadow">
            {Math.round(pct)}%
          </span>
        </div>
      </div>

      <p className={clsx('text-center text-2xl font-semibold text-ink', langFont(language))}>
        {showBn ? current.bn : current.en}
        <span className="inline-flex w-8 justify-start">
          <span className="animate-pulse">…</span>
        </span>
      </p>
      {!child && (
        <p className="mt-1 text-center text-xs text-slate-500">
          <span className="font-bn">{current.bn}</span> · {current.tech}
        </p>
      )}

      <div className="mt-5 h-4 w-full overflow-hidden rounded-full bg-white shadow-inner ring-1 ring-slate-200">
        <div
          className="relative h-full rounded-full bg-gradient-to-r from-teal-500 via-teal-600 to-teal-700 transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        >
          <div className="absolute inset-0 animate-pulse rounded-full bg-white/20" />
        </div>
      </div>
      <div className="mt-2 flex justify-between text-xs tabular-nums text-slate-500">
        <span>{Math.round(pct)}% done</span>
        <span>{remaining !== null && remaining > 0 ? `about ${remaining} s left` : progress && progress.elapsed_sec > 0 ? 'almost there' : 'estimating time…'}</span>
      </div>

      <ol className="mt-6 grid gap-2">
        {visible.map((s) => {
          const i = STEPS.indexOf(s)
          const state = i < idx ? 'done' : i === idx ? 'now' : 'next'
          return (
            <li
              key={s.key}
              className={clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors',
                state === 'now' && 'bg-white shadow-sm ring-1 ring-teal-200',
                state === 'next' && 'opacity-50',
              )}
            >
              <span
                className={clsx(
                  'grid size-7 shrink-0 place-items-center rounded-full',
                  state === 'done' ? 'bg-teal-600 text-white' : state === 'now' ? 'bg-teal-100 text-teal-800' : 'bg-slate-100 text-slate-400',
                )}
              >
                {state === 'done' ? <Check className="size-4" /> : <s.icon className={clsx('size-4', state === 'now' && 'animate-pulse')} />}
              </span>
              <span className={clsx('font-medium text-slate-800', showBn && langFont(language))}>{showBn ? s.bn : s.en}</span>
              {!child && <span className="ml-auto hidden text-xs text-slate-400 sm:inline">{s.tech}</span>}
            </li>
          )
        })}
      </ol>
      <p className="mt-4 text-center text-xs text-slate-400">Runs on this server's CPU. No audio is sent to any outside AI service.</p>
    </div>
  )
}
