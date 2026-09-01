export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed'

export type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical'

export interface ScanSummary {
  id: number
  target_path: string
  status: ScanStatus
  files_scanned: number
  files_total: number
  started_at: string
  finished_at: string | null
  error_message: string | null
  severity_counts: Record<Severity, number>
}

export interface Finding {
  id: number
  module: string
  severity: Severity
  title: string
  description: string
  file_path: string
  line: number | null
  evidence: string | null
  rule_id: string | null
  created_at: string
}
