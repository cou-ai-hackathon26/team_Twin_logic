import type { BenchmarkEvidence, PairedDiff, Proportion } from '@/api/types'
import { Badge, Card, CardHeader } from '@/components/ui/primitives'

const METRICS = ['recall', 'precision', 'false_alarm', 'unsure_rate'] as const
const NAME: Record<string, string> = {
  porabondhu_minus_whisper_word: 'PoraBondhu − Whisper + word compare',
  porabondhu_minus_ctc_word: 'PoraBondhu − plain CTC + word compare',
  childlike_minus_original: 'Phase-vocoder child-like − original (confounded)',
  childlike_rs_minus_original: 'Resampled child-like voice − original voice (PoraBondhu)',
}
const SET: Record<string, string> = {
  original: 'Original voices (paired reference)',
  childlike: 'Phase-vocoder child-like voice (confounded by processing artifacts, see notes)',
  unseen: 'Error types the detector was not designed around',
  skipcut: 'Real skips: word audio cut out',
  childlike_rs: 'Child-like voice by resampling (pitch + formants up 10-20%); a proxy, not children',
}
const pp = (x: number) => `${x >= 0 ? '+' : ''}${(x * 100).toFixed(1)}`
const label = (m: string) => m.replace('_', ' ')

function Cell({ p }: { p: Proportion | number | null | undefined }) {
  if (!p || typeof p === 'number' || p.value === null) return <span className="text-slate-400">n/a</span>
  return (
    <span className="tabular-nums">
      <b>{(p.value * 100).toFixed(1)}%</b>
      <span className="block text-[11px] text-slate-400">
        {p.k}/{p.n} · CI {((p.ci_low ?? 0) * 100).toFixed(0)}–{((p.ci_high ?? 0) * 100).toFixed(0)}%
      </span>
    </span>
  )
}

function Head({ first }: { first: string }) {
  return (
    <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
      <tr>
        <th className="px-5 py-2 font-medium">{first}</th>
        {METRICS.map((m) => (
          <th key={m} className="px-3 py-2 font-medium">
            {label(m)}
          </th>
        ))}
      </tr>
    </thead>
  )
}

/** Paired comparisons, robustness sets and tuning, exactly as published in backend/results/. */
export function EvidenceSection({ e }: { e: BenchmarkEvidence }) {
  const cal = e.calibration
  return (
    <>
      {Object.keys(e.comparisons).length > 0 && (
        <Card>
          <CardHeader
            title="Paired differences"
            subtitle="Same recordings scored by both arms; 95% bootstrap interval over recordings, in percentage points. ≠0 marks intervals that exclude zero."
          />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <Head first="Comparison" />
              <tbody className="divide-y divide-slate-100">
                {Object.entries(e.comparisons).map(([k, c]) => (
                  <tr key={k}>
                    <td className="px-5 py-3 font-medium">
                      {NAME[k] ?? k} <span className="text-xs font-normal text-slate-500">n={c.recordings}</span>
                    </td>
                    {METRICS.map((m) => {
                      const d = c[m] as PairedDiff | undefined
                      return (
                        <td key={m} className="px-3 py-3 tabular-nums">
                          {d ? (
                            <>
                              <b>{pp(d.diff)}</b>
                              {d.excludes_zero && <Badge className="ml-1 bg-slate-800 text-white ring-slate-800">≠0</Badge>}
                              <span className="block text-[11px] text-slate-400">
                                {pp(d.ci_low)} to {pp(d.ci_high)}
                              </span>
                            </>
                          ) : (
                            'n/a'
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {Object.keys(e.robustness).length > 0 && (
        <Card>
          <CardHeader title="Robustness checks (PoraBondhu only)" subtitle="Built from FLEURS test speakers; labels exact by construction. None of these is child speech." />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <Head first="Set" />
              <tbody className="divide-y divide-slate-100">
                {Object.entries(e.robustness).map(([k, r]) => (
                  <tr key={k}>
                    <td className="px-5 py-3">
                      <span className="font-medium">{SET[k] ?? k}</span> <span className="text-xs text-slate-500">n={r.recordings}</span>
                    </td>
                    {METRICS.map((m) => (
                      <td key={m} className="px-3 py-3">
                        <Cell p={r.porabondhu[m] as Proportion | null} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {!!e.notes?.length && (
        <Card>
          <CardHeader title="Notes on the robustness checks" />
          <ul className="list-disc space-y-1.5 px-9 py-4 text-sm text-slate-700">
            {e.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </Card>
      )}
      {cal && (
        <Card>
          <CardHeader title="Threshold tuning (development recordings only)" subtitle="Test recordings were never used to choose thresholds." />
          <ul className="space-y-1.5 px-5 py-4 text-sm text-slate-700">
            <li>
              Chosen:{' '}
              {Object.entries(cal.wide_grid_best.thresholds)
                .filter(([k]) => ['free_high', 'gop_high', 'gop_low', 'temperature'].includes(k))
                .map(([k, v]) => `${k} ${v}`)
                .join(', ')}
            </li>
            <li>
              3-fold cross-validation on {cal.recordings} recordings:{' '}
              {METRICS.map((m) => `${label(m)} ${(cal.cross_validation[m].mean * 100).toFixed(1)}% ± ${(cal.cross_validation[m].sd * 100).toFixed(1)}`).join(' · ')}
            </li>
            {Object.values(cal.on_grid_edge).some(Boolean) && (
              <li className="text-amber-800">
                At the edge of the searched range:{' '}
                {Object.entries(cal.on_grid_edge)
                  .filter(([, v]) => v)
                  .map(([k]) => k)
                  .join(', ')}{' '}
                (the best value may lie further out).
              </li>
            )}
          </ul>
        </Card>
      )}
    </>
  )
}
