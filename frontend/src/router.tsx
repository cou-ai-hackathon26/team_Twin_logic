import { lazy, Suspense, type ComponentType } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { PageLoader } from '@/components/ui/primitives'
import { RequireRole } from '@/features/auth/RequireRole'

// Each page is its own chunk, so the first load stays small (charts load only where used).
function page(load: () => Promise<Record<string, ComponentType>>, name: string) {
  const C = lazy(async () => {
    try {
      const mod = await load()
      sessionStorage.removeItem('pb-chunk-reload')
      return { default: mod[name] }
    } catch (e) {
      // After a new build the old page asks for files that no longer exist: reload once.
      if (!sessionStorage.getItem('pb-chunk-reload')) {
        sessionStorage.setItem('pb-chunk-reload', '1')
        window.location.reload()
        return new Promise<never>(() => {})
      }
      throw e
    }
  })
  return (
    <Suspense fallback={<PageLoader />}>
      <C />
    </Suspense>
  )
}

export const router = createBrowserRouter([
  { path: '/', element: page(() => import('@/features/landing/LandingPage'), 'LandingPage') },
  { path: '/login', element: page(() => import('@/features/auth/LoginPage'), 'LoginPage') },
  {
    // student role
    path: '/me',
    element: (
      <RequireRole role="student">
        {page(() => import('@/features/student/StudentShell'), 'StudentShell')}
      </RequireRole>
    ),
    children: [
      { index: true, element: page(() => import('@/features/student/StudentHome'), 'StudentHome') },
      { path: 'read/:passageId', element: page(() => import('@/features/student/StudentReading'), 'StudentReadingPage') },
      { path: 'readings/:id', element: page(() => import('@/features/student/StudentReading'), 'StudentResultPage') },
      { path: 'practice', element: page(() => import('@/features/student/StudentPractice'), 'StudentPractice') },
      { path: 'progress', element: page(() => import('@/features/student/StudentProgress'), 'StudentProgress') },
    ],
  },
  {
    // teacher role
    element: (
      <RequireRole role="teacher">
        <AppShell />
      </RequireRole>
    ),
    children: [
      { path: '/dashboard', element: page(() => import('@/features/classes/ClassesPage'), 'ClassesPage') },
      { path: '/classes/:id', element: page(() => import('@/features/classes/ClassPage'), 'ClassPage') },
      { path: '/students/:id', element: page(() => import('@/features/students/StudentPage'), 'StudentPage') },
      { path: '/assess', element: page(() => import('@/features/assess/AssessPage'), 'AssessPage') },
      { path: '/read/:studentId/:passageId', element: page(() => import('@/features/assess/ChildReadingPage'), 'ChildReadingPage') },
      { path: '/review', element: page(() => import('@/features/review/ReviewQueuePage'), 'ReviewQueuePage') },
      { path: '/readings/:id', element: page(() => import('@/features/review/ReviewPage'), 'ReviewPage') },
      { path: '/passages', element: page(() => import('@/features/passages/PassagesPage'), 'PassagesPage') },
      { path: '/engine', element: page(() => import('@/features/engine/EnginePage'), 'EnginePage') },
      { path: '/benchmark', element: page(() => import('@/features/benchmark/BenchmarkPage'), 'BenchmarkPage') },
      { path: '/settings', element: page(() => import('@/features/settings/SettingsPage'), 'SettingsPage') },
      { path: '/admin/teachers', element: page(() => import('@/features/admin/TeachersPage'), 'TeachersPage') },
      { path: '*', element: page(() => import('@/features/NotFound'), 'NotFound') },
    ],
  },
])
