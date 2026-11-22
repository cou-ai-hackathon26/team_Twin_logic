import { Archive, Pencil, Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useDeletePassage, usePassages, useSavePassage } from '@/api/hooks'
import type { Language, Passage } from '@/api/types'
import { GradeBadge, LanguageBadge, PatternChip } from '@/components/domain'
import { langFont } from '@/lib/format'
import { Button, Card, ErrorBox, Input, Label, Modal, PageHeader, PageLoader, Select, Textarea } from '@/components/ui/primitives'

function PassageEditor({ passage, onClose }: { passage: Partial<Passage> | null; onClose: () => void }) {
  const save = useSavePassage()
  const [title, setTitle] = useState(passage?.title ?? '')
  const [grade, setGrade] = useState(passage?.grade ?? 2)
  const [text, setText] = useState(passage?.text ?? '')
  const [language, setLanguage] = useState<Language>(passage?.language ?? 'bn')
  return (
    <Modal
      open
      wide
      onClose={onClose}
      title={passage?.id ? 'Edit passage' : 'New passage'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={save.isPending}
            disabled={!title.trim() || !text.trim()}
            onClick={() => save.mutate({ id: passage?.id, title, grade, text, language }, { onSuccess: onClose })}
          >
            Save passage
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-[1fr_auto_auto] gap-3">
          <div>
            <Label>Title</Label>
            <Input className={langFont(language)} value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <Label>Language</Label>
            <Select value={language} disabled={!!passage?.id} onChange={(e) => setLanguage(e.target.value as Language)} title={passage?.id ? 'Language is fixed once a passage exists' : undefined}>
              <option value="bn">Bangla</option>
              <option value="en">English</option>
            </Select>
          </div>
          <div>
            <Label>Grade</Label>
            <Select value={grade} onChange={(e) => setGrade(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <div>
          <Label>Text</Label>
          <Textarea className={`text-lg leading-relaxed ${langFont(language)}`} rows={7} value={text} onChange={(e) => setText(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">
            {text.split(/\s+/).filter(Boolean).length} words. Short passages (40-80 words) take about a minute to read. Editing a passage never changes
            old results: each reading keeps a copy of the text it was marked against.
          </p>
        </div>
        <ErrorBox error={save.error} />
      </div>
    </Modal>
  )
}

export function PassagesPage() {
  const { data, isLoading, error } = usePassages()
  const archive = useDeletePassage()
  const [editing, setEditing] = useState<Partial<Passage> | null | undefined>(undefined)
  const [grade, setGrade] = useState<number | 'all'>('all')
  const [lang, setLang] = useState<Language | 'all'>('all')
  const shown = useMemo(
    () => (data ?? []).filter((p) => (grade === 'all' || p.grade === grade) && (lang === 'all' || p.language === lang)),
    [data, grade, lang],
  )

  return (
    <>
      <PageHeader
        title="Passage bank"
        subtitle="Graded Bangla and English passages for every class. Chips show which conjuncts, ফলা and কার a Bangla passage practises."
        actions={
          <>
            <Select className="w-36" value={lang} onChange={(e) => setLang(e.target.value as Language | 'all')}>
              <option value="all">All languages</option>
              <option value="bn">Bangla</option>
              <option value="en">English</option>
            </Select>
            <Select className="w-36" value={grade} onChange={(e) => setGrade(e.target.value === 'all' ? 'all' : Number(e.target.value))}>
              <option value="all">All grades</option>
              {[1, 2, 3, 4, 5].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </Select>
            <Button onClick={() => setEditing(null)}>
              <Plus className="size-4" /> New passage
            </Button>
          </>
        }
      />
      {editing !== undefined && <PassageEditor passage={editing} onClose={() => setEditing(undefined)} />}
      <ErrorBox error={error || archive.error} />
      {isLoading ? (
        <PageLoader />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {shown.map((p) => (
            <Card key={p.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-semibold ${langFont(p.language)}`}>{p.title}</span>
                  <GradeBadge grade={p.grade} />
                  <LanguageBadge language={p.language} />
                  {p.code && <span className="text-xs text-slate-400">{p.code}</span>}
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(p)} aria-label="Edit">
                    <Pencil className="size-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => archive.mutate(p.id)} aria-label="Archive" title="Archive (kept if already used)">
                    <Archive className="size-4" />
                  </Button>
                </div>
              </div>
              <p className={`mt-3 flex-1 text-base leading-relaxed text-slate-700 ${langFont(p.language)}`}>{p.text}</p>
              <div className="mt-4 flex flex-wrap gap-1">
                {p.patterns?.slice(0, 10).map((pt) => (
                  <PatternChip key={pt.key} p={pt} count={pt.count} />
                ))}
              </div>
              <div className="mt-2 text-xs text-slate-500">{p.word_count} words</div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
