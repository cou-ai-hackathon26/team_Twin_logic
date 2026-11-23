import type { Role } from '@/api/types'

export const homeFor = (role: Role) => (role === 'student' ? '/me' : '/dashboard')
