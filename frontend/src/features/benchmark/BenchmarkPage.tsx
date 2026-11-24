import { EvidenceSection } from './EvidenceSection'
import { TrustTestCard } from './TrustTestCard'
import { WordClassifierCard } from './WordClassifierCard'
import clsx from 'clsx'
import { CheckCircle2, FlaskConical, XCircle } from 'lucide-react'
import { useBenchmark } from '@/api/hooks'
import type { Proportion } from '@/api/types'
import { Badge, Card, CardHeader, EmptyState, ErrorBox, PageHeader, PageLoader } from '@/components/ui/primitives'

const SYSTEM_LABEL: Record<string, string> = {
  whisper_word: 'Whisper + word compare',
  ctc_word: 'Bangla CTC + word compare',
  porabondhu: 'PoraBondhu',
}

function P({ p }: { p: Proportion | null | undefined }) {
  if (!p || p.value === null) return <span className="text-slate-400">n/a</span>
  return (
    <span className="tabular-nums">
      <span className="font-semibold">{(p.value * 100).toFixed(1)}%</span>
      <span className="ml-1 text-xs text-slate-500">
        {p.k}/{p.n}
      </span>
      <div className="text-[11px] text-slate-400">
        CI {((p.ci_low ?? 0) * 100).toFixed(0)}–{((p.ci_high ?? 0) * 100).toFixed(0)}%
      </div>
    </span>
  )
}

export function BenchmarkPage() {
  const { data, isLoading, error } = useBenchmark()
  if (isLoading) return <PageLoader />
  return (
    <>
      <PageHeader
        title="Benchmark"
        subtitle={!data?.available
          ? 'No benchmark result is published yet.'
          : Object.keys(data.results ?? {}).length < 3
            ? 'Pilot result for the system(s) shown. Check the label and sample-size limits; this is not child validation.'
            : 'Three systems on the same recordings, with 95% confidence intervals. Targets we miss are shown too.'}
      />
      <ErrorBox error={error} />
      {!data?.available ? (
        <Card>
          <EmptyState icon={<FlaskConical className="size-12" />} title={data?.reason ? 'No publishable benchmark result yet' : 'No benchmark has been run yet'}>
            {data?.reason && <p className="mb-3 text-sm text-slate-600">{data.reason}</p>}
            Collect and annotate recordings (see <code>docs/DATA_COLLECTION.md</code>), tune thresholds on the tuning speakers, then run:
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-left text-xs text-slate-100">
              {`python -m scripts.calibrate --recordings eval/recordings.csv --annotations eval/annotations.csv
python -m scripts.benchmark --recordings eval/recordings.csv --annotations eval/annotations.csv`}
            </pre>
          </EmptyState>
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Badge>{data.split} split</Badge>
            <Badge>{data.recordings} recordings</Badge>
            <Badge>{data.speakers?.length} speakers</Badge>
            {data.label && <Badge className="bg-amber-50 text-amber-800 ring-amber-200">{data.label}</Badge>}
            <span>generated {data.generated_at && new Date(data.generated_at).toLocaleString()}</span>
            <span className="text-slate-400">
              · {data.model?.ctc} ({data.model?.ctc_backend}) · whisper {data.model?.whisper ?? 'off'}
            </span>
          </div>

          {data.hypothesis && (
            <Card className={clsx('p-5', data.hypothesis.supported ? 'border-emerald-200 bg-emerald-50/50' : 'border-amber-200 bg-amber-50/50')}>
              <div className="flex items-start gap-3">
                {data.hypothesis.supported ? <CheckCircle2 className="size-6 text-emerald-600" /> : <XCircle className="size-6 text-amber-600" />}
                <div>
                  <div className="font-semibold text-slate-900">
                    Error-preserving hypothesis {data.hypothesis.supported ? 'supported' : 'not supported'}
                  </div>
                  <div className="text-sm text-slate-600">
                    PoraBondhu recall {data.hypothesis.recall_gain_pp >= 0 ? '+' : ''}
                    {data.hypothesis.recall_gain_pp} percentage points vs Whisper (needs ≥ +10), precision {data.hypothesis.precision_not_worse ? 'not worse' : 'worse'}.
                  </div>
                </div>
              </div>
            </Card>
          )}

          {Object.keys(data.results?.porabondhu ?? {}).map((group) => (
            <Card key={group}>
              <CardHeader title={group === 'all' ? 'All test recordings' : group.replace('_', ' · ')} />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-2 font-medium">System</th>
                      <th className="px-3 py-2 font-medium">Recall</th>
                      <th className="px-3 py-2 font-medium">Precision</th>
                      <th className="px-3 py-2 font-medium">False alarms</th>
                      <th className="px-3 py-2 font-medium">Unsure</th>
                      <th className="px-3 py-2 font-medium">Grapheme acc.</th>
                      <th className="px-3 py-2 font-medium">WCPM MAE</th>
                      <th className="px-3 py-2 font-medium">s / 60 s</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(data.results ?? {}).map(([sys, groups]) => {
                      const r = groups[group]
                      if (!r) return null
                      return (
                        <tr key={sys} className={sys === 'porabondhu' ? 'bg-teal-50/40' : ''}>
                          <td className="px-5 py-3 font-medium">{SYSTEM_LABEL[sys] ?? sys}</td>
                          <td className="px-3 py-3"><P p={r.recall} /></td>
                          <td className="px-3 py-3"><P p={r.precision} /></td>
                          <td className="px-3 py-3"><P p={r.false_alarm} /></td>
                          <td className="px-3 py-3"><P p={r.unsure_rate} /></td>
                          <td className="px-3 py-3"><P p={r.grapheme_accuracy} /></td>
                          <td className="px-3 py-3 tabular-nums">{r.wcpm_mae ?? 'n/a'}</td>
                          <td className="px-3 py-3 tabular-nums">{r.sec_per_60s ?? 'n/a'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}

          {data.trust_test && <TrustTestCard t={data.trust_test} />}

          {data.word_classifier && <WordClassifierCard w={data.word_classifier} />}

          {data.evidence && <EvidenceSection e={data.evidence} />}

          {Object.entries(data.targets ?? {}).map(([g, rows]) => (
            <Card key={g}>
              <CardHeader title={`Success criteria (${g})`} subtitle="Fixed in the proposal before any code was written." />
              <ul className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <li key={r.measure} className="flex items-center justify-between px-5 py-2.5 text-sm">
                    <span className="text-slate-700">{r.measure.replaceAll('_', ' ')}</span>
                    <span className="flex items-center gap-3 tabular-nums">
                      <span className="text-slate-500">{r.target}</span>
                      <span className="w-16 text-right font-medium">{r.value === null ? 'n/a' : r.value.toFixed(3)}</span>
                      {r.met === null ? (
                        <Badge>n/a</Badge>
                      ) : r.met ? (
                        <Badge className="bg-emerald-50 text-emerald-800 ring-emerald-200">met</Badge>
                      ) : (
                        <Badge className="bg-rose-50 text-rose-800 ring-rose-200">missed</Badge>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
