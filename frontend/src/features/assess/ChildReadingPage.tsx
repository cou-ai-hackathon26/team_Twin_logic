import { ClipboardCheck } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { usePassage, useStudent, useUploadReading } from '@/api/hooks'
import { Button, ErrorBox, PageLoader } from '@/components/ui/primitives'
import { ReadingSession } from './ReadingSession'

/** Teacher-run assessment: the teacher picks the child and hands over the device. */
export function ChildReadingPage() {
  const { studentId, passageId } = useParams()
  const sid = Number(studentId)
  const pid = Number(passageId)
  const student = useStudent(sid)
  const passage = usePassage(pid)
  const upload = useUploadReading()
  const nav = useNavigate()

  if (passage.isLoading || student.isLoading) return <PageLoader />
  if (!passage.data || !student.data) return <ErrorBox error={passage.error || student.error || 'Not found'} />

  return (
    <ReadingSession
      passage={passage.data}
      asStudent={false}
      backTo={`/assess?student=${sid}`}
      who={
        <>
          {student.data.code}
          {student.data.nickname && ` · ${student.data.nickname}`}
        </>
      }
      upload={(wav) => upload.mutateAsync({ studentId: sid, passageId: pid, audio: wav, filename: 'reading.wav' })}
      doneActions={(rid) => (
        <Button size="lg" variant="secondary" onClick={() => nav(`/readings/${rid}`)}>
          <ClipboardCheck className="size-5" /> Teacher: review the marks
        </Button>
      )}
    />
  )
}
