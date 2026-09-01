import type { ScanSummary } from '../types'

const STATUS_LABELS: Record<ScanSummary['status'], string> = {
  pending: 'Pendiente',
  running: 'Analizando…',
  completed: 'Completado',
  failed: 'Falló',
}

const STATUS_STYLES: Record<ScanSummary['status'], string> = {
  pending: 'text-slate-400',
  running: 'text-blue-400',
  completed: 'text-emerald-400',
  failed: 'text-red-400',
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes === 0) return `${seconds}s`
  return `${minutes} min ${seconds}s`
}

function estimateRemaining(scan: ScanSummary): string | null {
  if (scan.status !== 'running' || scan.files_total <= 0 || scan.files_scanned <= 0) {
    return null
  }
  const elapsedMs = Date.now() - new Date(scan.started_at).getTime()
  if (elapsedMs <= 0) return null

  const remainingFiles = scan.files_total - scan.files_scanned
  if (remainingFiles <= 0) return null

  const etaMs = (elapsedMs / scan.files_scanned) * remainingFiles
  return formatDuration(etaMs)
}

export function ScanProgress({ scan }: { scan: ScanSummary }) {
  const eta = estimateRemaining(scan)
  const progressPct =
    scan.files_total > 0 ? Math.min(100, Math.round((scan.files_scanned / scan.files_total) * 100)) : null

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">Ruta analizada</p>
          <p className="break-all font-mono text-sm text-slate-200">{scan.target_path}</p>
        </div>
        <span className={`text-sm font-semibold ${STATUS_STYLES[scan.status]}`}>
          {scan.status === 'running' && (
            <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />
          )}
          {STATUS_LABELS[scan.status]}
        </span>
      </div>

      {scan.status === 'running' && progressPct !== null && (
        <div className="mt-3">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-blue-500 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-400">
        <span>
          Archivos analizados: {scan.files_scanned}
          {scan.files_total > 0 ? ` / ${scan.files_total}` : ''}
        </span>
        <span>Iniciado: {new Date(scan.started_at).toLocaleString()}</span>
        {scan.finished_at && <span>Finalizado: {new Date(scan.finished_at).toLocaleString()}</span>}
        {eta && <span>Tiempo estimado restante: ~{eta}</span>}
      </div>

      {scan.error_message && (
        <p className="mt-3 rounded border border-red-900 bg-red-950/50 p-2 text-sm text-red-300">
          {scan.error_message}
        </p>
      )}
    </div>
  )
}
