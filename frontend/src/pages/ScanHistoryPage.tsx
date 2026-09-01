import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listScans } from '../api/client'
import type { ScanSummary } from '../types'

const STATUS_LABELS: Record<ScanSummary['status'], string> = {
  pending: 'Pendiente',
  running: 'Analizando…',
  completed: 'Completado',
  failed: 'Falló',
}

export function ScanHistoryPage() {
  const { data: scans, isLoading, isError } = useQuery({
    queryKey: ['scans'],
    queryFn: listScans,
    refetchInterval: 5000,
  })

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Historial de escaneos</h1>
        <Link
          to="/"
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500"
        >
          Nuevo escaneo
        </Link>
      </div>

      {isLoading && <p className="mt-6 text-sm text-slate-400">Cargando…</p>}
      {isError && <p className="mt-6 text-sm text-red-400">No se pudo cargar el historial.</p>}

      {scans && scans.length === 0 && (
        <p className="mt-6 text-sm text-slate-400">Todavía no hay escaneos. Inicia uno nuevo.</p>
      )}

      {scans && scans.length > 0 && (
        <ul className="mt-6 divide-y divide-slate-800 rounded-lg border border-slate-800">
          {scans.map((scan) => {
            const totalFindings = Object.values(scan.severity_counts).reduce((a, b) => a + b, 0)
            return (
              <li key={scan.id}>
                <Link
                  to={`/scans/${scan.id}`}
                  className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-900/60"
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-sm text-slate-200">{scan.target_path}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(scan.started_at).toLocaleString()} · {scan.files_scanned} archivos ·{' '}
                      {totalFindings} hallazgos
                    </p>
                  </div>
                  <span className="shrink-0 text-sm text-slate-400">
                    {STATUS_LABELS[scan.status]}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
