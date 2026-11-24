import { ShieldCheck } from 'lucide-react'
import type { Proportion, TrustTest } from '@/api/types'
import { Card, CardHeader } from '@/components/ui/primitives'

const pc = (p: Proportion | undefined) => (p && p.value !== null ? `${(p.value * 100).toFixed(1)}%` : 'n/a')
const ci = (p: Proportion | undefined) =>
  p && p.ci_low !== null && p.ci_high !== null ? `${(p.ci_low * 100).toFixed(1)}-${(p.ci_high * 100).toFixed(1)}` : ''
const count = (p: Proportion | undefined) => (p ? `${p.k}/${p.n}` : '')

function Cell({ off, on, lowerIsBetter }: { off: Proportion; on: Proportion; lowerIsBetter: boolean }) {
  const better = off.value !== null && on.value !== null && (lowerIsBetter ? on.value < off.value : on.value > off.value)
  const worse = off.value !== null && on.value !== null && (lowerIsBetter ? on.value > off.value : on.value < off.value)
  return (
    <td className="px-3 py-2.5 tabular-nums">
      <span className="text-slate-500">{pc(off)}</span>
      <span className="mx-1 text-slate-400">→</span>
      <span className={better ? 'font-semibold text-teal-700' : worse ? 'font-semibold text-rose-700' : 'font-semibold'}>{pc(on)}</span>
      <div className="text-[11px] text-slate-400">
        {count(off)} → {count(on)} · CI {ci(on)}
      </div>
    </td>
  )
}

/** Trust test: does the diagnosis hold up with background noise and a regional accent? */
export function TrustTestCard({ t }: { t: TrustTest }) {
  const a = t.accent
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-teal-700" /> Trust test: background noise and regional accent
          </span>
        }
        subtitle={`${t.label}. Each cell: trust guards off → on, on the same decoded recordings (paired). Counts and 95% Wilson intervals under each value. Noise: three other test speakers talking at once (classroom babble) or broadband hiss, mixed in at the stated signal-to-noise ratio.`}
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs tracking-wide text-slate-500 uppercase">
              <th className="px-5 py-2 font-medium">Condition</th>
              <th className="px-3 py-2 font-medium">False alarms (correct word flagged)</th>
              <th className="px-3 py-2 font-medium">Recall (real errors found)</th>
              <th className="px-3 py-2 font-medium">Unsure (left to teacher)</th>
              <th className="px-3 py-2 font-medium">Guard changes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Object.entries(t.noise).map(([k, c]) => (
              <tr key={k}>
                <td className="px-5 py-2.5 font-medium">{c.label}</td>
                <Cell off={c.guards_off.false_alarm} on={c.guards_on.false_alarm} lowerIsBetter />
                <Cell off={c.guards_off.recall} on={c.guards_on.recall} lowerIsBetter={false} />
                <td className="px-3 py-2.5 tabular-nums text-slate-600">
                  {pc(c.guards_off.unsure_rate)} → {pc(c.guards_on.unsure_rate)}
                </td>
                <td className="px-3 py-2.5 text-xs text-slate-500">
                  {c.guard_changes.accent} accent · {c.guard_changes.noisy} noisy · {c.guard_changes.odd_word} odd
                </td>
              </tr>
            ))}
            <tr className="bg-slate-50/60">
              <td className="px-5 py-2.5 font-medium">
                {a.label}
                <div className="text-[11px] font-normal text-slate-500">{a.accent_words} words read in the regional way</div>
              </td>
              <Cell off={a.guards_off.false_alarm} on={a.guards_on.false_alarm} lowerIsBetter />
              <td className="px-3 py-2.5 text-xs text-slate-500">
                other words' false alarms: {pc(a.other_words_false_alarm.guards_off)} → {pc(a.other_words_false_alarm.guards_on)}
              </td>
              <td className="px-3 py-2.5 tabular-nums text-slate-600">
                {pc(a.guards_off.unsure_rate)} → {pc(a.guards_on.unsure_rate)}
              </td>
              <td className="px-3 py-2.5 text-xs text-slate-500">
                {a.guard_changes.accent} accent · {a.guard_changes.noisy} noisy · {a.guard_changes.odd_word} odd
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        Limits: adult FLEURS speakers, not children; the accent is simulated by changing the passage spelling so the
        speaker's real pronunciation is the regional form (no real dialect recordings yet); a genuine aspiration slip is
        also sent to the teacher as unsure (♪), so recall counts it as not found even though the teacher still hears it. Generated {t.generated_at.slice(0, 10)}.
      </p>
    </Card>
  )
}
