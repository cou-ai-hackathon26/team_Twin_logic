import clsx from 'clsx'
import { Scale } from 'lucide-react'
import { useCompare } from '@/api/hooks'
import type { Reading, WordStatus } from '@/api/types'
import { Button, CardHeader, EmptyState, ErrorBox, Spinner } from '@/components/ui/primitives'
import { STATUS_META, num, pct } from '@/lib/format'

const SYSTEMS: { key: string; label: string; hint: string }[] = [
  { key: 'whisper_word', label: 'Whisper + word compare', hint: 'Baseline 1: language-model decoder' },
  { key: 'ctc_word', label: 'Bangla CTC + word compare', hint: 'Baseline 2: no grapheme engine' },
  { key: 'porabondhu', label: 'PoraBondhu', hint: 'CTC + grapheme alignment + confidence' },
]

const cellTone = (s: WordStatus | undefined) =>
  s === 'misread' ? 'bg-rose-500' : s === 'skipped' ? 'bg-slate-500' : s === 'unsure' ? 'bg-amber-400' : s === 'not_reached' ? 'bg-slate-200' : 'bg-emerald-400'

export function ComparisonPanel({ reading }: { reading: Reading }) {
  const compare = useCompare(reading.id)
  const busy = reading.comparison_status === 'queued' || reading.comparison_status === 'processing'
  const systems = reading.comparison?.systems
  const marks = reading.marks ?? []

  const rows = SYSTEMS.map((s) => {
    if (s.key === 'porabondhu')
      return { ...s, statuses: marks.map((m) => m.status), metrics: reading.metrics, transcript: reading.transcript ?? '', error: undefined, ms: reading.processing_ms }
    const sys = systems?.[s.key]
    return { ...s, statuses: sys?.marks?.map((m) => m.status) ?? [], metrics: sys?.metrics ?? null, transcript: sys?.transcript ?? '', error: sys?.error, ms: sys?.processing_ms ?? null }
  })

  return (
    <>
      <CardHeader
        title="Baseline comparison"
        subtitle="The same audio through three systems. Same passage, same words."
        actions={
          <Button variant="secondary" size="sm" loading={busy || compare.isPending} disabled={!reading.has_audio} onClick={() => compare.mutate()}>
            <Scale className="size-4" /> {systems ? 'Run again' : 'Run comparison'}
          </Button>
        }
      />
      <div className="p-5">
        <ErrorBox error={compare.error || reading.comparison?.error} className="mb-3" />
        {!reading.has_audio && !systems && <EmptyState title="Audio was not kept for this reading, so it cannot be compared." />}
        {busy && (
          <div className="mb-3 flex items-center gap-2 text-sm text-slate-600">
            <Spinner className="size-4" /> Running baselines on CPU (Whisper can take a minute)…
          </div>
        )}
        {systems && (
          <div className="space-y-4">
            {rows.map((r) => (
              <div key={r.key}>
                <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <span className={clsx('text-sm font-semibold', r.key === 'porabondhu' ? 'text-teal-800' : 'text-slate-800')}>{r.label}</span>
                    <span className="ml-2 text-xs text-slate-500">{r.hint}</span>
                  </div>
                  {r.metrics && (
                    <span className="text-xs tabular-nums text-slate-600">
                      {r.metrics.errors} errors · {r.metrics.unsure} unsure · {num(r.metrics.wcpm)} WCPM · {pct(r.metrics.accuracy)} · {r.ms ? `${(r.ms / 1000).toFixed(1)}s` : ''}
                    </span>
                  )}
                </div>
                {r.error ? (
                  <ErrorBox error={r.error} />
                ) : (
                  <div className="flex flex-wrap gap-0.5">
                    {marks.map((m, i) => (
                      <div
                        key={i}
                        className={clsx('h-5 w-3 rounded-sm', cellTone(r.statuses[i]))}
                        title={`${m.display}: ${r.statuses[i] ? STATUS_META[r.statuses[i]].label : '—'}`}
                      />
                    ))}
                  </div>
                )}
                {r.transcript && <div className="mt-1 truncate font-bn text-xs text-slate-500" title={r.transcript}>{r.transcript}</div>}
              </div>
            ))}
            <p className="text-xs text-slate-500">
              One cell per passage word: green correct, red misread, grey skipped, amber unsure. Teacher corrections are not applied here.
            </p>
          </div>
        )}
      </div>
    </>
  )
}
