import { Navigate, Route, Routes } from 'react-router'
import { StudioShell } from './components/StudioShell'
import { DashboardPage } from './pages/DashboardPage'
import { CreateCharacterPage } from './pages/CreateCharacterPage'
import { CharacterPage } from './pages/CharacterPage'
import { JobPage } from './pages/JobPage'

export function App() {
  return (
    <Routes>
      <Route element={<StudioShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="create" element={<CreateCharacterPage />} />
        <Route path="characters/:characterId" element={<CharacterPage />} />
        <Route path="jobs/:jobId" element={<JobPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
