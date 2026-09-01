import { Fragment, useState } from 'react'
import type { Finding } from '../types'
import { SeverityBadge } from './SeverityBadge'

export function FindingsTable({ findings }: { findings: Finding[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  if (findings.length === 0) {
    return (
      <p className="rounded-lg border border-slate-800 bg-slate-900/60 p-6 text-center text-sm text-slate-400">
        No hay hallazgos que coincidan con los filtros seleccionados.
      </p>
    )
  }

  return (
    <div className="max-h-[65vh] overflow-auto rounded-lg border border-slate-800">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="sticky top-0 z-10 bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-4 py-2">Severidad</th>
            <th className="px-4 py-2">Módulo</th>
            <th className="px-4 py-2">Hallazgo</th>
            <th className="px-4 py-2">Archivo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 bg-slate-950">
          {findings.map((finding) => {
            const expanded = expandedId === finding.id
            return (
              <Fragment key={finding.id}>
                <tr
                  onClick={() => setExpandedId(expanded ? null : finding.id)}
                  className="cursor-pointer hover:bg-slate-900/60"
                >
                  <td className="px-4 py-2">
                    <SeverityBadge severity={finding.severity} />
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-400">{finding.module}</td>
                  <td className="px-4 py-2 text-slate-200">{finding.title}</td>
                  <td className="max-w-xs truncate px-4 py-2 font-mono text-xs text-slate-400">
                    {finding.file_path}
                    {finding.line ? `:${finding.line}` : ''}
                  </td>
                </tr>
                {expanded && (
                  <tr className="bg-slate-900/40">
                    <td colSpan={4} className="px-4 py-3 text-sm text-slate-300">
                      <p>{finding.description}</p>
                      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-slate-400">
                        {finding.rule_id && (
                          <>
                            <dt className="font-semibold text-slate-500">Regla</dt>
                            <dd className="font-mono">{finding.rule_id}</dd>
                          </>
                        )}
                        {finding.evidence && (
                          <>
                            <dt className="font-semibold text-slate-500">Evidencia</dt>
                            <dd className="break-all font-mono">{finding.evidence}</dd>
                          </>
                        )}
                        <dt className="font-semibold text-slate-500">Archivo completo</dt>
                        <dd className="break-all font-mono">{finding.file_path}</dd>
                      </dl>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
