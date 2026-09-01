import { Link, Route, Routes } from 'react-router-dom'
import { NewScanPage } from './pages/NewScanPage'
import { ScanDetailPage } from './pages/ScanDetailPage'
import { ScanHistoryPage } from './pages/ScanHistoryPage'

function App() {
  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-bold tracking-tight text-slate-100">
            Proyecto-<span className="text-blue-400">Pegazus</span>
          </Link>
          <nav className="flex gap-4 text-sm text-slate-400">
            <Link to="/" className="hover:text-slate-100">
              Nuevo escaneo
            </Link>
            <Link to="/history" className="hover:text-slate-100">
              Historial
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<NewScanPage />} />
          <Route path="/history" element={<ScanHistoryPage />} />
          <Route path="/scans/:scanId" element={<ScanDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
