import { TriangleAlert } from 'lucide-react'
import { useHealth } from '@/api/practice'

/** Shown only on the public demo server (PB_SEED_DEMO=true). */
export function DemoNotice({ className = '' }: { className?: string }) {
  const { data } = useHealth()
  if (!data?.demo_mode) return null
  return (
    <div className={`flex items-start gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200 ${className}`}>
      <TriangleAlert className="mt-0.5 size-4 shrink-0" />
      <span>
        <b>Public demo.</b> The test logins are shared, so please <b>do not record real children</b> here. Read the passage in your own voice. Recordings are
        deleted after 14 days or when the demo is reset. <span className="font-bn">এটি পরীক্ষামূলক ডেমো; এখানে শিশুদের কণ্ঠ রেকর্ড করবেন না।</span>
      </span>
    </div>
  )
}
