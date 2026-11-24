import { Flag, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useAddTrickyWord, useDeleteTrickyWord, useTrickyWords } from '@/api/hooks'
import { Button, Card, CardHeader, EmptyState, ErrorBox, Input } from '@/components/ui/primitives'

/** Words the AI must never decide alone (names, rare or foreign words). */
export function TrickyWordsCard() {
  const list = useTrickyWords()
  const add = useAddTrickyWord()
  const del = useDeleteTrickyWord()
  const [word, setWord] = useState('')
  return (
    <Card className="xl:col-span-2">
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Flag className="size-4 text-teal-700" /> Words the AI leaves to you
          </span>
        }
        subtitle="Names, rare or foreign words the speech model is unreliable on. A misread here is shown as unsure (⚑), never counted until you decide. Words where teachers corrected the AI in 3 or more reviewed readings are treated the same way automatically."
      />
      <form
        className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-4"
        onSubmit={(e) => {
          e.preventDefault()
          add.mutate(word, { onSuccess: () => setWord('') })
        }}
      >
        <Input className="w-48 font-bn" placeholder="Passage word" value={word} onChange={(e) => setWord(e.target.value)} />
        <Button type="submit" loading={add.isPending} disabled={!word.trim()}>
          <Plus className="size-4" /> Add
        </Button>
        <ErrorBox error={add.error} />
      </form>
      {!list.data?.length ? (
        <EmptyState title="No words yet">Add one here, or press “AI unreliable here” on a word while reviewing.</EmptyState>
      ) : (
        <ul className="divide-y divide-slate-100">
          {list.data.map((t) => (
            <li key={t.id} className="flex items-center justify-between px-5 py-2.5">
              <span className="font-bn text-base">{t.word}</span>
              <Button variant="ghost" size="sm" onClick={() => del.mutate(t.id)} aria-label="Remove">
                <Trash2 className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
