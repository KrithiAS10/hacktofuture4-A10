'use client'

import { motion } from 'framer-motion'
import { ArrowLeft, Play, FlaskConical, AlertOctagon, Brain } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { Badge, Button, PageHeader } from '@/components/ui'
import { SparklineChart } from '@/components/charts/SparklineChart'
import clsx from 'clsx'
import { fetchAgentWorkflow, type AgentWorkflowResponse } from '@/lib/observation-api'
import {
  extractLogLinesFromWorkflow,
  rcaFromWorkflow,
} from '@/lib/workflow-ui'

const logLevelStyle: Record<string, string> = {
  ERROR: 'text-lerna-red',
  WARN: 'text-lerna-amber',
  INFO: 'text-lerna-cyan',
  SUCCESS: 'text-lerna-green',
}

const errorRateData = [2.1, 2.3, 4.8, 9.2, 18.7, 18.1, 17.9, 18.3, 17.6, 17.8, 18.0, 17.5]

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>()
  const [wf, setWf] = useState<AgentWorkflowResponse | null | undefined>(undefined)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    const id = params?.id
    if (!id) return
    let cancel = false
    setWf(undefined)
    setLoadError(null)
    void fetchAgentWorkflow(id)
      .then((w) => {
        if (!cancel) setWf(w)
      })
      .catch(() => {
        if (!cancel) {
          setWf(null)
          setLoadError('Workflow not found or agents API unreachable.')
        }
      })
    return () => {
      cancel = true
    }
  }, [params?.id])

  const cost = useMemo(() => {
    if (!wf) return 0
    if (typeof wf.api_cost_usd === 'number' && !Number.isNaN(wf.api_cost_usd)) return wf.api_cost_usd
    return wf.cost ?? 0
  }, [wf])

  const title = wf ? `Incident ${wf.incident_id}` : 'Incident'
  const subtitle = wf ? `${wf.workflow_id} · ${wf.status}` : 'Loading…'

  const logLines = useMemo(() => (wf ? extractLogLinesFromWorkflow(wf) : []), [wf])
  const rcaItems = useMemo(() => (wf ? rcaFromWorkflow(wf) : []), [wf])

  if (wf === undefined) {
    return (
      <div className="p-7 text-sm text-[#8A9BBB]">Loading workflow…</div>
    )
  }

  if (wf === null) {
    return (
      <div className="p-7 flex flex-col gap-4">
        <Link href="/incidents" className="text-[12px] text-[#4A5B7A] hover:text-[#8A9BBB] font-mono w-fit">
          ← Back to Incidents
        </Link>
        <div className="rounded-xl border border-lerna-red/40 bg-bg-2 px-4 py-3 text-sm text-lerna-red">
          {loadError ?? 'Unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-7 flex flex-col gap-6">
      <div>
        <Link href="/incidents">
          <motion.div
            whileHover={{ x: -2 }}
            className="flex items-center gap-1.5 text-[12px] text-[#4A5B7A] hover:text-[#8A9BBB] font-mono mb-4 w-fit transition-colors"
          >
            <ArrowLeft size={12} /> Back to Incidents
          </motion.div>
        </Link>
        <PageHeader title={title} subtitle={subtitle}>
          <Badge variant={wf.status === 'failed' ? 'red' : wf.status === 'completed' ? 'green' : 'amber'}>
            {wf.status.toUpperCase()}
          </Badge>
          <Badge variant="blue">${cost.toFixed(4)} API</Badge>
        </PageHeader>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        <div>
          <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
            Agent output (abridged)
          </div>
          <div className="bg-[#060A10] border border-border rounded-xl p-4 h-[280px] overflow-y-auto terminal-scroll font-mono text-xs space-y-0.5">
            {logLines.map((log, i) => (
              <motion.div
                key={`${log.time}-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.02 }}
                className="py-0.5 border-b border-white/[0.03] leading-relaxed"
              >
                <span className="text-[#4A5B7A]">{log.time} </span>
                <span className={clsx('font-semibold', logLevelStyle[log.level] ?? 'text-[#8A9BBB]')}>
                  [{log.level.padEnd(5)}]
                </span>
                <span className="text-[#8A9BBB] ml-1"> {log.message}</span>
              </motion.div>
            ))}
          </div>
        </div>

        <div>
          <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
            Error rate (demo)
          </div>
          <div className="bg-bg-2 border border-border rounded-xl p-5 h-[280px] flex flex-col">
            <div className="text-[11px] font-mono text-[#8A9BBB] mb-1">Placeholder chart</div>
            <div className="text-2xl font-black text-lerna-red mb-1">—</div>
            <div className="text-[11px] text-[#4A5B7A] font-mono mb-4">Wire PromQL / Loki for live error rate</div>
            <div className="flex-1">
              <SparklineChart color="#EF4444" gradientId="error" data={errorRateData} height={160} showTooltip />
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.35 }}
        className="bg-gradient-to-br from-[rgba(168,85,247,0.08)] to-[rgba(59,130,246,0.08)] border border-[rgba(168,85,247,0.2)] rounded-2xl p-6"
      >
        <div className="flex items-center gap-2.5 mb-4">
          <Brain size={15} className="text-lerna-purple2" />
          <span className="text-[13px] font-bold text-lerna-purple2 font-mono tracking-wide">
            Post-run report {rcaItems.length ? '' : '(pending)'}
          </span>
        </div>
        {rcaItems.length ? (
          <div className="space-y-0">
            {rcaItems.map((rca, i) => (
              <div key={i} className="flex gap-3 py-3 border-b border-white/[0.05] last:border-b-0 text-[13px]">
                <span className="font-mono font-bold shrink-0 mt-0.5 text-lerna-amber">{i + 1}.</span>
                <span className="flex-1 text-[#8A9BBB] leading-relaxed">{rca.text}</span>
                <span className="text-[10px] text-[#4A5B7A] font-mono shrink-0 mt-1">{rca.confidence}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[13px] text-[#8A9BBB]">
            No Qdrant incident report yet for this run. Complete workflows with reporting enabled populate this section.
          </p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.35 }}
        className="flex gap-3 flex-wrap"
      >
        <Button variant="primary">
          <Play size={14} /> Apply Fix
        </Button>
        <Button variant="outline">
          <FlaskConical size={14} /> Simulate in Sandbox
        </Button>
        <Button variant="danger">
          <AlertOctagon size={14} /> Escalate to Human
        </Button>
      </motion.div>
    </div>
  )
}
