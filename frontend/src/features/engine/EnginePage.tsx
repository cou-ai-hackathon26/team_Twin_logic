import clsx from 'clsx'
import { ArrowRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { analyzeText, diffWords } from '@/api/hooks'
import type { AnalyzeResult, AnalyzedUnit, DiffResult } from '@/api/types'
import { PatternChip } from '@/components/domain'
import { Badge, Button, Card, CardHeader, ErrorBox, Input, Label, PageHeader, Textarea } from '@/components/ui/primitives'

const EXAMPLES: [string, string][] = [
  ['প্রথম', 'পথম'],
  ['শিক্ষক', 'শিকক'],
  ['স্বাগত', 'সাগত'],
  ['কার্য', 'কাজ'],
  ['চাঁদ', 'চাদ'],
  ['সকাল', 'শকাল'],
]

function UnitCard({ u }: { u: AnalyzedUnit }) {
  const parts: [string, string | null][] = [
    ['reph', u.reph ? 'র্' : null],
    ['core', u.core.length ? u.core.join(' + ') : u.vowel],
    ['phala', u.phalas.length ? u.phalas.map((p) => `্${p}`).join(' ') : null],
    ['kar', u.kar ? `◌${u.kar}` : null],
    ['signs', u.signs.length ? u.signs.map((s) => `◌${s}`).join(' ') : null],
  ]
  return (
    <div className="w-44 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between">
        <span className="font-bn text-4xl">{u.text}</span>
        <div className="flex flex-col items-end gap-1">
          {u.is_conjunct && <Badge className="bg-violet-50 text-violet-800 ring-violet-200">conjunct</Badge>}
          {u.kind !== 'consonant' && <Badge>{u.kind}</Badge>}
        </div>
      </div>
      <dl className="mt-2 space-y-0.5 text-xs">
        {parts
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <dt className="text-slate-500">{k}</dt>
              <dd className="font-bn text-sm text-slate-900">{v}</dd>
            </div>
          ))}
      </dl>
      <div className="mt-2 truncate font-mono text-[10px] text-slate-400" title={u.codepoints.join(' ')}>
        {u.codepoints.join(' ')}
      </div>
    </div>
  )
}

export function EnginePage() {
  const [text, setText] = useState('ক্ষেত্রে প্রথম স্বাধীনতা চাঁদ কার্য')
  const [res, setRes] = useState<AnalyzeResult | null>(null)
  const [exp, setExp] = useState('প্রথম')
  const [heard, setHeard] = useState('পথম')
  const [diff, setDiff] = useState<DiffResult | null>(null)
  const [err, setErr] = useState<unknown>(null)

  const runAnalyze = (t = text) => analyzeText(t).then(setRes, setErr)
  const runDiff = (e = exp, h = heard) => diffWords(e, h).then(setDiff, setErr)
  useEffect(() => {
    void runAnalyze()
    void runDiff()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <>
      <PageHeader
        title="Bangla grapheme engine"
        subtitle="The team-built normaliser, segmenter and aligner that turn a wrong word into a teachable unit."
      />
      <ErrorBox error={err} className="mb-4" />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Diagnose a misreading" subtitle="Expected word vs what was heard. Spelling-only differences (same sound) are not errors." />
          <div className="space-y-4 p-5">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <Label>Expected</Label>
                <Input className="w-48 font-bn text-lg" value={exp} onChange={(e) => setExp(e.target.value)} />
              </div>
              <ArrowRight className="mb-2.5 size-5 text-slate-400" />
              <div>
                <Label>Heard</Label>
                <Input className="w-48 font-bn text-lg" value={heard} onChange={(e) => setHeard(e.target.value)} />
              </div>
              <Button onClick={() => runDiff()}>Diagnose</Button>
              <div className="flex flex-wrap gap-1">
                {EXAMPLES.map(([a, b]) => (
                  <button
                    key={a + b}
                    onClick={() => (setExp(a), setHeard(b), void runDiff(a, b))}
                    className="rounded-md bg-slate-100 px-2 py-1 font-bn text-sm text-slate-700 hover:bg-slate-200"
                  >
                    {a}→{b}
                  </button>
                ))}
              </div>
            </div>
            {diff && (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {diff.ops.map((o, i) => (
                    <div
                      key={i}
                      className={clsx(
                        'flex min-w-16 flex-col items-center rounded-lg px-3 py-2 ring-1 ring-inset',
                        o.op === 'match' ? 'bg-white ring-slate-200' : o.op === 'spelling' ? 'bg-sky-50 ring-sky-200' : 'bg-rose-50 ring-rose-200',
                      )}
                    >
                      <span className="font-bn text-2xl">{o.expected ?? '·'}</span>
                      <span className="font-bn text-base text-rose-700">{o.heard ?? '∅'}</span>
                      <span className="mt-1 text-[10px] uppercase text-slate-400">{o.op}</span>
                    </div>
                  ))}
                </div>
                <ul className="space-y-1">
                  {diff.ops.flatMap((o) => o.errors).map((e, i) => (
                    <li key={i} className="flex flex-wrap items-center gap-2 text-sm">
                      {e.label && <PatternChip p={e.label} strong />}
                      <span className="font-bn">{e.description_bn}</span>
                      <span className="text-slate-500">· {e.description_en}</span>
                    </li>
                  ))}
                  {!diff.ops.some((o) => o.errors.length) && (
                    <li className="text-sm text-emerald-700">No reading error: the words are the same or differ only in letters that sound the same.</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Segment text into units" subtitle="Unicode normalisation, then orthographic units: base, conjunct core, রেফ, ফলা, কার and signs." />
          <div className="space-y-4 p-5">
            <div className="flex gap-3">
              <Textarea className="font-bn text-lg" rows={2} value={text} onChange={(e) => setText(e.target.value)} />
              <Button className="self-start" onClick={() => runAnalyze()}>
                Analyse
              </Button>
            </div>
            {res?.words.map((w, i) => (
              <div key={i}>
                <div className="mb-2 font-bn text-lg font-semibold text-slate-800">{w.display}</div>
                <div className="flex flex-wrap gap-3">
                  {w.units.map((u, j) => (
                    <UnitCard key={j} u={u} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  )
}
