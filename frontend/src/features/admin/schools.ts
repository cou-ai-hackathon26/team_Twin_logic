import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export interface SchoolRow {
  id: number
  name: string
  upazila: string | null
  district: string | null
  teachers: number
  children: number
  classes: { id: number; name: string; grade: number }[]
}
export interface SchoolsData {
  schools: SchoolRow[]
  unassigned_classes: { id: number; name: string; grade: number }[]
}

export const SCHOOLS_KEY = ['admin', 'schools']
export const useSchools = (enabled = true) =>
  useQuery({
    queryKey: SCHOOLS_KEY,
    queryFn: () => api.get<SchoolsData>('/admin/schools'),
    enabled,
  })
