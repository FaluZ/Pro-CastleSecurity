import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { getScan, getScanFindings } from '../api/client'
import { FindingsTable } from '../components/FindingsTable'
import { ScanProgress } from '../components/ScanProgress'
import type { Severity } from '../types'

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const id = Number(scanId)
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null)
  const [moduleFilter, setModuleFilter] = useState<string | null>(null)

  const scanQuery = useQuery({
    queryKey: ['scan', id],
    queryFn: () => getScan(id),
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 2000 : false),
  })

  const findingsQuery = useQuery({
    queryKey: ['scan', id, 'findings', severityFilter, moduleFilter],
    queryFn: () =>
      getScanFindings(id, {
        severity: severityFilter ?? undefined,
        module: moduleFilter ?? undefined,
      }),
    enabled: scanQuery.data !== undefined,
    refetchInterval: scanQuery.data?.status === 'running' ? 2000 : false,
  })

  if (scanQuery.isLoading) return <p className="text-sm text-slate-400">Cargando…</p>
  if (scanQuery.isError || !scanQuery.data) {
    return <p className="text-sm text-red-400">No se pudo cargar el escaneo.</p>
  }

  const scan = scanQuery.data
  const modules = findingsQuery.data
    ? Array.from(new Set(findingsQuery.data.map((f) => f.module))).sort()
    : []

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-100">Escaneo #{scan.id}</h1>

      <div className="mt-4">
        <ScanProgress scan={scan} />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-400">Severidad:</span>
        <FilterChip active={severityFilter === null} onClick={() => setSeverityFilter(null)}>
          Todas
        </FilterChip>
        {SEVERITIES.map((severity) => (
          <FilterChip
            key={severity}
            active={severityFilter === severity}
            onClick={() => setSeverityFilter(severity)}
          >
            {severity} ({scan.severity_counts[severity] ?? 0})
          </FilterChip>
        ))}

        {modules.length > 1 && (
          <>
            <span className="ml-4 text-sm text-slate-400">Módulo:</span>
            <FilterChip active={moduleFilter === null} onClick={() => setModuleFilter(null)}>
              Todos
            </FilterChip>
            {modules.map((module) => (
              <FilterChip
                key={module}
                active={moduleFilter === module}
                onClick={() => setModuleFilter(module)}
              >
                {module}
              </FilterChip>
            ))}
          </>
        )}
      </div>

      <div className="mt-4">
        {findingsQuery.isLoading ? (
          <p className="text-sm text-slate-400">Cargando hallazgos…</p>
        ) : (
          <FindingsTable findings={findingsQuery.data ?? []} />
        )}
      </div>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
      }`}
    >
      {children}
    </button>
  )
}
