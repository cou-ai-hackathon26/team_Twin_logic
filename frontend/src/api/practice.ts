import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import { keys } from './hooks'
import type { Assignment, WordCheckResult } from './types'

const k = {
  my: ['my', 'assignments'] as const,
  student: (id: number) => ['assignments', 'student', id] as const,
  classroom: (id: number) => ['assignments', 'class', id] as const,
}

// ------------------------------------------------------------- teacher
export const useStudentAssignments = (sid: number) =>
  useQuery({ queryKey: k.student(sid), queryFn: () => api.get<Assignment[]>(`/students/${sid}/assignments`), enabled: !!sid })

export const useClassAssignments = (cid: number) =>
  useQuery({ queryKey: k.classroom(cid), queryFn: () => api.get<Assignment[]>(`/classrooms/${cid}/assignments`), enabled: !!cid })

export function useAssign() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: { student_ids: number[]; passage_id?: number | null; pattern_key?: string | null; words?: string[]; note?: string }) =>
      api.post<{ created: number; passage: string | null; words: string[] }>('/assignments', b),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assignments'] }),
  })
}

export function useDeleteAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.del(`/assignments/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assignments'] }),
  })
}

export function useDemoReset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ readings_deleted: number; assignments_deleted: number }>('/demo/reset'),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export const useChangePassword = () =>
  useMutation({
    mutationFn: (b: { current_password: string; new_password: string }) => api.post('/auth/password', b),
  })

export const exportClassUrl = (cid: number) => `/api/classrooms/${cid}/export.csv`

// ------------------------------------------------------------- student
export const useMyAssignments = () => useQuery({ queryKey: k.my, queryFn: () => api.get<Assignment[]>('/my/assignments') })

export function useFinishAssignment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.post<Assignment>(`/my/assignments/${id}/done`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: k.my })
      qc.invalidateQueries({ queryKey: keys.myOverview })
    },
  })
}

export const useWordCheck = () =>
  useMutation({
    mutationFn: (b: { word: string; audio: Blob }) => {
      const fd = new FormData()
      fd.append('word', b.word)
      fd.append('audio', b.audio, 'word.wav')
      return api.post<WordCheckResult>('/my/practice/check', fd)
    },
  })

// ------------------------------------------------------------- public
/** Server flags; demo_mode = public test logins, so the UI warns against recording real children. */
export const useHealth = () =>
  useQuery({ queryKey: ['health'], queryFn: () => api.get<{ ok: boolean; demo_mode?: boolean }>('/health'), staleTime: 10 * 60_000 })

// ------------------------------------------------------- learning from reviews
export interface LearningStatus {
  reviewed_readings: number
  decided_words: number
  needs: { readings: number; words: number }
  agreement_now: { precision: number; recall: number; false_alarm: number; unsure_rate: number; words: number } | null
  thresholds: Record<string, number>
  thresholds_source: string
  last_learned: { tuned_at?: string; reviewed_readings?: number; before?: { f1: number }; after?: { f1: number } } | null
  learned_variants: { word: string; variant: string; note: string }[]
  can_undo: boolean
}
export const useLearning = () => useQuery({ queryKey: ['learning'], queryFn: () => api.get<LearningStatus>('/learning') })
export function useLearnNow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ variants_added: unknown[]; thresholds: { changed: boolean; reason?: string } }>('/learning/run'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['learning'] }),
  })
}
export function useUndoLearning() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ undone: boolean }>('/learning/undo'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['learning'] }),
  })
}
