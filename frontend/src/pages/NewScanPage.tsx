import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, createScan } from '../api/client'

export function NewScanPage() {
  const [path, setPath] = useState('')
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (targetPath: string) => createScan(targetPath),
    onSuccess: (scan) => navigate(`/scans/${scan.id}`),
  })

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (path.trim()) mutation.mutate(path.trim())
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-100">Nuevo escaneo</h1>
      <p className="mt-1 text-sm text-slate-400">
        Indica la ruta local de un proyecto para analizarlo con los módulos de detección
        habilitados (actualmente: malware genérico).
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
        <label htmlFor="path" className="text-sm font-medium text-slate-300">
          Ruta del proyecto
        </label>
        <input
          id="path"
          type="text"
          value={path}
          onChange={(event) => setPath(event.target.value)}
          placeholder="C:\ruta\al\proyecto"
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100 outline-none focus:border-blue-500"
        />

        <button
          type="submit"
          disabled={!path.trim() || mutation.isPending}
          className="mt-2 self-start rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? 'Iniciando…' : 'Iniciar escaneo'}
        </button>

        {mutation.isError && (
          <p className="rounded border border-red-900 bg-red-950/50 p-2 text-sm text-red-300">
            {mutation.error instanceof ApiError ? mutation.error.message : 'Error inesperado.'}
          </p>
        )}
      </form>
    </div>
  )
}
