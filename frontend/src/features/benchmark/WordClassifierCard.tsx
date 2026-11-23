import { BrainCircuit } from 'lucide-react'
import type { ClsStats, WordClassifierReport } from '@/api/types'
import { Badge, Card, CardHeader } from '@/components/ui/primitives'

const pct = (x: number) => `${(x * 100).toFixed(1)}%`
const pp = (x: number) => `${x >= 0 ? '+' : ''}${(x * 100).toFixed(1)}`
const ROWS: [keyof ClsStats, string, boolean][] = [
  ['precision', 'Precision (target ≥ 80%)', true],
  ['recall', 'Recall', true],
  ['false_alarm', 'False alarms (≤ 5%)', false],
  ['unsure_rate', 'Unsure (sent to the teacher)', false],
  ['f1', 'F1', true],
]

/** The trained word-error classifier vs the hand-set rules, on the same held-out test recordings. */
export function WordClassifierCard({ w }: { w: WordClassifierReport }) {
  const d = w.difference_learned_minus_rules_test
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <BrainCircuit className="size-4 text-teal-700" /> Trained word classifier vs hand-set rules
            {w.use_in_app ? (
              <Badge className="bg-teal-50 text-teal-800 ring-teal-200">used by the app</Badge>
            ) : (
              <Badge className="bg-slate-50 text-slate-600 ring-slate-200">not used: did not beat the rules</Badge>
            )}
          </span>
        }
        subtitle={`Logistic regression on 18 evidence features per flagged word, trained on ${w.train.recordings} tuning recordings only (${w.train.candidate_words} words); cut-off chosen by 5-fold cross-validation (false alarms ≤ 5%). Tested once on the same ${w.test.recordings} held-out test recordings as the table above. Adult speech with simulated errors, not children.`}
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs tracking-wide text-slate-500 uppercase">
              <th className="px-5 py-2 font-medium">Held-out test</th>
              <th className="px-3 py-2 font-medium">Rules (thresholds)</th>
              <th className="px-3 py-2 font-medium">Trained classifier</th>
              <th className="px-3 py-2 font-medium">Difference (95% CI, pp)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {ROWS.map(([k, name, up]) => {
              const diff = d[k as string]
              const sig = diff && (diff.ci95[0] > 0 || diff.ci95[1] < 0)
              const good = diff && (up ? diff.diff > 0 : diff.diff < 0)
              return (
                <tr key={k}>
                  <td className="px-5 py-2.5 font-medium">{name}</td>
                  <td className="px-3 py-2.5 tabular-nums">{pct(w.rules_test[k])}</td>
                  <td className="px-3 py-2.5 font-semibold tabular-nums">{pct(w.learned_test[k])}</td>
                  <td className="px-3 py-2.5 tabular-nums">
                    {diff ? (
                      <span className={sig ? (good ? 'font-semibold text-teal-700' : 'font-semibold text-rose-700') : 'text-slate-500'}>
                        {pp(diff.diff)} ({pp(diff.ci95[0])} to {pp(diff.ci95[1])}){sig ? ' *' : ''}
                      </span>
                    ) : (
                      'n/a'
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="space-y-1 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        <p>
          * the bootstrap interval (2000 resamples of recordings) excludes zero. The cross-validated cut-off put every flagged word on one side, so the
          classifier sends no word to "unsure"; the teacher still reviews every reading and has the final word. Teacher reviews later tune this cut-off
          (Settings → Learning from your reviews).
        </p>
        <p>
          Strongest evidence: {w.strongest_features.slice(0, 4).map((f) => `${f.feature} (${f.weight > 0 ? '+' : ''}${f.weight})`).join(', ')}.
        </p>
      </div>
    </Card>
  )
}
