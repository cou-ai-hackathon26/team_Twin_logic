import clsx from 'clsx'
import { Flag, Headphones, Play, Repeat2, RotateCcw, Sparkles } from 'lucide-react'
import type { WordMark, WordStatus } from '@/api/types'
import { PatternChip, StatusBadge } from '@/components/domain'
import { Button, ProgressBar } from '@/components/ui/primitives'
import { FLAG_META, STATUS_META } from '@/lib/format'

const CHOICES: { status: WordStatus; key: string }[] = [
  { status: 'correct', key: '1' },
  { status: 'misread', key: '2' },
  { status: 'skipped', key: '3' },
  { status: 'unsure', key: '4' },
]

function Signal({ label, value, min, max, hint }: { label: string; value: number | null; min: number; max: number; hint: string }) {
  const norm = value === null ? 0 : (value - min) / (max - min)
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="tabular-nums text-slate-800">{value === null ? 'n/a' : value.toFixed(2)}</span>
      </div>
      <ProgressBar className="mt-1" value={norm} tone={norm > 0.66 ? 'bg-emerald-500' : norm > 0.4 ? 'bg-amber-400' : 'bg-rose-500'} />
      <div className="mt-0.5 text-[11px] text-slate-400">{hint}</div>
    </div>
  )
}

export function WordInspector({
  mark,
  onSet,
  saving,
  canPlay,
  onPlay,
  onContext,
  onCompare,
  comparing = false,
  onAcceptAccent,
  accepting = false,
  onTricky,
  trickySaved = false,
}: {
  mark: WordMark
  onSet: (s: WordStatus | null) => void
  saving: boolean
  canPlay: boolean
  onPlay: () => void
  onContext?: () => void
  onCompare?: () => void
  comparing?: boolean
  onAcceptAccent?: () => void
  accepting?: boolean
  onTricky?: () => void
  trickySaved?: boolean
}) {
  const errors = mark.units.flatMap((u) => u.errors.map((e) => ({ ...e, unit: u })))
  const heard = mark.heard.trim()
  const canAccept = !!onAcceptAccent && !!heard && !heard.includes(' ') && heard !== mark.expected && mark.final_status !== 'correct'
  const hasTime = canPlay && mark.start !== null
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-bn text-4xl font-semibold text-slate-900">{mark.display}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <StatusBadge status={mark.final_status} />
            {mark.teacher_status && <span className="text-xs text-teal-700">set by teacher (system: {STATUS_META[mark.status].label.toLowerCase()})</span>}
          </div>
        </div>
      </div>

      <div>
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Listen before you decide</div>
        {hasTime ? (
          <div className="grid grid-cols-3 gap-2">
            <Button variant="secondary" size="sm" onClick={onPlay} title="Play just this word (space)">
              <Play className="size-4" /> Word
            </Button>
            <Button variant="secondary" size="sm" onClick={onContext} title="Play with the word before and after (C)">
              <Repeat2 className="size-4" /> In context
            </Button>
            <Button variant="secondary" size="sm" onClick={onCompare} loading={comparing} title="The child's word, then the correct pronunciation (V)">
              <Headphones className="size-4" /> Compare
            </Button>
          </div>
        ) : (
          <p className="text-sm text-slate-500">{canPlay ? 'No timing for this word.' : 'The audio was not kept for this reading.'}</p>
        )}
        {hasTime && <p className="mt-1.5 text-[11px] text-slate-400">Compare plays the child, then the correct reading of the word.</p>}
      </div>

      <div>
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Teacher decision</div>
        <div className="grid grid-cols-2 gap-2">
          {CHOICES.map(({ status, key }) => (
            <button
              key={status}
              disabled={saving}
              onClick={() => onSet(status)}
              className={clsx(
                'flex items-center justify-between rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                mark.final_status === status ? 'border-teal-600 bg-teal-50 text-teal-900 ring-1 ring-teal-600' : 'border-slate-200 hover:bg-slate-50',
              )}
            >
              <span className="flex items-center gap-2">
                <span className={clsx('size-2 rounded-full', STATUS_META[status].dot)} />
                {STATUS_META[status].label}
              </span>
              <kbd className="text-xs text-slate-400">{key}</kbd>
            </button>
          ))}
        </div>
        {mark.teacher_status && (
          <button onClick={() => onSet(null)} className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800">
            <RotateCcw className="size-3" /> Reset to system decision
          </button>
        )}
        {(canAccept || onTricky) && (
          <div className="mt-3 flex flex-wrap gap-2">
            {canAccept && (
              <Button variant="secondary" size="sm" loading={accepting} onClick={onAcceptAccent}
                title="The child said it the regional way. Mark correct and accept this pronunciation from now on">
                <Sparkles className="size-4" /> Accept as accent: <span className="font-bn">{heard}</span>
              </Button>
            )}
            {onTricky && (
              <Button variant="ghost" size="sm" disabled={trickySaved} onClick={onTricky}
                title="Names, rare or foreign words: the AI will always leave this word to you">
                <Flag className="size-4" /> {trickySaved ? 'Always left to you' : 'AI unreliable here: always ask me'}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="rounded-lg bg-slate-50 p-3">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Heard vs expected, unit by unit</div>
        <div className="flex flex-wrap gap-1.5">
          {mark.units.map((u, i) => (
            <div
              key={i}
              className={clsx(
                'flex min-w-12 flex-col items-center rounded-md px-2 py-1 ring-1 ring-inset',
                u.op === 'match' || u.op === 'spelling'
                  ? 'bg-white ring-slate-200'
                  : u.op === 'ins'
                    ? 'bg-indigo-50 ring-indigo-200'
                    : 'bg-rose-50 ring-rose-200',
              )}
              title={u.op}
            >
              <span className="font-bn text-xl">{u.expected ?? '·'}</span>
              <span className={clsx('font-bn text-sm', u.op === 'match' ? 'text-slate-400' : 'text-rose-700')}>{u.heard ?? '∅'}</span>
            </div>
          ))}
          {!mark.units.length && <span className="text-sm text-slate-500">No unit detail</span>}
        </div>
        <div className="mt-2 text-sm text-slate-600">
          Heard: <span className="font-bn text-base text-slate-900">{mark.heard || '— (nothing)'}</span>
        </div>
      </div>

      {errors.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Diagnosis</div>
          <ul className="space-y-1.5">
            {errors.map((e, i) => (
              <li key={i} className="text-sm">
                <div className="font-bn text-slate-900">{e.description_bn}</div>
                <div className="text-xs text-slate-500">{e.description_en}</div>
              </li>
            ))}
          </ul>
          {mark.patterns.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {mark.patterns.map((p) => (
                <PatternChip key={p.key} p={p} />
              ))}
            </div>
          )}
        </div>
      )}

      {(mark.note_en || mark.flags.length > 0 || mark.inserted.length > 0) && (
        <div className="space-y-1 text-sm text-slate-600">
          {mark.note_en && (
            <div>
              {mark.note_bn ? (
                <>
                  <span className="font-bn">{mark.note_bn}</span> <span className="text-xs text-slate-400">({mark.note_en})</span>
                </>
              ) : (
                mark.note_en
              )}
            </div>
          )}
          {mark.flags.map((f) => (
            <div key={f} className="text-indigo-700">
              {FLAG_META[f]?.icon} {FLAG_META[f]?.label ?? f}
            </div>
          ))}
          {mark.inserted.length > 0 && (
            <div>
              Also said: <span className="font-bn">{mark.inserted.join(', ')}</span>
            </div>
          )}
        </div>
      )}

      <div className="space-y-3 border-t border-slate-100 pt-4">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Evidence</div>
        <Signal label="Free-decoding confidence" value={mark.free_conf} min={0} max={1} hint="How sure the recogniser was about what it heard" />
        <Signal label="Expected-text score" value={mark.gop} min={-10} max={10} hint="How well the audio fits the passage text here (forced alignment)" />
        {mark.snr_db !== null && mark.snr_db !== undefined && (
          <Signal label="Above background noise (dB)" value={mark.snr_db} min={0} max={30} hint="Below 10 dB the word is not trusted and is left to you" />
        )}
        {mark.start !== null && (
          <div className="text-xs text-slate-500">
            Time: {mark.start.toFixed(2)}s – {mark.end?.toFixed(2)}s
          </div>
        )}
      </div>
    </div>
  )
}
