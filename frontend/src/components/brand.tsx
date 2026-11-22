import clsx from 'clsx'
import { Link } from 'react-router-dom'

/** Brand mark: bottle-green tile with a red sun (Bangladesh flag) and the letter প. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={clsx('shrink-0', className ?? 'size-9')} aria-hidden="true">
      <rect width="48" height="48" rx="13" fill="#006a4e" />
      <circle cx="35" cy="13" r="6.5" fill="#e23a4e" />
      <text x="21" y="36" fontSize="27" textAnchor="middle" fill="#fff" fontFamily="'Tiro Bangla','Noto Sans Bengali',serif">
        প
      </text>
    </svg>
  )
}

export function Logo({ to = '/', dark, sub = 'পড়াবন্ধু AI', className }: { to?: string; dark?: boolean; sub?: string; className?: string }) {
  return (
    <Link to={to} className={clsx('flex items-center gap-2.5', className)} aria-label="PoraBondhu AI home">
      <LogoMark />
      <div className="leading-tight">
        <div className={clsx('font-display text-[17px] font-semibold tracking-tight', dark ? 'text-white' : 'text-ink')}>PoraBondhu</div>
        <div className={clsx('font-bn text-xs', dark ? 'text-teal-200/80' : 'text-slate-500')}>{sub}</div>
      </div>
    </Link>
  )
}
