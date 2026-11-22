import clsx from 'clsx'
import { Loader2, Mic, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useWordCheck } from '@/api/practice'
import type { WordCheckResult } from '@/api/types'
import { startRecording, type RecorderHandle } from '@/lib/recorder'

const MAX_SEC = 4

/** Say one word; the speech model checks it straight away (Bangla only). */
export function WordCheck({ word, onRight }: { word: string; onRight?: () => void }) {
  const check = useWordCheck()
  const [rec, setRec] = useState<RecorderHandle | null>(null)
  const [res, setRes] = useState<WordCheckResult | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => {
    window.clearTimeout(timer.current)
    rec?.cancel()
  }, [rec])

  const stop = async (h: RecorderHandle) => {
    window.clearTimeout(timer.current)
    setRec(null)
    const blob = await h.stop()
    check.mutate(
      { word, audio: blob },
      {
        onSuccess: (r) => {
          setRes(r)
          if (r.result === 'right') onRight?.()
        },
        onError: (e) => setErr(e instanceof Error ? e.message : 'Could not check'),
      },
    )
  }

  const start = async () => {
    setErr(null)
    setRes(null)
    try {
      const h = await startRecording()
      setRec(h)
      timer.current = window.setTimeout(() => void stop(h), MAX_SEC * 1000)
    } catch (e) {
      setErr(window.isSecureContext ? (e instanceof Error ? e.message : 'Microphone not available') : 'Recording needs the https:// link')
    }
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => (rec ? void stop(rec) : void start())}
        disabled={check.isPending}
        className={clsx(
          'inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-xl text-sm font-semibold transition-colors',
          rec ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-white text-teal-800 ring-1 ring-teal-300 hover:bg-teal-50',
        )}
      >
        {check.isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" /> Checking…
          </>
        ) : rec ? (
          <>
            <Square className="size-3.5 fill-current" /> Stop
          </>
        ) : (
          <>
            <Mic className="size-4" /> <span className="font-bn">আমি বলি</span> · Say it
          </>
        )}
      </button>
      {res && (
        <p
          className={clsx(
            'mt-2 rounded-lg px-3 py-2 text-center text-sm',
            res.result === 'right' ? 'bg-teal-50 text-teal-800' : res.result === 'practise' ? 'bg-amber-50 text-amber-900' : 'bg-slate-50 text-slate-700',
          )}
        >
          <span className="font-bn font-semibold">{res.message_bn}</span>
          <span className="block text-xs opacity-80">{res.message_en}</span>
          <span className="mt-1 block text-[11px] opacity-60">
            <span className="font-bn">শুধু অনুশীলনের ইঙ্গিত</span> · practice hint only, not a mark
          </span>
        </p>
      )}
      {err && <p className="mt-2 text-center text-xs text-rose-700">{err}</p>}
    </div>
  )
}
