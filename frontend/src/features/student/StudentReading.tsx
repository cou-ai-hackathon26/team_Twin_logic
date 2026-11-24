import clsx from 'clsx'
import { ArrowLeft, Bot, Ear, Hourglass, ListChecks, Loader2, Mic, RotateCcw, Volume2 } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMe, useMyPassage, useReading, useUploadMyReading } from '@/api/hooks'
import { ListenAlong, MyVoicePlayer, useMyVoice, useSayWord } from '@/components/audio'
import { LanguageBadge, MarkBadge } from '@/components/domain'
import { Button, Card, CardHeader, EmptyState, ErrorBox, PageHeader, PageLoader, Stat } from '@/components/ui/primitives'
import { ProcessingProgress } from '@/features/assess/ProcessingProgress'
import { dateTime, langFont, STATUS_META } from '@/lib/format'
import { ReadingSession } from '../assess/ReadingSession'
import { buddyLine, ReadingBuddy } from '@/components/ReadingBuddy'
import { Legend, MarkedPassage } from '../review/MarkedPassage'

/** A student takes a reading test on their own. */
export function StudentReadingPage() {
  const pid = Number(useParams().passageId)
  const { data: me } = useMe()
  const passage = useMyPassage(pid)
  const upload = useUploadMyReading()
  const nav = useNavigate()

  if (passage.isLoading) return <PageLoader />
  if (!passage.data) return <ErrorBox className="m-6" error={passage.error || 'Passage not found'} />

  return (
    <ReadingSession
      passage={passage.data}
      asStudent
      backTo="/me"
      who={me?.student?.code}
      upload={(wav) => upload.mutateAsync({ passageId: pid, audio: wav, filename: 'reading.wav' })}
      doneActions={(rid) => (
        <>
          <Button size="lg" onClick={() => nav(`/me/readings/${rid}`)}>
            <ListChecks className="size-5" /> See my result
          </Button>
          <Button size="lg" variant="secondary" onClick={() => nav('/me')}>
            Back to my tests
          </Button>
        </>
      )}
    />
  )
}

/** A student's own result: mark out of 10 and which words to practise, once the teacher has checked it. */
export function StudentResultPage() {
  const id = Number(useParams().id)
  const { data: r, isLoading, error } = useReading(id, true)
  const myAudio = `/api/my/readings/${id}/audio`
  const { say, busy } = useSayWord(r?.language ?? 'bn')
  const { playClip } = useMyVoice(myAudio)

  if (isLoading) return <PageLoader />
  if (error || !r) return <ErrorBox error={error ?? 'Result not found'} />
  const lang = r.language
  const back = (
    <Link to="/me" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
      <ArrowLeft className="size-4" /> My tests
    </Link>
  )
  const title = (
    <span className="flex flex-wrap items-center gap-3">
      <span className={langFont(lang)}>{r.passage?.title}</span> <LanguageBadge language={lang} />
    </span>
  )

  if (r.status === 'queued' || r.status === 'processing')
    return (
      <>
        <PageHeader back={back} title={title} />
        <Card>
          <div className="flex justify-center px-4 py-10">
            <ProcessingProgress progress={r.progress} language={r.language} child />
          </div>
        </Card>
      </>
    )
  if (r.status !== 'done')
    return (
      <>
        <PageHeader back={back} title={title} />
        <Card className="p-6">
          <p className="font-medium text-slate-900">{r.status === 'rejected' ? 'The recording was not clear enough to mark.' : 'This test could not be marked.'}</p>
          {r.quality && <p className="mt-1 text-sm text-slate-600">{r.quality.message_en}</p>}
          <Link to={`/me/read/${r.passage_id}`} className="mt-4 inline-block">
            <Button>
              <RotateCcw className="size-4" /> Read again
            </Button>
          </Link>
        </Card>
      </>
    )

  const m = r.metrics
  const marks = r.marks ?? []
  const practise = marks.filter((w) => w.final_status === 'misread' || w.final_status === 'skipped')
  const passageText = marks.map((w) => w.display).join(' ')

  return (
    <>
      <PageHeader
        back={back}
        title={title}
        subtitle={`${dateTime(r.created_at)} · ${r.pending_review ? 'AI result · waiting for your teacher to check' : 'checked by your teacher'}`}
        actions={
          <Link to={`/me/read/${r.passage_id}`}>
            <Button variant="secondary">
              <Mic className="size-4" /> Try again
            </Button>
          </Link>
        }
      />
      <ReadingBuddy size={88} {...buddyLine(r.score)} className="mb-4" />
      {r.pending_review && (
        <Card className="mb-6 overflow-hidden">
          <div className="flex items-start gap-4 bg-marigold-50 px-5 py-4">
            <div className="grid size-12 shrink-0 place-items-center rounded-full bg-white shadow ring-1 ring-amber-200">
              <Bot className="size-6 text-amber-600" />
            </div>
            <div>
              <p className="font-bn text-lg font-semibold text-ink">এটি AI-এর ফলাফল। শিক্ষক এখন তোমার পড়া শুনে যাচাই করবেন।</p>
              <p className="mt-0.5 text-sm text-slate-600">
                This is the AI's result. It has also gone to your teacher for review, so your mark may change after your teacher checks it.
              </p>
            </div>
            <Hourglass className="ml-auto hidden size-5 shrink-0 text-amber-600 sm:block" />
          </div>
        </Card>
      )}
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card className="flex flex-col items-center justify-center gap-1 p-4">
          <span className="text-xs font-medium tracking-wide text-slate-500 uppercase">{r.pending_review ? 'AI mark' : 'Mark'}</span>
          <MarkBadge score={r.score} size="lg" />
        </Card>
        <Stat label="Words correct" value={m ? `${m.correct}/${m.total_words}` : '—'} />
        <Stat label="Words to practise" value={practise.length} tone={practise.length ? 'text-rose-700' : 'text-emerald-700'} />
        <Stat label="Not reached" value={m?.not_reached ?? 0} hint="words after you stopped" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <Ear className="size-4 text-teal-700" /> How you read
                </span>
              }
              subtitle={r.has_audio ? 'Play your recording, or tap a word to hear how you said it' : 'Coloured words need more practice'}
            />
            <div className="px-5 py-6">
              {r.has_audio ? (
                <MyVoicePlayer src={myAudio} marks={marks} language={lang} />
              ) : (
                <MarkedPassage marks={marks} selected={null} onSelect={() => {}} language={lang} />
              )}
            </div>
            <div className="border-t border-slate-100 px-5 py-3">
              <Legend />
            </div>
          </Card>
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <Volume2 className="size-4 text-teal-700" /> Hear the correct reading
                </span>
              }
              subtitle="Listen and follow the words. Then compare with your own reading above."
            />
            <div className="px-5 py-6">
              <ListenAlong compact text={passageText} language={lang} textClassName={clsx('text-2xl leading-[2.2] text-slate-900', langFont(lang))} />
            </div>
          </Card>
        </div>
        <Card className="h-fit">
          <CardHeader title="Practise these words" subtitle={practise.length ? 'Hear it said correctly, then hear yourself' : undefined} />
          {!practise.length ? (
            <EmptyState title="Every word was right. Great job!" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {practise.map((w) => (
                <li key={w.index} className="px-5 py-3.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className={clsx('text-2xl font-semibold text-ink', langFont(lang))}>{w.display}</span>
                    <span className="text-right text-sm text-slate-500">
                      {w.final_status === 'skipped' ? (
                        STATUS_META.skipped.label
                      ) : (
                        <>
                          you said <span className={clsx('text-rose-700', langFont(lang))}>{w.heard || '—'}</span>
                        </>
                      )}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => void say(w.display)}
                      className="inline-flex h-9 items-center gap-1.5 rounded-full bg-teal-700 px-3.5 text-sm font-semibold text-white hover:bg-teal-800"
                    >
                      {busy === w.display ? <Loader2 className="size-4 animate-spin" /> : <Volume2 className="size-4" />} Correct
                    </button>
                    {r.has_audio && w.start !== null && w.end !== null && (
                      <button
                        type="button"
                        onClick={() => void playClip(w.start as number, w.end as number)}
                        className="inline-flex h-9 items-center gap-1.5 rounded-full bg-white px-3.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-200 hover:ring-teal-300"
                      >
                        <Ear className="size-4" /> Me
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
