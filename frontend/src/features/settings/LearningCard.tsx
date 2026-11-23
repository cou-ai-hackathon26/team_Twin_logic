import { BrainCircuit, RotateCcw, Sparkles } from 'lucide-react'
import { useLearning, useLearnNow, useUndoLearning } from '@/api/practice'
import { Badge, Button, Card, CardHeader, ErrorBox, ProgressBar } from '@/components/ui/primitives'

const pct = (x: number) => `${(x * 100).toFixed(1)}%`

/** How PoraBondhu improves from the teacher's reviews (no model retraining, fully reversible). */
export function LearningCard() {
  const { data, error } = useLearning()
  const learn = useLearnNow()
  const undo = useUndoLearning()
  if (!data) return <ErrorBox error={error} />
  const progress = Math.min(1, Math.min(data.reviewed_readings / data.needs.readings, data.decided_words / data.needs.words))
  const result = learn.data?.thresholds
  return (
    <Card className="xl:col-span-2">
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <BrainCircuit className="size-4 text-teal-700" /> Learning from your reviews
          </span>
        }
        subtitle="Every review you finalise is a lesson for PoraBondhu. It adapts to your school's pronunciations and to how you mark, without sending data anywhere."
      />
      <div className="grid gap-6 p-5 lg:grid-cols-3">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Your reviews so far</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {data.reviewed_readings} <span className="text-sm font-normal text-slate-500">readings · {data.decided_words} words</span>
          </div>
          <ProgressBar className="mt-2" value={progress} />
          <p className="mt-1 text-xs text-slate-500">
            Marking rules are re-tuned after {data.needs.readings} reviewed readings and {data.needs.words} decided words; pronunciations after 3
            readings with the same correction.
          </p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Agreement with you now</div>
          {data.agreement_now ? (
            <ul className="mt-1 space-y-0.5 text-sm tabular-nums text-slate-700">
              <li>Errors you confirmed that it found: <b>{pct(data.agreement_now.recall)}</b></li>
              <li>Its error marks you kept: <b>{pct(data.agreement_now.precision)}</b></li>
              <li>Correct words it wrongly flagged: <b>{pct(data.agreement_now.false_alarm)}</b></li>
            </ul>
          ) : (
            <p className="mt-1 text-sm text-slate-500">Appears after your first finalised review of a real recording.</p>
          )}
          <p className="mt-2 text-xs text-slate-500">
            Rules in use: {data.thresholds_source}
            {data.last_learned?.reviewed_readings ? ` (from ${data.last_learned.reviewed_readings} of your reviews)` : ''}.
          </p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Pronunciations learned</div>
          {data.learned_variants.length ? (
            <div className="mt-1 flex flex-wrap gap-1.5">
              {data.learned_variants.map((v) => (
                <Badge key={v.word + v.variant} className="bg-teal-50 font-bn text-sm text-teal-900 ring-teal-200">
                  {v.word} ≈ {v.variant}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-slate-500">None yet. When you accept the same pronunciation of a word three times, it stops being flagged.</p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 px-5 py-3">
        <Button variant="secondary" size="sm" onClick={() => learn.mutate()} loading={learn.isPending}>
          <Sparkles className="size-4" /> Learn now
        </Button>
        {data.can_undo && (
          <Button variant="ghost" size="sm" onClick={() => undo.mutate()} loading={undo.isPending}>
            <RotateCcw className="size-4" /> Undo last change
          </Button>
        )}
        {result && (
          <span className="text-sm text-slate-600">
            {result.changed ? 'Marking rules updated to agree better with your reviews.' : result.reason}
          </span>
        )}
        <ErrorBox error={learn.error ?? undo.error} />
      </div>
    </Card>
  )
}
