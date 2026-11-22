import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/ui/primitives'

export function NotFound() {
  return (
    <EmptyState title="Page not found">
      <Link className="text-teal-700 underline" to="/dashboard">
        Back to classes
      </Link>
    </EmptyState>
  )
}
