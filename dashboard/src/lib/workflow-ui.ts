import type { AgentWorkflowResponse } from '@/lib/observation-api'
import { formatDateTime } from '@/lib/datetime'

/** Measured LLM spend (USD). Does not use legacy `cost` (incident hint). */
export function resolveWorkflowApiCostUsd(w: AgentWorkflowResponse | null | undefined): number | null {
  if (!w) return null
  if (typeof w.api_cost_usd === 'number' && !Number.isNaN(w.api_cost_usd)) {
    return w.api_cost_usd
  }
  return null
}

/** Human-readable API cost; prefers `api_cost_usd` over stale incident `cost` hints. */
export function formatWorkflowApiCost(w: AgentWorkflowResponse | null | undefined): string {
  const usd = resolveWorkflowApiCostUsd(w)
  if (usd !== null) {
    const abs = Math.abs(usd)
    const decimals = abs > 0 && abs < 0.01 ? 4 : 2
    return `$${usd.toFixed(decimals)}`
  }
  const st = (w?.status ?? '').toLowerCase()
  if (st === 'running' || st === 'accepted') {
    return '…'
  }
  return '—'
}

export type IncidentSeverityUI = 'critical' | 'warning' | 'info'
export type IncidentStatusUI = 'active' | 'investigating' | 'monitoring' | 'resolved'

export interface IncidentListRow {
  id: string
  incidentId: string
  service: string
  severity: IncidentSeverityUI
  priority: 'P1' | 'P2' | 'P3'
  status: IncidentStatusUI
  title: string
  description: string
  timestamp: string
  cost: number
}

export type UiLogLine = {
  time: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS'
  message: string
}

function mapWorkflowStatus(status: string): IncidentStatusUI {
  const s = status.toLowerCase()
  if (s === 'completed') return 'resolved'
  if (s === 'failed') return 'active'
  if (s === 'running') return 'investigating'
  if (s === 'accepted') return 'active'
  return 'monitoring'
}

function summarizeResult(w: AgentWorkflowResponse): string {
  const r = w.result
  if (r == null) return `${w.status} · no output yet`
  if (typeof r === 'string') return r.slice(0, 220) || w.status
  if (typeof r === 'object' && r !== null && 'error' in r) {
    return `Error: ${String((r as { error?: unknown }).error).slice(0, 220)}`
  }
  if (typeof r === 'object' && r !== null) {
    const keys = ['filter', 'matcher', 'diagnosis', 'planning', 'executor', 'validation'] as const
    for (const k of keys) {
      const block = (r as Record<string, unknown>)[k]
      if (block && typeof block === 'object' && 'text' in (block as object)) {
        const t = String((block as { text?: string }).text ?? '').trim()
        if (t) return `${k}: ${t.slice(0, 200)}`
      }
    }
  }
  return w.status
}

export function workflowToListRow(w: AgentWorkflowResponse): IncidentListRow {
  const cost = resolveWorkflowApiCostUsd(w) ?? 0
  const st = w.status.toLowerCase()
  const severity: IncidentSeverityUI =
    st === 'failed' ? 'critical' : st === 'completed' ? 'info' : st === 'running' ? 'warning' : 'warning'
  const priority: IncidentListRow['priority'] = st === 'failed' ? 'P1' : 'P2'
  const ts = formatDateTime(w.accepted_at)
  return {
    id: w.workflow_id,
    incidentId: w.incident_id,
    service: w.incident_id,
    severity,
    priority,
    status: mapWorkflowStatus(w.status),
    title: `Workflow ${w.workflow_id}`,
    description: summarizeResult(w),
    timestamp: ts,
    cost,
  }
}

export function extractLogLinesFromWorkflow(w: AgentWorkflowResponse): UiLogLine[] {
  const out: UiLogLine[] = []
  const r = w.result
  if (r == null) {
    return [{ time: '—', level: 'INFO', message: 'No agent output recorded yet.' }]
  }
  if (typeof r === 'string') {
    return r
      .split('\n')
      .filter(Boolean)
      .slice(0, 48)
      .map((msg, i) => ({
        time: String(i + 1).padStart(2, '0'),
        level: 'INFO' as const,
        message: msg.slice(0, 240),
      }))
  }
  if (typeof r === 'object' && r !== null && 'error' in r) {
    return [
      {
        time: 'ERR',
        level: 'ERROR',
        message: String((r as { error?: unknown }).error).slice(0, 500),
      },
    ]
  }
  if (typeof r === 'object' && r !== null) {
    const keys = ['filter', 'matcher', 'diagnosis', 'planning', 'executor', 'validation'] as const
    for (const k of keys) {
      const block = (r as Record<string, unknown>)[k]
      if (!block || typeof block !== 'object') continue
      const text = String((block as { text?: string }).text ?? '').trim()
      if (!text) continue
      const lines = text.split('\n').slice(0, 8)
      for (const line of lines) {
        out.push({ time: k.slice(0, 3).toUpperCase(), level: 'INFO', message: line.slice(0, 220) })
      }
    }
  }
  const report = w.incident_report as { report_markdown?: string } | null | undefined
  if (report?.report_markdown) {
    out.push({
      time: 'RPT',
      level: 'SUCCESS',
      message: report.report_markdown.split('\n').slice(0, 6).join(' ').slice(0, 400),
    })
  }
  return out.length ? out : [{ time: '—', level: 'INFO', message: 'Workflow finished.' }]
}

export function rcaFromWorkflow(w: AgentWorkflowResponse | null): { text: string; confidence: string }[] {
  if (!w) return []
  const report = w.incident_report as { report_markdown?: string } | undefined
  if (report?.report_markdown) {
    const chunks = report.report_markdown
      .split(/\n##+\s+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 4)
    return chunks.map((text, i) => ({
      text: text.slice(0, 320),
      confidence: i === 0 ? 'report' : '—',
    }))
  }
  return []
}
