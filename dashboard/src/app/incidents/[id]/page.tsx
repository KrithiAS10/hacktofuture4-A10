'use client'
// src/app/incidents/[id]/page.tsx
import { motion } from 'framer-motion'
import { ArrowLeft, Play, FlaskConical, AlertOctagon, Brain } from 'lucide-react'
import Link from 'next/link'
import { useMemo } from 'react'
import { useParams } from 'next/navigation'
import { Badge, Button, PageHeader } from '@/components/ui'
import { SparklineChart } from '@/components/charts/SparklineChart'
import { incidentLogs, incidents } from '@/lib/mock-data'
import clsx from 'clsx'

const errorRateData = [2.1, 2.3, 4.8, 9.2, 18.7, 18.1, 17.9, 18.3, 17.6, 17.8, 18.0, 17.5]
const rcaCauses = [
  { rank: 1, color: 'text-lerna-amber', confidence: '87%', text: 'Database connection pool exhaustion on db-primary:5432. Pool limit (100) reached under peak load from marketing campaign spike (+340%).' },
  { rank: 2, color: 'text-[#4A5B7A]', confidence: '74%', text: 'Missing read replica routing for SELECT queries causing unnecessary write-path load. 68% of DB queries are reads routed to primary.' },
  { rank: 3, color: 'text-[#4A5B7A]', confidence: '61%', text: 'Upstream traffic spike (+340% vs baseline) from marketing campaign triggered cascading failure in payment pipeline downstream.' },
]

const logLevelStyle: Record<string, string> = {
  ERROR: 'text-lerna-red',
  WARN: 'text-lerna-amber',
  INFO: 'text-lerna-cyan',
  SUCCESS: 'text-lerna-green',
}

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>()
  const incident = useMemo(
    () => incidents.find((item) => item.id === params?.id) ?? incidents[0],
    [params?.id]
  )

  return (
    <div className="p-7 flex flex-col gap-6">
      {/* Back + Header */}
      <div>
        <Link href="/incidents">
          <motion.div
            whileHover={{ x: -2 }}
            className="flex items-center gap-1.5 text-[12px] text-[#4A5B7A] hover:text-[#8A9BBB] font-mono mb-4 w-fit transition-colors"
          >
            <ArrowLeft size={12} /> Back to Incidents
          </motion.div>
        </Link>
        <PageHeader title={incident.title} subtitle={`${incident.id} · ${incident.service}`}>
          <Badge variant="red">{incident.priority} {incident.severity.toUpperCase()}</Badge>
          <Badge variant="amber">{incident.status.toUpperCase()} · {incident.timestamp}</Badge>
          <Badge variant="blue">${incident.cost.toFixed(2)} COST</Badge>
        </PageHeader>
      </div>

      {/* Logs + Metrics grid */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {/* Terminal Logs */}
        <div>
          <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
            Live Logs
          </div>
          <div className="bg-[#060A10] border border-border rounded-xl p-4 h-[280px] overflow-y-auto terminal-scroll font-mono text-xs space-y-0.5">
            {incidentLogs.map((log, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                className="py-0.5 border-b border-white/[0.03] leading-relaxed"
              >
                <span className="text-[#4A5B7A]">{log.time} </span>
                <span className={clsx('font-semibold', logLevelStyle[log.level])}>[{log.level.padEnd(5)}]</span>
                <span className="text-[#8A9BBB] ml-1"> {log.message}</span>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Metrics */}
        <div>
          <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
            Error Rate
          </div>
          <div className="bg-bg-2 border border-border rounded-xl p-5 h-[280px] flex flex-col">
            <div className="text-[11px] font-mono text-[#8A9BBB] mb-1">Error Rate %</div>
            <div className="text-2xl font-black text-lerna-red mb-1">18.7%</div>
            <div className="text-[11px] text-[#4A5B7A] font-mono mb-4">↑ from 2.1% baseline</div>
            <div className="flex-1">
              <SparklineChart
                color="#EF4444"
                gradientId="error"
                data={errorRateData}
                height={160}
                showTooltip
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Root Cause Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.35 }}
        className="bg-gradient-to-br from-[rgba(168,85,247,0.08)] to-[rgba(59,130,246,0.08)] border border-[rgba(168,85,247,0.2)] rounded-2xl p-6"
      >
        <div className="flex items-center gap-2.5 mb-4">
          <Brain size={15} className="text-lerna-purple2" />
          <span className="text-[13px] font-bold text-lerna-purple2 font-mono tracking-wide">
            Root Cause Analysis · Confidence 87%
          </span>
        </div>
        <div className="space-y-0">
          {rcaCauses.map((rca, i) => (
            <div key={i} className="flex gap-3 py-3 border-b border-white/[0.05] last:border-b-0 text-[13px]">
              <span className={clsx('font-mono font-bold shrink-0 mt-0.5', rca.color)}>{rca.rank}.</span>
              <span className="flex-1 text-[#8A9BBB] leading-relaxed">{rca.text}</span>
              <span className="text-[10px] text-[#4A5B7A] font-mono shrink-0 mt-1">{rca.confidence} conf.</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.35 }}
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