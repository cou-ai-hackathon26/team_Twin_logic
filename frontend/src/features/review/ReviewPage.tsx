import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, Mic, RefreshCw, Trash2, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { audioUrl } from '@/api/client'
import { useDeleteReading, useFinalize, useReading, useReprocess, useReviewQueue, useSetMark } from '@/api/hooks'
import type { WordStatus } from '@/api/types'
import { LanguageBadge, MarkBadge, ReadingStatusBadge } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Modal, PageHeader, PageLoader, Stat } from '@/components/ui/primitives'
import { ProcessingProgress } from '@/features/assess/ProcessingProgress'
import { accTone, dateTime, langFont, num, pct, secs, wcpmTone } from '@/lib/format'
import { ComparisonPanel } from './ComparisonPanel'
import { Legend, MarkedPassage } from './MarkedPassage'
import { WordInspector } from './WordInspector'

const KEY_STATUS: Record<string, WordStatus> = { '1': 'correct', '2': 'misread', '3': 'skipped', '4': 'unsure' }

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

  const marks = useMemo(() => r?.marks ?? [], [r?.marks])
  const sel = marks.find((m) => m.index === selected) ?? null

  // Select the first word that needs attention once results arrive.
  useEffect(() => {
    if (selected === null && marks.length) {
      const first = marks.find((m) => m.final_status === 'unsure') ?? marks.find((m) => m.final_status !== 'correct') ?? marks[0]
      setSelected(first.index)
    }
  }, [marks, selected])

  const playSegment = useCallback((start: number | null, end: number | null) => {
    const a = audioRef.current
    if (!a || start === null) return
    a.currentTime = Math.max(0, start - 0.35)
    stopAt.current = end !== null ? end + 0.35 : null
    void a.play()
  }, [])

  const onSet = useCallback(
    (status: WordStatus | null) => sel && setMark.mutate({ index: sel.index, status }),
    [sel, setMark],
  )

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
        playSegment(sel.start, sel.end)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [marks, selected, sel, onSet, playSegment, r?.has_audio])

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
          {r.student?.code} · {dateTime(r.created_at)} <ReadingStatusBadge status={r.status} reviewed={r.reviewed} />
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
            if (stopAt.current !== null && e.currentTarget.currentTime >= stopAt.current) {
              e.currentTarget.pause()
              stopAt.current = null
            }
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

      {r.quality?.warnings?.includes('noisy') && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          <AlertTriangle className="size-4" /> Background noise was high ({r.quality.snr_db} dB). Check unsure words by listening.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Marked passage"
              subtitle="Click a word to inspect it. Keys: ← → move · 1-4 set · space listen"
              actions={
                r.has_audio && (
                  <Button variant="secondary" size="sm" onClick={() => audioRef.current && (audioRef.current.currentTime = 0, stopAt.current = null, void audioRef.current.play())}>
                    <Volume2 className="size-4" /> Play all
                  </Button>
                )
              }
            />
            <div className="px-5 py-6">
              <MarkedPassage marks={marks} selected={selected} onSelect={setSelected} language={r.language} />
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
                onPlay={() => playSegment(sel.start, sel.end)}
              />
            ) : (
              <EmptyState title="Select a word" />
            )}
            <ErrorBox error={setMark.error} className="mt-3" />
          </Card>

          <Card className="p-5">
            {r.reviewed ? (
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-6 text-teal-600" />
                <div className="text-sm">
                  <div className="font-medium text-slate-900">Review finalised</div>
                  <div className="text-slate-500">
                    {r.reviewed_at && dateTime(r.reviewed_at)} · audio {r.has_audio ? 'kept' : 'deleted'}. You can still change marks.
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
