export type Language = 'bn' | 'en'
export type Role = 'teacher' | 'student'

export interface Me {
  id: number
  username: string
  role: Role
  display_name: string
  student: { id: number; code: string; nickname: string | null; classroom_id: number; classroom: string; grade: number } | null
}

export type WordStatus = 'correct' | 'misread' | 'skipped' | 'unsure' | 'not_reached'
export type ReadingStatus = 'queued' | 'processing' | 'done' | 'rejected' | 'failed'

export interface PatternLabel {
  key: string
  category: string
  category_bn: string
  category_en: string
  bn: string
  en: string
  glyph: string
}

export interface PatternStat extends PatternLabel {
  errors: number
  opportunities: number
  error_rate: number | null
  readings_with_error: number
  candidate: boolean
  examples: { reading_id: number; expected: string; heard: string }[]
  last_seen: string | null
}

export interface Metrics {
  total_words: number
  attempted_words: number
  correct: number
  errors: number
  misread: number
  skipped: number
  unsure: number
  not_reached: number
  repetitions: number
  hesitations: number
  reading_time_sec: number | null
  accuracy: number | null
  wcpm: number | null
  /** mark out of 10 */
  score: number | null
}

export interface ReadingSummary {
  id: number
  created_at: string
  status: ReadingStatus
  reviewed: boolean
  passage_id: number
  passage_title: string
  passage_grade: number | null
  language: Language
  score: number | null
  correct: number | null
  total_words: number | null
  wcpm: number | null
  accuracy: number | null
  errors: number | null
  unsure: number | null
  student_id: number
  student_code?: string
  student_nickname?: string | null
  classroom_id?: number
  classroom_name?: string
}

export interface StudentCard {
  id: number
  code: string
  nickname: string | null
  classroom_id: number
  readings: number
  latest: ReadingSummary | null
  candidate_patterns: PatternStat[]
  unreviewed: number
  mean_score: number | null
  username: string | null
}

export interface ClassStats {
  students: number
  assessed: number
  readings: number
  mean_wcpm: number | null
  mean_accuracy: number | null
  mean_score: number | null
  unreviewed: number
}

export interface ClassPattern extends PatternLabel {
  errors: number
  opportunities: number
  students_with_errors: number
  students_candidate: number
  students: string[]
}

export interface ClassroomSummary {
  id: number
  name: string
  grade: number
  school: string | null
  stats: ClassStats
}

export interface ClassroomDetail extends ClassroomSummary {
  students: StudentCard[]
  pattern_map: ClassPattern[]
}

export interface Recommendation {
  pattern: PatternLabel
  passages: { id: number; title: string; grade: number; occurrences: number }[]
  practice_words: string[]
}

export interface StudentDetail extends StudentCard {
  classroom: { id: number; name: string; grade: number }
  history: ReadingSummary[]
  patterns: PatternStat[]
  progress: { reading_id: number; date: string; wcpm: number | null; accuracy: number | null; score: number | null; passage: string; language: Language }[]
  recommendations: Recommendation[]
}

export interface Passage {
  id: number
  code: string | null
  title: string
  grade: number
  language: Language
  text: string
  active: boolean
  created_at: string
  word_count: number
  patterns?: (PatternLabel & { count: number })[]
  words?: { index: number; display: string; norm: string; units: string[] }[]
}

export interface UnitError {
  pattern: string
  kind: 'dropped' | 'substituted' | 'added' | 'split'
  expected: string | null
  heard: string | null
  description_bn: string
  description_en: string
}

export interface UnitResult {
  expected: string | null
  heard: string | null
  op: 'match' | 'sub' | 'del' | 'ins' | 'spelling'
  exp_index: number | null
  free_conf: number | null
  gop: number | null
  errors: UnitError[]
}

export interface WordMark {
  id: number
  index: number
  display: string
  expected: string
  heard: string
  status: WordStatus
  raw_status: WordStatus
  teacher_status: WordStatus | null
  final_status: WordStatus
  flags: string[]
  inserted: string[]
  start: number | null
  end: number | null
  free_conf: number | null
  gop: number | null
  units: UnitResult[]
  patterns: PatternLabel[]
  note_bn: string
  note_en: string
}

export interface QualityReport {
  ok: boolean
  duration_sec: number
  speech_level_db: number
  noise_floor_db: number
  snr_db: number
  clipping_ratio: number
  speech_ratio: number
  warnings: string[]
  reasons: string[]
  message_bn: string
  message_en: string
}

export interface ComparisonSystem {
  transcript?: string
  processing_ms?: number
  model_id?: string
  metrics?: Metrics | null
  marks?: { index: number; status: WordStatus; heard: string }[]
  error?: string
}

export interface Thresholds {
  free_high: number
  gop_high: number
  gop_low: number
  temperature: number
  hesitation_sec: number
  not_reached_min_run: number
  _meta?: Record<string, unknown>
}

export interface Reading {
  id: number
  student_id: number
  passage_id: number
  status: ReadingStatus
  created_at: string
  processed_at: string | null
  error: string | null
  quality: QualityReport | null
  transcript: string | null
  metrics: Metrics | null
  duration_sec: number | null
  processing_ms: number | null
  model_id: string | null
  thresholds: Thresholds | null
  forced_alignment_ok: boolean
  has_audio: boolean
  keep_audio: boolean
  reviewed: boolean
  reviewed_at: string | null
  comparison: { systems?: Record<string, ComparisonSystem>; error?: string } | null
  comparison_status: 'queued' | 'processing' | 'done' | 'failed' | null
  passage: { id: number; title: string; grade: number; language: Language } | null
  language: Language
  score: number | null
  student: { id: number; code: string; nickname: string | null; classroom_id: number } | null
  marks?: WordMark[]
  progress?: ReadingProgress
}

export interface ModelStatus {
  state: 'not_loaded' | 'loading' | 'ready' | 'error'
  error: string | null
  load_sec: number | null
}

export interface SystemInfo {
  models: {
    ctc: ModelStatus & { model_id: string; backend: string }
    whisper: ModelStatus & { model: string; enabled: boolean }
    device: string
  }
  thresholds: Thresholds
  settings: {
    weak_min_errors: number
    weak_min_readings: number
    count_unsure_as_correct: boolean
    database: string
  }
}

export interface Variant {
  id: number
  word: string
  variant: string
  note: string | null
}

export interface AnalyzedUnit {
  text: string
  kind: string
  consonants: string[]
  core: string[]
  phalas: string[]
  reph: boolean
  kar: string | null
  signs: string[]
  hasanta: boolean
  vowel: string | null
  is_conjunct: boolean
  codepoints: string[]
  patterns: PatternLabel[]
}

export interface AnalyzeResult {
  words: { display: string; norm: string; units: AnalyzedUnit[] }[]
}

export interface DiffResult {
  expected: string
  heard: string
  cost: number
  ops: {
    op: string
    expected: string | null
    heard: string | null
    cost: number
    errors: (UnitError & { label: PatternLabel | null })[]
  }[]
}

export interface Proportion {
  k: number
  n: number
  value: number | null
  ci_low: number | null
  ci_high: number | null
}

export interface BenchmarkGroupResult {
  recordings: number
  words: number
  recall: Proportion
  precision: Proportion
  false_alarm: Proportion
  unsure_rate: Proportion
  grapheme_accuracy: Proportion
  uncertainty_coverage: Proportion
  confusion: { tp: number; fp: number; fn: number; tn: number }
  cer: Proportion | null
  wer: Proportion | null
  wcpm_mae?: number
  wcpm_spearman?: number | null
  sec_per_60s?: number
  sec_per_60s_max?: number
}

export interface BenchmarkReport {
  available: boolean
  generated_at?: string
  label?: string
  split?: string
  recordings?: number
  speakers?: string[]
  groups?: string[]
  model?: { ctc: string; ctc_backend: string; whisper: string | null }
  results?: Record<string, Record<string, BenchmarkGroupResult>>
  kappa?: Record<string, number | null>
  targets?: Record<string, { measure: string; target: string; value: number | null; met: boolean | null }[]>
  hypothesis?: { recall_gain_pp: number; precision_not_worse: boolean; supported: boolean } | null
}

export interface MyPassage extends Passage {
  attempted: boolean
  best_score: number | null
}

export interface StudentOverview extends StudentCard {
  classroom: { id: number; name: string; grade: number }
  history: ReadingSummary[]
  best_score: number | null
}

export interface SearchResult {
  students: { id: number; code: string; nickname: string | null; classroom: string; grade: number }[]
  classes: { id: number; name: string; grade: number }[]
  passages: { id: number; title: string; grade: number; language: Language }[]
}

export interface PracticeWord {
  word: string
  expected: string
  heard: string
  status: 'misread' | 'skipped'
  count: number
  language: Language
  reading_id: number
  passage_title: string
  date: string
  clip: { start: number; end: number } | null
  patterns: PatternLabel[]
}

export type ProgressStage = 'queued' | 'loading' | 'quality' | 'listening' | 'aligning' | 'diagnosing'

/** Live processing state, present while a reading is queued or processing. */
export interface ReadingProgress {
  stage: ProgressStage
  elapsed_sec: number
  stage_elapsed_sec: number
  estimated_sec: number
  audio_sec: number | null
}
