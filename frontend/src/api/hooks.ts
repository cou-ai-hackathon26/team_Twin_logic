import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from './client'
import type {
  AnalyzeResult,
  Language,
  Me,
  MyPassage,
  StudentOverview,
  BenchmarkReport,
  ClassroomDetail,
  ClassroomSummary,
  DiffResult,
  Passage,
  PracticeWord,
  SearchResult,
  Reading,
  ReadingSummary,
  StudentCard,
  StudentDetail,
  SystemInfo,
  Variant,
  WordStatus,
} from './types'

export const keys = {
  me: ['me'] as const,
  myOverview: ['my', 'overview'] as const,
  myPassages: ['my', 'passages'] as const,
  myPassage: (id: number) => ['my', 'passage', id] as const,
  myReading: (id: number) => ['my', 'reading', id] as const,
  classrooms: ['classrooms'] as const,
  classroom: (id: number) => ['classroom', id] as const,
  student: (id: number) => ['student', id] as const,
  passages: (all = false) => ['passages', all] as const,
  passage: (id: number) => ['passage', id] as const,
  reading: (id: number) => ['reading', id] as const,
  readings: ['readings'] as const,
  system: ['system'] as const,
  variants: ['variants'] as const,
  tricky: ['tricky-words'] as const,
  benchmark: ['benchmark'] as const,
}

// ------------------------------------------------------------------- auth
/** The logged-in user, or null when nobody is logged in. */
export const useMe = () =>
  useQuery({
    queryKey: keys.me,
    staleTime: 5 * 60_000,
    queryFn: async () => {
      try {
        return await api.get<Me>('/auth/me')
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
  })

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: { username: string; password: string; role: 'teacher' | 'student' }) => api.post<Me>('/auth/login', b),
    onSuccess: (me) => {
      qc.clear()
      qc.setQueryData(keys.me, me)
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/auth/logout'),
    onSettled: () => {
      qc.clear()
      qc.setQueryData(keys.me, null)
    },
  })
}

export function useSetStudentAccount(studentId: number) {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { username: string; password: string }) => api.put<StudentCard>(`/students/${studentId}/account`, b),
    onSuccess: (s) => inv([...keys.student(studentId)], [...keys.classroom(s.classroom_id)]),
  })
}

export function useDeleteStudentAccount(studentId: number) {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: () => api.del(`/students/${studentId}/account`),
    onSuccess: () => inv([...keys.student(studentId)], ['classroom']),
  })
}

// --------------------------------------------------------- student area
export const useMyOverview = () =>
  useQuery({ queryKey: keys.myOverview, queryFn: () => api.get<StudentOverview>('/my/overview') })

export const useMyPassages = () => useQuery({ queryKey: keys.myPassages, queryFn: () => api.get<MyPassage[]>('/my/passages') })

export const useMyPassage = (id: number) =>
  useQuery({ queryKey: keys.myPassage(id), queryFn: () => api.get<Passage>(`/my/passages/${id}`), enabled: !!id })

export function useUploadMyReading() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { passageId: number; audio: Blob; filename: string }) => {
      const fd = new FormData()
      fd.append('passage_id', String(b.passageId))
      fd.append('audio', b.audio, b.filename)
      return api.post<Reading>('/my/readings', fd)
    },
    onSuccess: () => inv([...keys.myOverview], [...keys.myPassages]),
  })
}

// ---------------------------------------------------------------- queries
export const useClassrooms = () =>
  useQuery({ queryKey: keys.classrooms, queryFn: () => api.get<ClassroomSummary[]>('/classrooms') })

export const useClassroom = (id: number) =>
  useQuery({ queryKey: keys.classroom(id), queryFn: () => api.get<ClassroomDetail>(`/classrooms/${id}`) })

export const useStudent = (id: number) =>
  useQuery({ queryKey: keys.student(id), queryFn: () => api.get<StudentDetail>(`/students/${id}`) })

export const usePassages = (includeInactive = false) =>
  useQuery({
    queryKey: keys.passages(includeInactive),
    queryFn: () => api.get<Passage[]>(`/passages${includeInactive ? '?include_inactive=true' : ''}`),
  })

export const usePassage = (id: number | null) =>
  useQuery({
    queryKey: keys.passage(id ?? 0),
    queryFn: () => api.get<Passage>(`/passages/${id}`),
    enabled: !!id,
  })

export const useRecentReadings = () =>
  useQuery({ queryKey: keys.readings, queryFn: () => api.get<ReadingSummary[]>('/readings?limit=12') })

/** Polls while the reading or its comparison is still being processed.
 *  ``asStudent`` reads it through the student's own endpoint. */
export const useReading = (id: number, asStudent = false) =>
  useQuery({
    queryKey: asStudent ? keys.myReading(id) : keys.reading(id),
    queryFn: () => api.get<Reading>(asStudent ? `/my/readings/${id}` : `/readings/${id}`),
    refetchInterval: (q) => {
      const r = q.state.data
      if (!r) return false
      const busy =
        r.status === 'queued' ||
        r.status === 'processing' ||
        r.comparison_status === 'queued' ||
        r.comparison_status === 'processing'
      return busy ? 1500 : false
    },
  })

export const useSystem = (poll = false) =>
  useQuery({
    queryKey: keys.system,
    queryFn: () => api.get<SystemInfo>('/system'),
    refetchInterval: (q) => {
      const s = q.state.data
      if (poll) return 3000
      return s && (s.models.ctc.state === 'loading' || s.models.whisper.state === 'loading') ? 2000 : false
    },
  })

export const useVariants = () => useQuery({ queryKey: keys.variants, queryFn: () => api.get<Variant[]>('/variants') })

export const useBenchmark = () =>
  useQuery({ queryKey: keys.benchmark, queryFn: () => api.get<BenchmarkReport>('/benchmark') })

// -------------------------------------------------------------- mutations
function useInvalidate() {
  const qc = useQueryClient()
  return (...k: readonly unknown[][]) => Promise.all(k.map((queryKey) => qc.invalidateQueries({ queryKey })))
}

export function useCreateClassroom() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { name: string; grade: number; school?: string | null }) =>
      api.post<ClassroomDetail>('/classrooms', b),
    onSuccess: () => inv([...keys.classrooms]),
  })
}

export function useDeleteClassroom() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (id: number) => api.del(`/classrooms/${id}`),
    onSuccess: () => inv([...keys.classrooms]),
  })
}

export function useAddStudent(classroomId: number) {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { code: string; nickname?: string | null }) =>
      api.post<StudentCard>(`/classrooms/${classroomId}/students`, b),
    onSuccess: () => inv([...keys.classroom(classroomId)], [...keys.classrooms]),
  })
}

export function useAddStudentsBulk(classroomId: number) {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { count: number; prefix: string; start: number }) =>
      api.post<{ added: number }>(`/classrooms/${classroomId}/students/bulk`, b),
    onSuccess: () => inv([...keys.classroom(classroomId)], [...keys.classrooms]),
  })
}

export function useUpdateStudent(id: number) {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { code?: string; nickname?: string | null; active?: boolean }) =>
      api.patch<StudentCard>(`/students/${id}`, b),
    onSuccess: (s) => inv([...keys.student(id)], [...keys.classroom(s.classroom_id)]),
  })
}

export function useDeleteStudent() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (s: { id: number; classroom_id: number }) => api.del(`/students/${s.id}`),
    onSuccess: (_d, s) => inv([...keys.classroom(s.classroom_id)], [...keys.classrooms]),
  })
}

export function useSavePassage() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (p: { id?: number; title: string; grade: number; text: string; language?: Language }) =>
      p.id
        ? api.patch<Passage>(`/passages/${p.id}`, { title: p.title, grade: p.grade, text: p.text })
        : api.post<Passage>('/passages', p),
    onSuccess: () => inv(['passages'], ['passage']),
  })
}

export function useDeletePassage() {
  const inv = useInvalidate()
  return useMutation({ mutationFn: (id: number) => api.del(`/passages/${id}`), onSuccess: () => inv(['passages']) })
}

export function useUploadReading() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { studentId: number; passageId: number; audio: Blob; filename: string }) => {
      const fd = new FormData()
      fd.append('student_id', String(b.studentId))
      fd.append('passage_id', String(b.passageId))
      fd.append('audio', b.audio, b.filename)
      return api.post<Reading>('/readings', fd)
    },
    onSuccess: () => inv([...keys.readings]),
  })
}

function useReadingMutation<V>(fn: (v: V) => Promise<Reading>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      qc.setQueryData(keys.reading(r.id), (old: Reading | undefined) => ({ ...old, ...r }))
      qc.invalidateQueries({ queryKey: keys.student(r.student_id) })
      if (r.student) qc.invalidateQueries({ queryKey: keys.classroom(r.student.classroom_id) })
      qc.invalidateQueries({ queryKey: keys.readings })
    },
  })
}

export const useSetMark = (readingId: number) =>
  useReadingMutation((v: { index: number; status: WordStatus | null }) =>
    api.patch<Reading>(`/readings/${readingId}/marks/${v.index}`, { teacher_status: v.status }),
  )

/** The child said the word in their regional way: accept that pronunciation and mark it correct. */
export const useAcceptAccent = (readingId: number) =>
  useReadingMutation((index: number) => api.post<Reading>(`/readings/${readingId}/marks/${index}/accept-accent`))

export interface TrickyWord {
  id: number
  word: string
  note: string | null
}
export const useTrickyWords = () => useQuery({ queryKey: keys.tricky, queryFn: () => api.get<TrickyWord[]>('/tricky-words') })

/** Tell PoraBondhu it is unreliable on a word (a name, a rare word): always left to the teacher. */
export function useAddTrickyWord() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (word: string) => api.post<TrickyWord>('/tricky-words', { word }),
    onSuccess: () => inv([...keys.tricky]),
  })
}

export function useDeleteTrickyWord() {
  const inv = useInvalidate()
  return useMutation({ mutationFn: (id: number) => api.del(`/tricky-words/${id}`), onSuccess: () => inv([...keys.tricky]) })
}

export const useFinalize = (readingId: number) =>
  useReadingMutation((keepAudio: boolean) =>
    api.post<Reading>(`/readings/${readingId}/finalize`, { keep_audio: keepAudio }),
  )

export const useCompare = (readingId: number) =>
  useReadingMutation(() => api.post<Reading>(`/readings/${readingId}/compare`))

export const useReprocess = (readingId: number) =>
  useReadingMutation(() => api.post<Reading>(`/readings/${readingId}/reprocess`))

export function useDeleteReading() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (r: { id: number; student_id: number }) => api.del(`/readings/${r.id}`),
    onSuccess: (_d, r) => inv([...keys.student(r.student_id)], [...keys.readings], ['classroom']),
  })
}

export function useWarmup() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (includeWhisper: boolean) => api.post(`/system/warmup?include_whisper=${includeWhisper}`),
    onSettled: () => inv([...keys.system]),
  })
}

export function useAddVariant() {
  const inv = useInvalidate()
  return useMutation({
    mutationFn: (b: { word: string; variant: string; note?: string }) => api.post<Variant>('/variants', b),
    onSuccess: () => inv([...keys.variants]),
  })
}

export function useDeleteVariant() {
  const inv = useInvalidate()
  return useMutation({ mutationFn: (id: number) => api.del(`/variants/${id}`), onSuccess: () => inv([...keys.variants]) })
}

export const analyzeText = (text: string) => api.post<AnalyzeResult>('/bangla/analyze', { text })
export const diffWords = (expected: string, heard: string) => api.post<DiffResult>('/bangla/diff', { expected, heard })

// ------------------------------------------------------------ navigation helpers
/** Every finished reading still waiting for the teacher's check (newest first). */
export const useReviewQueue = () =>
  useQuery({
    queryKey: [...keys.readings, 'queue'],
    queryFn: () => api.get<ReadingSummary[]>('/readings?reviewed=false&status=done&limit=300'),
    refetchInterval: 30_000,
  })

export const useSearch = (q: string) =>
  useQuery({
    queryKey: ['search', q],
    queryFn: () => api.get<SearchResult>(`/search?q=${encodeURIComponent(q)}`),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })

export const useMyPractice = () => useQuery({ queryKey: ['my', 'practice'], queryFn: () => api.get<PracticeWord[]>('/my/practice') })
