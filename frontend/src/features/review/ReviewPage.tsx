import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, ListChecks, Mic, RefreshCw, ShieldCheck, Trash2, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { audioUrl } from '@/api/client'
import { useAcceptAccent, useAddTrickyWord, useDeleteReading, useFinalize, useReading, useReprocess, useReviewQueue, useSetMark } from '@/api/hooks'
import { useSayWord } from '@/components/audio'
import type { WordMark, WordStatus } from '@/api/types'
import { LanguageBadge, MarkBadge, ReadingStatusBadge } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Modal, PageHeader, PageLoader, Stat } from '@/components/ui/primitives'
import { ProcessingProgress } from '@/features/assess/ProcessingProgress'
import { accTone, dateTime, langFont, num, pct, secs, wcpmTone } from '@/lib/format'
import { ComparisonPanel } from './ComparisonPanel'
import { Legend, MarkedPassage } from './MarkedPassage'
import { WordInspector } from './WordInspector'

const KEY_STATUS: Record<string, WordStatus> = { '1': 'correct', '2': 'misread', '3': 'skipped', '4': 'unsure' }
const RATES = [1, 0.75, 0.5]
const GUARD_FLAGS = ['accent', 'noisy', 'odd_word']
/** Words worth a listen: the AI flagged them, or a trust guard changed its decision. */
const needsCheck = (m: WordMark) =>
  m.status === 'misread' || m.status === 'skipped' || m.status === 'unsure' || m.flags.some((f) => GUARD_FLAGS.includes(f))

export function ReviewPage() {
  const id = Number(useParams().id)
  const { data: r, isLoading, error } = useReading(id)
  const setMark = useSetMark(id)
  const finalize = useFinalize(id)
  const queue = useReviewQueue()
  const nextInQueue = queue.data?.find((q) => q.id !== id)
  const reprocess = useReprocess(id)
  const del = useDeleteReading()
  const nav = useNavigate()
  const [selected, setSelected] = useState<number | null>(null)
  const [keepAudio, setKeepAudio] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  const stopAt = useRef<number | null>(null)
  const onStop = useRef<(() => void) | null>(null)
  const [rate, setRate] = useState(1)
  const [playing, setPlaying] = useState<number | null>(null)
  const [quick, setQuick] = useState(false)
  const [comparing, setComparing] = useState(false)
  const [tricky, setTricky] = useState<Set<string>>(new Set())
  const acceptAccent = useAcceptAccent(id)
  const addTricky = useAddTrickyWord()
  const { say } = useSayWord(r?.language ?? 'bn')

  const marks = useMemo(() => r?.marks ?? [], [r?.marks])
  const sel = marks.find((m) => m.index === selected) ?? null
  const checkList = useMemo(() => marks.filter(needsCheck), [marks])

  // Select the first word that needs attention once results arrive.
  useEffect(() => {
    if (selected === null && marks.length) {
      const first = marks.find((m) => m.final_status === 'unsure') ?? marks.find((m) => m.final_status !== 'correct') ?? marks[0]
      setSelected(first.index)
    }
  }, [marks, selected])

  /** Play part of the child's recording; resolves when that part has finished. */
  const playSegment = useCallback(
    (start: number | null, end: number | null, pad = 0.35) =>
      new Promise<void>((resolve) => {
        const a = audioRef.current
        if (!a || start === null) return resolve()
        onStop.current?.()
        onStop.current = resolve
        a.playbackRate = rate
        a.currentTime = Math.max(0, start - pad)
        stopAt.current = end !== null ? end + pad : null
        void a.play().catch(() => resolve())
      }),
    [rate],
  )
  const playWord = useCallback((m: WordMark | null) => (m ? playSegment(m.start, m.end) : Promise.resolve()), [playSegment])
  /** The word with its neighbours, so a cut-off or blended word can be judged in context. */
  const playContext = useCallback(
    (m: WordMark | null) => {
      if (!m) return Promise.resolve()
      const timed = marks.filter((x) => x.start !== null && x.end !== null)
      const k = timed.findIndex((x) => x.index === m.index)
      const prev = k > 0 ? timed[k - 1] : m
      const next = k >= 0 && k < timed.length - 1 ? timed[k + 1] : m
      return playSegment(prev.start, next.end, 0.15)
    },
    [marks, playSegment],
  )
  /** The child's word, then the correct pronunciation, back to back. */
  const compare = useCallback(
    async (m: WordMark | null) => {
      if (!m) return
      setComparing(true)
      try {
        await playSegment(m.start, m.end)
        await new Promise((res) => setTimeout(res, 300))
        await say(m.display)
      } finally {
        setComparing(false)
      }
    },
    [playSegment, say],
  )

  const nextToCheck = useCallback((from: number) => checkList.find((m) => m.index > from) ?? null, [checkList])
  const onSet = useCallback(
    (status: WordStatus | null) => {
      if (!sel) return
      setMark.mutate({ index: sel.index, status })
      if (quick && status !== null) {
        const nxt = nextToCheck(sel.index)
        if (nxt) setSelected(nxt.index)
      }
    },
    [sel, setMark, quick, nextToCheck],
  )

  // Quick check: every word you land on plays by itself.
  useEffect(() => {
    if (quick && sel && r?.has_audio) void playWord(sel)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quick, selected])

  // Keyboard: ←/→ move, 1-4 set status, space plays the word.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!marks.length || (e.target as HTMLElement)?.closest('input,textarea,select')) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault()
        const cur = selected ?? -1
        const next = e.key === 'ArrowRight' ? Math.min(marks.length - 1, cur + 1) : Math.max(0, cur - 1)
        setSelected(next)
      } else if (KEY_STATUS[e.key] && sel) {
        onSet(KEY_STATUS[e.key])
      } else if (e.key === ' ' && sel && r?.has_audio) {
        e.preventDefault()
        void playWord(sel)
      } else if ((e.key === 'c' || e.key === 'C') && sel && r?.has_audio) {
        void playContext(sel)
      } else if ((e.key === 'v' || e.key === 'V') && sel && r?.has_audio) {
        void compare(sel)
      } else if (e.key === 'n' || e.key === 'N') {
        const nxt = nextToCheck(selected ?? -1) ?? checkList[0]
        if (nxt) setSelected(nxt.index)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [marks, selected, sel, onSet, playWord, playContext, compare, nextToCheck, checkList, r?.has_audio])

  if (isLoading) return <PageLoader />
  if (error || !r) return <ErrorBox error={error ?? 'Reading not found'} />

  const back = r.student ? (
    <Link to={`/students/${r.student.id}`} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
      <ArrowLeft className="size-4" /> {r.student.code}
    </Link>
  ) : null
  const header = (
    <PageHeader
      back={back}
      title={
        <span className="flex flex-wrap items-center gap-3">
          <span className={langFont(r.language)}>{r.passage?.title ?? 'Reading'}</span>
          <LanguageBadge language={r.language} />
        </span>
      }
      subtitle={
        <span className="flex flex-wrap items-center gap-2">
          {r.student?.code} · {dateTime(r.created_at)} <ReadingStatusBadge status={r.status} reviewed={r.reviewed} simulated={r.simulated} />
        </span>
      }
      actions={
        <Button variant="ghost" onClick={() => setConfirmDel(true)} aria-label="Delete reading">
          <Trash2 className="size-4" />
        </Button>
      }
    />
  )
  const deleteModal = (
    <Modal
      open={confirmDel}
      onClose={() => setConfirmDel(false)}
      title="Delete this reading?"
      footer={
        <>
          <Button variant="secondary" onClick={() => setConfirmDel(false)}>
            Keep
          </Button>
          <Button
            variant="danger"
            loading={del.isPending}
            onClick={() => del.mutate({ id: r.id, student_id: r.student_id }, { onSuccess: () => nav(r.student ? `/students/${r.student.id}` : '/dashboard') })}
          >
            Delete
          </Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">The marks and any stored audio are removed permanently.</p>
    </Modal>
  )

  if (r.status === 'queued' || r.status === 'processing')
    return (
      <>
        {header}
        <Card>
          <div className="flex justify-center bg-gradient-to-b from-teal-50/60 to-transparent px-4 py-10">
            <ProcessingProgress progress={r.progress} language={r.language} child={false} />
          </div>
        </Card>
      </>
    )
  if (r.status === 'rejected' || r.status === 'failed')
    return (
      <>
        {header}
        {deleteModal}
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="size-6 shrink-0 text-amber-500" />
            <div className="space-y-2">
              <p className="font-medium text-slate-900">{r.status === 'rejected' ? 'The recording quality was too low to assess.' : 'Processing failed.'}</p>
              {r.quality && <p className="text-sm text-slate-600">{r.quality.message_en}</p>}
              {r.error && <ErrorBox error={r.error} />}
              {r.quality && (
                <p className="text-xs text-slate-500">
                  Speech level {r.quality.speech_level_db} dBFS · signal-to-noise {r.quality.snr_db} dB · {secs(r.quality.duration_sec)}
                </p>
              )}
              <div className="flex gap-2 pt-2">
                <Link to={`/read/${r.student_id}/${r.passage_id}`}>
                  <Button>
                    <Mic className="size-4" /> Record again
                  </Button>
                </Link>
                {r.has_audio && (
                  <Button variant="secondary" loading={reprocess.isPending} onClick={() => reprocess.mutate()}>
                    <RefreshCw className="size-4" /> Retry processing
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Card>
      </>
    )

  const m = r.metrics
  return (
    <>
      {header}
      {deleteModal}
      {r.has_audio && (
        <audio
          ref={audioRef}
          src={audioUrl(r.id)}
          preload="auto"
          onTimeUpdate={(e) => {
            const t = e.currentTarget.currentTime
            const cur = marks.find((m) => m.start !== null && m.end !== null && t >= m.start - 0.05 && t <= m.end + 0.05)
            setPlaying(cur ? cur.index : null)
            if (stopAt.current !== null && t >= stopAt.current) {
              e.currentTarget.pause()
              stopAt.current = null
            }
          }}
          onPause={() => {
            setPlaying(null)
            onStop.current?.()
            onStop.current = null
          }}
          onEnded={() => {
            setPlaying(null)
            onStop.current?.()
            onStop.current = null
          }}
        />
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat
          label="Mark"
          value={<MarkBadge score={r.score} size="lg" />}
          hint={`${m?.correct ?? 0} of ${m?.total_words ?? 0} passage words correct`}
        />
        <Stat label="WCPM" value={num(m?.wcpm)} tone={wcpmTone(m?.wcpm)} hint="words correct per minute" />
        <Stat label="Accuracy" value={pct(m?.accuracy)} tone={accTone(m?.accuracy)} hint={`${m?.correct ?? 0} of ${m?.attempted_words ?? 0} words`} />
        <Stat label="Errors" value={m?.errors ?? '—'} hint={`${m?.misread ?? 0} misread · ${m?.skipped ?? 0} skipped`} />
        <Stat label="Unsure" value={m?.unsure ?? '—'} tone={m?.unsure ? 'text-amber-700' : undefined} hint="never counted as errors" />
        <Stat label="Reading time" value={secs(m?.reading_time_sec)} hint={`${m?.hesitations ?? 0} hesitations · ${m?.repetitions ?? 0} repeats`} />
      </div>

      {r.review_stats && (
        <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border border-teal-200 bg-teal-50/60 px-4 py-2.5 text-sm text-teal-900">
          <span className="flex items-center gap-1.5 font-medium">
            <ShieldCheck className="size-4" /> Teacher agrees with AI on {Math.round(r.review_stats.agreement * 100)}% of words
          </span>
          <span>
            {r.review_stats.changed} of {r.review_stats.words} changed by you · {r.review_stats.to_check} flagged to check
          </span>
          {r.review_stats.guards.accent + r.review_stats.guards.noisy + r.review_stats.guards.odd_word > 0 && (
            <span className="text-teal-800">
              Trust guards: {r.review_stats.guards.accent} accent ♪ · {r.review_stats.guards.noisy} noisy 〰 · {r.review_stats.guards.odd_word} odd word ⚑
            </span>
          )}
        </div>
      )}

      {r.quality?.warnings?.includes('noisy') && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          <AlertTriangle className="size-4" /> Background noise was high ({r.quality.snr_db} dB). Check unsure words by listening.
        </div>
      )}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Marked passage"
              subtitle="Click a word to inspect it. Keys: ← → move · 1-4 set · space word · C context · V compare · N next to check"
              actions={
                r.has_audio && (
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-xs" role="group" aria-label="Playback speed">
                      {RATES.map((x) => (
                        <button
                          key={x}
                          type="button"
                          onClick={() => {
                            setRate(x)
                            if (audioRef.current) audioRef.current.playbackRate = x
                          }}
                          className={`rounded-md px-2 py-1 font-medium ${rate === x ? 'bg-white shadow-sm' : 'text-slate-600'}`}
                          title={x === 1 ? 'Normal speed' : 'Slower, to hear small slips'}
                        >
                          {x}×
                        </button>
                      ))}
                    </div>
                    <Button
                      variant={quick ? 'primary' : 'secondary'}
                      size="sm"
                      onClick={() => {
                        const on = !quick
                        setQuick(on)
                        if (on && checkList.length && !(sel && needsCheck(sel))) setSelected(checkList[0].index)
                      }}
                      title="Jump through only the flagged words; each one plays by itself"
                    >
                      <ListChecks className="size-4" /> Quick check{checkList.length ? ` (${checkList.length})` : ''}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        const a = audioRef.current
                        if (!a) return
                        onStop.current?.()
                        onStop.current = null
                        stopAt.current = null
                        a.playbackRate = rate
                        a.currentTime = 0
                        void a.play()
                      }}
                    >
                      <Volume2 className="size-4" /> Play all
                    </Button>
                  </div>
                )
              }
            />
            {quick && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-teal-100 bg-teal-50 px-5 py-2 text-sm text-teal-900">
                <span>
                  Quick check: word {Math.max(1, checkList.findIndex((m) => m.index === selected) + 1)} of {checkList.length}. Listen, then press 1-4;
                  the next flagged word plays by itself.
                </span>
                <button type="button" className="font-medium underline" onClick={() => setQuick(false)}>
                  Stop
                </button>
              </div>
            )}
            <div className="px-5 py-6">
              <MarkedPassage marks={marks} selected={selected} onSelect={setSelected} language={r.language} playing={playing} />
            </div>
            <div className="border-t border-slate-100 px-5 py-3">
              <Legend />
            </div>
          </Card>

          {r.language === 'bn' && (
            <Card>
              <ComparisonPanel reading={r} />
            </Card>
          )}

          <details className="group rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm">
            <summary className="flex cursor-pointer list-none items-center gap-2 font-medium text-slate-700">
              <ChevronDown className="size-4 transition group-open:rotate-180" /> Technical details
            </summary>
            <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-slate-500">
                  {r.language === 'en' ? 'Whisper transcript (English, greedy)' : 'Free-decoding transcript (no language model)'}
                </dt>
                <dd className={`text-base ${langFont(r.language)}`}>{r.transcript || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Model</dt>
                <dd>
                  {r.model_id} {r.processing_ms ? `· processed in ${(r.processing_ms / 1000).toFixed(1)}s` : ''}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Forced alignment</dt>
                <dd>{r.forced_alignment_ok ? 'ok' : 'not available (marks rely on decoding only)'}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Thresholds used</dt>
                <dd className="tabular-nums">
                  {r.thresholds && `conf ≥ ${r.thresholds.free_high} · score high ≥ ${r.thresholds.gop_high} · low ≤ ${r.thresholds.gop_low} · T=${r.thresholds.temperature}`}
                </dd>
              </div>
              {r.quality && (
                <div>
                  <dt className="text-xs text-slate-500">Recording quality</dt>
                  <dd className="tabular-nums">
                    {r.quality.speech_level_db} dBFS · SNR {r.quality.snr_db} dB · {secs(r.quality.duration_sec)}
                  </dd>
                </div>
              )}
            </dl>
          </details>
        </div>

        <div className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <Card className="p-5">
            {sel ? (
              <WordInspector
                mark={sel}
                onSet={onSet}
                saving={setMark.isPending}
                canPlay={r.has_audio}
                onPlay={() => void playWord(sel)}
                onContext={() => void playContext(sel)}
                onCompare={() => void compare(sel)}
                comparing={comparing}
                onAcceptAccent={() => acceptAccent.mutate(sel.index)}
                accepting={acceptAccent.isPending}
                onTricky={() => addTricky.mutate(sel.expected, { onSuccess: () => setTricky((t) => new Set(t).add(sel.expected)) })}
                trickySaved={tricky.has(sel.expected)}
              />
            ) : (
              <EmptyState title="Select a word" />
            )}
            <ErrorBox error={setMark.error || acceptAccent.error || addTricky.error} className="mt-3" />
          </Card>

          <Card className="p-5">
            {r.reviewed ? (
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-6 text-teal-600" />
                <div className="text-sm">
                  <div className="font-medium text-slate-900">Review finalised</div>
                  <div className="text-slate-500">
                    {r.reviewed_at && dateTime(r.reviewed_at)} · audio {r.has_audio ? 'kept' : 'deleted'}. You can still change marks. {!r.simulated && 'Your corrections now help PoraBondhu learn the pronunciations at your school (Settings → Learning).'}
                  </div>
                  {nextInQueue ? (
                    <Link to={`/readings/${nextInQueue.id}`} className="mt-3 inline-flex">
                      <Button size="sm">
                        Next in review queue: {nextInQueue.student_code} <ArrowRight className="size-4" />
                      </Button>
                    </Link>
                  ) : (
                    <Link to="/review" className="mt-3 inline-block text-sm font-medium text-teal-700 hover:underline">
                      Review queue is clear. Back to the queue
                    </Link>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm text-slate-600">
                  When the marks look right, finalise. The audio is deleted unless you choose to keep it.
                </div>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={keepAudio} onChange={(e) => setKeepAudio(e.target.checked)} className="size-4 rounded border-slate-300 text-teal-600" />
                  Keep the audio (needed for re-listening and comparison)
                </label>
                <Button className="w-full" variant="success" loading={finalize.isPending} onClick={() => finalize.mutate(keepAudio)}>
                  <CheckCircle2 className="size-4" /> Finalise review
                </Button>
                <ErrorBox error={finalize.error} />
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
