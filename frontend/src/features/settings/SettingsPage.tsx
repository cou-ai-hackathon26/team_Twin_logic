import clsx from 'clsx'
import { Cpu, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useAddVariant, useDeleteVariant, useSystem, useVariants, useWarmup } from '@/api/hooks'
import type { ModelStatus } from '@/api/types'
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, Input, PageHeader, PageLoader } from '@/components/ui/primitives'
import { PasswordCard, PrivacyCard } from './AccountCards'

function StateBadge({ s }: { s: ModelStatus }) {
  const cls = {
    ready: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    loading: 'bg-amber-50 text-amber-800 ring-amber-200',
    error: 'bg-rose-50 text-rose-800 ring-rose-200',
    not_loaded: 'bg-slate-50 text-slate-600 ring-slate-200',
  }[s.state]
  return <Badge className={cls}>{s.state.replace('_', ' ')}</Badge>
}

export function SettingsPage() {
  const { data, isLoading, error } = useSystem()
  const warm = useWarmup()
  const variants = useVariants()
  const addV = useAddVariant()
  const delV = useDeleteVariant()
  const [word, setWord] = useState('')
  const [variant, setVariant] = useState('')

  if (isLoading) return <PageLoader />
  if (!data) return <ErrorBox error={error} />
  const th = data.thresholds
  return (
    <>
      <PageHeader title="Settings" subtitle="Speech models run on this server's CPU. No audio is sent to any outside AI service." />
      <div className="grid gap-6 xl:grid-cols-2">
        <PrivacyCard settings={data.settings} />
        <PasswordCard demo={data.settings.demo_mode} />
        <Card>
          <CardHeader
            title="Speech models"
            actions={
              <>
                <Button variant="secondary" size="sm" loading={warm.isPending && !warm.variables} onClick={() => warm.mutate(false)}>
                  <Cpu className="size-4" /> Load CTC
                </Button>
                <Button variant="secondary" size="sm" loading={warm.isPending && !!warm.variables} onClick={() => warm.mutate(true)}>
                  Load all
                </Button>
              </>
            }
          />
          <dl className="divide-y divide-slate-100 text-sm">
            <div className="flex items-center justify-between gap-4 px-5 py-3">
              <dt>
                <div className="font-medium">Bangla CTC (wav2vec2)</div>
                <div className="text-xs text-slate-500">
                  {data.models.ctc.model_id} · {data.models.ctc.backend}
                </div>
              </dt>
              <dd className="flex items-center gap-2">
                {data.models.ctc.load_sec && <span className="text-xs text-slate-500">{data.models.ctc.load_sec}s</span>}
                <StateBadge s={data.models.ctc} />
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 px-5 py-3">
              <dt>
                <div className="font-medium">Whisper baseline</div>
                <div className="text-xs text-slate-500">
                  faster-whisper {data.models.whisper.model} · int8 {data.models.whisper.enabled ? '' : '· disabled'}
                </div>
              </dt>
              <dd className="flex items-center gap-2">
                {data.models.whisper.load_sec && <span className="text-xs text-slate-500">{data.models.whisper.load_sec}s</span>}
                <StateBadge s={data.models.whisper} />
              </dd>
            </div>
          </dl>
          <ErrorBox className="m-5" error={warm.error || data.models.ctc.error || data.models.whisper.error} />
        </Card>

        <Card>
          <CardHeader
            title="Decision thresholds"
            subtitle={th._meta ? `Tuned on ${String((th._meta as { recordings?: number }).recordings ?? '?')} tuning recordings` : 'Defaults: run scripts/calibrate.py on tuning speakers to tune them'}
          />
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 px-5 py-4 text-sm">
            {[
              ['Free-decoding confidence counted high', `≥ ${th.free_high}`],
              ['Expected-text score counted high', `≥ ${th.gop_high}`],
              ['Expected-text score counted low', `≤ ${th.gop_low}`],
              ['Logit temperature', th.temperature],
              ['Hesitation pause', `${th.hesitation_sec} s`],
              ['Weak pattern after', `${data.settings.weak_min_errors} errors in ${data.settings.weak_min_readings}+ readings`],
              ['Unsure words in WCPM', data.settings.count_unsure_as_correct ? 'counted as correct (provisional)' : 'excluded'],
              ['Database', data.settings.database],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt className="text-xs text-slate-500">{k}</dt>
                <dd className="font-medium tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Accepted variants"
            subtitle="Regional pronunciations the school accepts as correct for a word (e.g. a local form). They are never flagged as errors."
          />
          <form
            className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-4"
            onSubmit={(e) => {
              e.preventDefault()
              addV.mutate({ word, variant }, { onSuccess: () => (setWord(''), setVariant('')) })
            }}
          >
            <Input className="w-48 font-bn" placeholder="Passage word" value={word} onChange={(e) => setWord(e.target.value)} />
            <Input className="w-48 font-bn" placeholder="Accepted form" value={variant} onChange={(e) => setVariant(e.target.value)} />
            <Button type="submit" loading={addV.isPending} disabled={!word || !variant}>
              <Plus className="size-4" /> Add
            </Button>
            <ErrorBox error={addV.error} />
          </form>
          {!variants.data?.length ? (
            <EmptyState title="No accepted variants" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {variants.data.map((v) => (
                <li key={v.id} className={clsx('flex items-center justify-between px-5 py-2.5')}>
                  <span className="font-bn text-base">
                    {v.word} <span className="text-slate-400">≈</span> {v.variant}
                  </span>
                  <Button variant="ghost" size="sm" onClick={() => delV.mutate(v.id)} aria-label="Remove">
                    <Trash2 className="size-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
