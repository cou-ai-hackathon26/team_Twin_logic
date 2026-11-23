import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useMe } from '@/api/hooks'
import type { Role } from '@/api/types'
import { ErrorBox, PageLoader } from '@/components/ui/primitives'
import { homeFor } from './home'

/** Shows children only to a logged-in user with the given role; otherwise redirects. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { data: me, isLoading, error } = useMe()
  const loc = useLocation()
  if (isLoading) return <PageLoader />
  if (error) return <ErrorBox className="m-6" error={error} />
  if (!me) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  // an admin can do everything a teacher can (and manages teacher accounts)
  const allowed = me.role === role || (role === 'teacher' && me.role === 'admin')
  if (!allowed) return <Navigate to={homeFor(me.role)} replace />
  return <>{children}</>
}
