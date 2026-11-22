import clsx from 'clsx'
import { Ear, Loader2, Pause, Play, RotateCcw, Snail, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { Language, WordMark } from '@/api/types'
import { langFont } from '@/lib/format'

/* ----------------------------------------------------------------- TTS data */

interface SpeechWord {
  text: string
  start: number
  end: number
}
interface Speech {
  url: string
  words: SpeechWord[]
}

const speechCache = new Map<string, Promise<Speech>>()

/** Model reading of `text` (cached per text/lang/speed, here and on the server). */
function fetchSpeech(text: string, lang: Language, slow: boolean): Promise<Speech> {
  const k = `${lang}|${slow ? 1 : 0}|${text}`
  let p = speechCache.get(k)
  if (!p) {
    p = api.post<Speech>('/tts', { text, lang, slow })
    p.catch(() => speechCache.delete(k))
    speechCache.set(k, p)
  }
  return p
}

const clean = (s: string) => s.replace(/[\s\p{P}\p{S}]/gu, '').toLowerCase()

/** Map each passage token to its spoken word timing (in order, tolerant of punctuation and numbers). */
function alignTokens(tokens: string[], words: SpeechWord[]): (SpeechWord | null)[] {
  const out: (SpeechWord | null)[] = tokens.map(() => null)
  let j = 0
  for (let i = 0; i < tokens.length && j < words.length; i++) {
    const t = clean(tokens[i])
    if (!t) continue
    // look a few words ahead for an exact match; otherwise take the next word
    let hit = -1
    for (let k = j; k < Math.min(words.length, j + 4); k++)
      if (clean(words[k].text) === t) {
        hit = k
        break
      }
    const use = hit >= 0 ? hit : j
    out[i] = words[use]
    j = use + 1
  }
  return out
}

/** Browser voice fallback when the model reading can't be generated (offline, first play). */
function browserVoice(lang: Language): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null
  const prefix = lang === 'bn' ? 'bn' : 'en'
  return window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(prefix)) ?? null
}

let sharedAudio: HTMLAudioElement | null = null
/** Only one sound at a time across the page. */
function claimAudio(): HTMLAudioElement {
  sharedAudio?.pause()
  sharedAudio = new Audio()
  return sharedAudio
}

/* --------------------------------------------------- listen to the passage */

const LABELS = {
  bn: { listen: 'শুনে নাও', pause: 'থামাও', slow: 'ধীরে', tip: 'যেকোনো শব্দে চাপ দিলে সেখান থেকে শোনা যাবে' },
  en: { listen: 'Listen first', pause: 'Pause', slow: 'Slow', tip: 'Tap any word to hear it from there' },
}

/**
 * The passage text with a "listen" bar: plays a model reading and highlights each word
 * as it is spoken (karaoke style). Tap a word to start from it.
 */
export function ListenAlong({
  text,
  language,
  disabled,
  textClassName,
  compact,
}: {
  text: string
  language: Language
  /** e.g. while recording: stop and hide controls so the mic doesn't hear it */
  disabled?: boolean
  textClassName?: string
  compact?: boolean
}) {
  const tokens = useMemo(() => text.split(/(\s+)/), [text])
  const words = useMemo(() => tokens.filter((t) => !/^\s+$/.test(t) && t !== ''), [tokens])
  const [slow, setSlow] = useState(false)
  const [state, setState] = useState<'idle' | 'loading' | 'playing' | 'paused'>('idle')
  const [current, setCurrent] = useState(-1)
  const [error, setError] = useState<string | null>(null)
  const audio = useRef<HTMLAudioElement | null>(null)
  const timing = useRef<(SpeechWord | null)[]>([])
  const raf = useRef(0)
  const L = LABELS[language]

  const stop = useCallback(() => {
    cancelAnimationFrame(raf.current)
    audio.current?.pause()
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    setState((s) => (s === 'idle' ? s : 'paused'))
  }, [])

  useEffect(() => () => (cancelAnimationFrame(raf.current), audio.current?.pause()), [])
  useEffect(() => {
    if (disabled) {
      stop()
      setCurrent(-1)
    }
  }, [disabled, stop])
  // a new speed needs new audio
  useEffect(() => {
    audio.current?.pause()
    audio.current = null
    setState('idle')
    setCurrent(-1)
  }, [slow, text, language])

  const track = () => {
    const a = audio.current
    if (!a) return
    const t = a.currentTime
    const idx = timing.current.findIndex((w) => w && t >= w.start - 0.03 && t < w.end + 0.12)
    if (idx >= 0) setCurrent(idx)
    raf.current = requestAnimationFrame(track)
  }

  const speakWithBrowser = (fromWord: number) => {
    const v = browserVoice(language)
    if (!v) {
      setError(language === 'bn' ? 'Model reading needs internet the first time. Connect once and try again.' : 'Model reading is not available offline yet.')
      setState('idle')
      return
    }
    const u = new SpeechSynthesisUtterance(words.slice(fromWord).join(' '))
    u.voice = v
    u.lang = v.lang
    u.rate = slow ? 0.65 : 0.9
    let base = 0
    const offsets = words.slice(fromWord).map((w) => ((base += w.length + 1), base - w.length - 1))
    u.onboundary = (e) => {
      let k = -1
      offsets.forEach((o, n) => o <= e.charIndex && (k = n))
      if (k >= 0) setCurrent(fromWord + k)
    }
    u.onend = () => (setState('idle'), setCurrent(-1))
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
    setState('playing')
  }

  const play = async (fromWord?: number) => {
    if (disabled) return
    setError(null)
    if (audio.current && fromWord === undefined && state === 'paused') {
      await audio.current.play()
      setState('playing')
      raf.current = requestAnimationFrame(track)
      return
    }
    setState('loading')
    try {
      const sp = await fetchSpeech(text, language, slow)
      timing.current = alignTokens(words, sp.words)
      const a = claimAudio()
      a.src = sp.url
      a.preload = 'auto'
      a.onended = () => (cancelAnimationFrame(raf.current), setState('idle'), setCurrent(-1))
      a.onpause = () => {
        cancelAnimationFrame(raf.current)
        setState((st) => (st === 'playing' ? 'paused' : st))
      }
      audio.current = a
      if (fromWord !== undefined) {
        const w = timing.current[fromWord] ?? timing.current.slice(fromWord).find(Boolean)
        if (w) {
          await new Promise<void>((res) => {
            if (a.readyState >= 1) return res()
            a.onloadedmetadata = () => res()
          })
          a.currentTime = Math.max(0, w.start - 0.05)
        }
      }
      await a.play()
      setState('playing')
      cancelAnimationFrame(raf.current)
      raf.current = requestAnimationFrame(track)
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) speakWithBrowser(fromWord ?? 0)
      else {
        setError(e instanceof Error ? e.message : 'Could not play the reading')
        setState('idle')
      }
    }
  }

  let wi = -1
  return (
    <div>
      {!disabled && (
        <div className={clsx('flex flex-wrap items-center gap-2', compact ? 'mb-4' : 'mb-6 justify-center')}>
          <button
            type="button"
            onClick={() => (state === 'playing' ? stop() : void play())}
            className={clsx(
              'inline-flex h-11 items-center gap-2 rounded-full pr-5 pl-2 text-sm font-semibold shadow-sm transition-all',
              state === 'playing' ? 'bg-marigold text-ink' : 'bg-teal-700 text-white hover:bg-teal-800',
              langFont(language),
            )}
          >
            <span className={clsx('grid size-8 place-items-center rounded-full', state === 'playing' ? 'bg-white/50' : 'bg-white/15')}>
              {state === 'loading' ? <Loader2 className="size-4 animate-spin" /> : state === 'playing' ? <Pause className="size-4 fill-current" /> : <Volume2 className="size-4" />}
            </span>
            {state === 'playing' ? L.pause : state === 'paused' ? (language === 'bn' ? 'আবার চালাও' : 'Resume') : L.listen}
          </button>
          <button
            type="button"
            onClick={() => setSlow((s) => !s)}
            aria-pressed={slow}
            title="Read slowly"
            className={clsx(
              'inline-flex h-11 items-center gap-1.5 rounded-full px-4 text-sm font-semibold ring-1 transition-colors',
              slow ? 'bg-teal-50 text-teal-800 ring-teal-300' : 'bg-white text-slate-600 ring-slate-200 hover:ring-teal-300',
              langFont(language),
            )}
          >
            <Snail className="size-4" /> {L.slow}
          </button>
          {state !== 'idle' && state !== 'loading' && (
            <button type="button" onClick={() => void play(0)} className="grid size-11 place-items-center rounded-full bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-teal-300" title="From the start" aria-label="Play from the start">
              <RotateCcw className="size-4" />
            </button>
          )}
        </div>
      )}
      <p className={textClassName}>
        {tokens.map((tok, i) => {
          if (/^\s+$/.test(tok) || tok === '') return tok
          wi += 1
          const k = wi
          return (
            <span
              key={i}
              role={disabled ? undefined : 'button'}
              tabIndex={disabled ? undefined : 0}
              onClick={disabled ? undefined : () => void play(k)}
              onKeyDown={disabled ? undefined : (e) => e.key === 'Enter' && void play(k)}
              className={clsx(
                'rounded-lg px-0.5 transition-colors duration-150',
                !disabled && 'cursor-pointer hover:bg-teal-50',
                current === k && 'bg-marigold/40 text-ink shadow-[0_0_0_3px_rgb(244_166_42/0.25)]',
              )}
            >
              {tok}
            </span>
          )
        })}
      </p>
      {!disabled && !error && !compact && <p className={clsx('mt-4 text-center text-xs text-slate-400', langFont(language))}>{L.tip}</p>}
      {error && <p className="mt-4 text-center text-sm text-amber-700">{error}</p>}
    </div>
  )
}

/* ------------------------------------------------- one word, said correctly */

export function useSayWord(language: Language) {
  const [busy, setBusy] = useState<string | null>(null)
  const say = useCallback(
    async (word: string) => {
      const w = word.replace(/[।,.!?;:"'“”‘’]/g, '').trim()
      if (!w) return
      setBusy(word)
      try {
        const sp = await fetchSpeech(w, language, true)
        const a = claimAudio()
        a.src = sp.url
        await a.play()
      } catch {
        const v = browserVoice(language)
        if (v) {
          const u = new SpeechSynthesisUtterance(w)
          u.voice = v
          u.lang = v.lang
          u.rate = 0.7
          window.speechSynthesis.speak(u)
        }
      } finally {
        setBusy(null)
      }
    },
    [language],
  )
  return { say, busy }
}

/* ------------------------------------------------- the child's own reading */

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

/** Imperative handle to play part of the child's recording. */
export function useMyVoice(src: string) {
  const ref = useRef<HTMLAudioElement | null>(null)
  const stopAt = useRef<number | null>(null)
  const get = () => {
    if (!ref.current || ref.current.src !== new URL(src, location.href).href) {
      const a = claimAudio()
      a.src = src
      a.ontimeupdate = () => {
        if (stopAt.current !== null && a.currentTime >= stopAt.current) {
          a.pause()
          stopAt.current = null
        }
      }
      ref.current = a
    } else if (sharedAudio !== ref.current) {
      sharedAudio?.pause()
      sharedAudio = ref.current
    }
    return ref.current
  }
  const playClip = async (start: number, end: number) => {
    const a = get()
    stopAt.current = end + 0.15
    a.currentTime = Math.max(0, start - 0.15)
    await a.play()
  }
  return { playClip }
}

/**
 * Player for the child's own recording. While it plays, the word being read is highlighted
 * (using the word times from marking). Tapping a word plays just that bit of the recording.
 */
export function MyVoicePlayer({ src, marks, language }: { src: string; marks: WordMark[]; language: Language }) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [t, setT] = useState(0)
  const [dur, setDur] = useState(0)
  const [failed, setFailed] = useState(false)
  const stopAt = useRef<number | null>(null)
  const timed = marks.filter((m) => m.start !== null && m.end !== null)
  const current = timed.find((m) => t >= (m.start as number) - 0.05 && t <= (m.end as number) + 0.2)?.index ?? -1

  useEffect(() => {
    const a = audio.current
    if (!a) return
    let raf = 0
    const tick = () => {
      setT(a.currentTime)
      if (stopAt.current !== null && a.currentTime >= stopAt.current) {
        a.pause()
        stopAt.current = null
      }
      raf = requestAnimationFrame(tick)
    }
    const on = () => {
      if (sharedAudio && sharedAudio !== a) sharedAudio.pause()
      sharedAudio = a
      setPlaying(true)
      raf = requestAnimationFrame(tick)
    }
    const off = () => (setPlaying(false), cancelAnimationFrame(raf))
    a.addEventListener('play', on)
    a.addEventListener('pause', off)
    a.addEventListener('ended', off)
    return () => (a.removeEventListener('play', on), a.removeEventListener('pause', off), a.removeEventListener('ended', off), cancelAnimationFrame(raf))
  }, [])

  const toggle = () => {
    const a = audio.current
    if (!a) return
    stopAt.current = null
    if (a.paused) void a.play()
    else a.pause()
  }
  const playWord = (m: WordMark) => {
    const a = audio.current
    if (!a || m.start === null || m.end === null) return
    stopAt.current = m.end + 0.15
    a.currentTime = Math.max(0, m.start - 0.15)
    void a.play()
  }

  if (failed) return <p className="text-sm text-slate-500">Your recording is no longer stored, so it can’t be played.</p>

  return (
    <div>
      <audio ref={audio} src={src} preload="metadata" onLoadedMetadata={(e) => setDur(e.currentTarget.duration)} onError={() => setFailed(true)} />
      <div className="mb-5 flex items-center gap-3 rounded-2xl bg-slate-50 p-2 pr-4 ring-1 ring-slate-200">
        <button
          type="button"
          onClick={toggle}
          className={clsx('grid size-11 shrink-0 place-items-center rounded-full text-white shadow-sm', playing ? 'bg-flag' : 'bg-ink hover:bg-teal-900')}
          aria-label={playing ? 'Pause my reading' : 'Play my reading'}
        >
          {playing ? <Pause className="size-5 fill-current" /> : <Play className="size-5 translate-x-px fill-current" />}
        </button>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex justify-between text-xs font-medium text-slate-500">
            <span className="flex items-center gap-1.5">
              <Ear className="size-3.5" /> {language === 'bn' ? 'আমার পড়া · My voice' : 'My voice'}
            </span>
            <span className="tabular-nums">
              {fmt(t)} / {dur ? fmt(dur) : '—'}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={dur || 0}
            step={0.05}
            value={Math.min(t, dur || 0)}
            onChange={(e) => {
              if (audio.current) audio.current.currentTime = Number(e.target.value)
              setT(Number(e.target.value))
            }}
            className="h-1.5 w-full cursor-pointer accent-teal-700"
            aria-label="Position"
          />
        </div>
      </div>
      <p className={clsx('text-2xl leading-[2.4] text-slate-900', langFont(language))}>
        {marks.map((m) => {
          const st = m.final_status
          const canPlay = m.start !== null && m.end !== null
          return (
            <span key={m.index}>
              <button
                type="button"
                onClick={() => playWord(m)}
                disabled={!canPlay}
                title={canPlay ? 'Hear how you read this word' : undefined}
                className={clsx('word', `word-${st}`, current === m.index && playing && 'bg-marigold/40 !text-ink shadow-[0_0_0_3px_rgb(244_166_42/0.25)]', !canPlay && 'cursor-default')}
              >
                {m.display}
              </button>{' '}
            </span>
          )
        })}
      </p>
    </div>
  )
}
