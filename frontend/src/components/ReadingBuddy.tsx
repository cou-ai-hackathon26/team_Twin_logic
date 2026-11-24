import clsx from 'clsx'

/** "Pori" (পড়ি), PoraBondhu's own reading buddy: an original drawing (simple SVG shapes) shown only on
 * the student pages. Moods change the eyes and mouth; the speech bubble is optional. */
export type BuddyMood = 'happy' | 'cheer' | 'think'

export function ReadingBuddy({
  size = 96,
  mood = 'happy',
  say,
  className,
}: {
  size?: number
  mood?: BuddyMood
  say?: string
  className?: string
}) {
  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        role="img"
        aria-label="Pori, your reading buddy"
        className="shrink-0 animate-float drop-shadow-md"
      >
        {/* body */}
        <path d="M30 118c0-22 13-36 30-36s30 14 30 36z" fill="#0f766e" />
        <path d="M52 84h16l-8 10z" fill="#fef3c7" />
        {/* head */}
        <circle cx="60" cy="52" r="30" fill="#f5c9a0" />
        {/* hair */}
        <path d="M30 50c0-20 13-31 30-31s30 11 30 31c-6-9-14-13-22-14-4 5-12 8-22 8-6 0-11 2-16 6z" fill="#3b2a20" />
        <circle cx="31" cy="44" r="7" fill="#3b2a20" />
        <circle cx="89" cy="44" r="7" fill="#3b2a20" />
        <circle cx="31" cy="44" r="3" fill="#e11d48" />
        <circle cx="89" cy="44" r="3" fill="#e11d48" />
        {/* cheeks */}
        <circle cx="44" cy="62" r="5" fill="#fb7185" opacity="0.45" />
        <circle cx="76" cy="62" r="5" fill="#fb7185" opacity="0.45" />
        {/* eyes */}
        {mood === 'cheer' ? (
          <>
            <path d="M44 53q4-5 8 0" stroke="#1f2937" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M68 53q4-5 8 0" stroke="#1f2937" strokeWidth="3" fill="none" strokeLinecap="round" />
          </>
        ) : (
          <>
            <circle cx="48" cy="53" r="3.6" fill="#1f2937" />
            <circle cx="72" cy="53" r="3.6" fill="#1f2937" />
            <circle cx="49.2" cy="51.8" r="1.1" fill="#fff" />
            <circle cx="73.2" cy="51.8" r="1.1" fill="#fff" />
          </>
        )}
        {/* mouth */}
        {mood === 'think' ? (
          <path d="M54 68h12" stroke="#9f1239" strokeWidth="3" strokeLinecap="round" />
        ) : mood === 'cheer' ? (
          <path d="M50 64q10 12 20 0z" fill="#9f1239" />
        ) : (
          <path d="M52 65q8 7 16 0" stroke="#9f1239" strokeWidth="3" fill="none" strokeLinecap="round" />
        )}
        {/* open book held in front */}
        <path d="M34 92q13-6 26 0v20q-13-6-26 0z" fill="#fff" stroke="#f59e0b" strokeWidth="2" />
        <path d="M60 92q13-6 26 0v20q-13-6-26 0z" fill="#fff" stroke="#f59e0b" strokeWidth="2" />
        <path d="M39 98q8-3 16 0M39 104q8-3 16 0M65 98q8-3 16 0M65 104q8-3 16 0" stroke="#cbd5e1" strokeWidth="1.6" fill="none" />
        {/* hands */}
        <circle cx="33" cy="100" r="5" fill="#f5c9a0" />
        <circle cx="87" cy="100" r="5" fill="#f5c9a0" />
      </svg>
      {say && (
        <div className="relative rounded-2xl bg-white px-4 py-2.5 font-bn text-lg font-semibold text-ink shadow-sm ring-1 ring-amber-200">
          <span aria-hidden="true" className="absolute top-1/2 -left-2 size-4 -translate-y-1/2 rotate-45 bg-white ring-1 ring-amber-200 [clip-path:polygon(0_0,0_100%,100%_100%)]" />
          {say}
        </div>
      )}
    </div>
  )
}

/** What Pori says after a reading, by the mark out of 10. */
export function buddyLine(score: number | null | undefined): { mood: BuddyMood; say: string } {
  if (score === null || score === undefined) return { mood: 'happy', say: 'চলো পড়ি!' }
  if (score >= 8) return { mood: 'cheer', say: 'খুব ভালো পড়েছ!' }
  if (score >= 5) return { mood: 'happy', say: 'ভালো! আরেকটু অনুশীলন করি।' }
  return { mood: 'think', say: 'চলো, আবার একসাথে পড়ি!' }
}
