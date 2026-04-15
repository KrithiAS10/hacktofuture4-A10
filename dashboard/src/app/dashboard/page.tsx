'use client'
// src/app/dashboard/page.tsx
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, Server, Bot, CheckCircle } from 'lucide-react'
import { Badge, PageHeader, StatCard } from '@/components/ui'
import { SparklineChart } from '@/components/charts/SparklineChart'
import { fetchClusterHealth, fetchClusterSummary } from '@/lib/observation-api'
import { incidents as mockIncidents } from '@/lib/mock-data'

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
}
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
}

const timeLabels = ['11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','14:45','15:00','15:15','15:30']
const latencyData = [120, 125, 118, 130, 142, 155, 160, 142, 148, 139, 135, 142]

const recentEvents: UiEvent[] = [
  { id: 'evt-1', severity: 'red' as const, label: 'CRITICAL', service: 'payment-service', desc: 'High error rate detected (5.2% → 18.7%)', time: '2m ago' },
  { id: 'evt-2', severity: 'amber' as const, label: 'WARNING', service: 'api-gateway', desc: 'P95 latency spike (180ms → 450ms)', time: '14m ago' },
  { id: 'evt-3', severity: 'green' as const, label: 'RESOLVED', service: 'auth-service', desc: 'Memory leak patched by Executor Agent', time: '38m ago' },
  { id: 'evt-4', severity: 'blue' as const, label: 'INFO', service: 'user-service', desc: 'Auto-scaling triggered — added 4 replicas', time: '52m ago' },
]

type UiEvent = {
  id: string
  severity: 'red' | 'amber' | 'green' | 'blue'
  label: string
  service: string
  desc: string
  time: string
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [clusterHealth, setClusterHealth] = useState<any | null>(null)
  const [clusterSummary, setClusterSummary] = useState<any | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [health, summary] = await Promise.all([fetchClusterHealth(), fetchClusterSummary()])
        if (!active) return
        setClusterHealth(health)
        setClusterSummary(summary)
      } catch {
        if (!active) return
        setClusterHealth(null)
        setClusterSummary(null)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    const t = setInterval(load, 15000)
    return () => {
      active = false
      clearInterval(t)
    }
  }, [])

  const nodesReady = clusterHealth?.nodes?.ready ?? 0
  const nodesTotal = clusterHealth?.nodes?.total ?? 0
  const servicesTotal = clusterHealth?.services?.total ?? 0
  const servicesDown = clusterHealth?.services?.without_ready_endpoints_count ?? 0
  const score = clusterHealth?.score_hint ?? 0

  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Command Center" subtitle="Real-time cluster telemetry">
        <Badge variant={clusterHealth?.ok ? 'green' : 'red'}>
          {loading ? '● LOADING' : clusterHealth?.ok ? '● HEALTHY' : '● DEGRADED'}
        </Badge>
        <Badge variant="blue" className="text-[10px]">
          {clusterHealth?.last_updated ? new Date(clusterHealth.last_updated).toLocaleString() : 'No sync yet'}
        </Badge>
      </PageHeader>

      {/* Stat Cards */}
      <motion.div
        variants={container} initial="hidden" animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
      >
        <motion.div variants={item}>
          <StatCard
            label="Cluster Health"
            value={clusterHealth?.ok ? 'GOOD' : 'CHECK'}
            sub={`${nodesReady}/${nodesTotal} nodes ready · score ${score}`}
            valueColor={clusterHealth?.ok ? 'text-lerna-green' : 'text-lerna-red'}
            glow="blue"
            icon={<Activity size={18} className="text-lerna-green" />}
            iconBg="bg-[rgba(16,185,129,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Active Incidents"
            value={`${mockIncidents.filter((item) => item.status !== 'resolved').length}`}
            sub="1 critical · 2 warning"
            valueColor="text-lerna-red"
            icon={<AlertTriangle size={18} className="text-lerna-red" />}
            iconBg="bg-[rgba(239,68,68,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Services Running"
            value={`${Math.max(0, servicesTotal - servicesDown)}/${servicesTotal}`}
            sub={`${servicesDown} services without ready endpoints`}
            valueColor={servicesDown === 0 ? 'text-lerna-blue2' : 'text-lerna-amber'}
            glow="blue"
            icon={<Server size={18} className="text-lerna-blue2" />}
            iconBg="bg-[rgba(59,130,246,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Observation Status"
            value={clusterSummary?.available ? 'LIVE' : 'DOWN'}
            sub={clusterSummary?.available ? 'Poller connected to cluster' : (clusterSummary?.reason ?? 'Poller unavailable')}
            valueColor={clusterSummary?.available ? 'text-lerna-purple2' : 'text-lerna-red'}
            glow="purple"
            icon={clusterSummary?.available ? <Bot size={18} className="text-lerna-purple2" /> : <CheckCircle size={18} className="text-lerna-red" />}
            iconBg="bg-[rgba(168,85,247,0.1)]"
          />
        </motion.div>
      </motion.div>

      {/* Charts */}
      <motion.div
        variants={container} initial="hidden" animate="show"
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">CPU Usage</div>
          <div className="text-xl font-black text-lerna-blue2 mb-4">{Math.min(100, score)}%</div>
          <SparklineChart color="#3B82F6" gradientId="cpu" baseValue={65} height={100} showTooltip />
        </motion.div>

        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">Memory Usage</div>
          <div className="text-xl font-black text-lerna-purple2 mb-4">{clusterSummary?.pods?.restarting_count ?? 0} restarting</div>
          <SparklineChart color="#A855F7" gradientId="mem" baseValue={55} height={100} showTooltip />
        </motion.div>

        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">Avg Latency</div>
          <div className="text-xl font-black text-lerna-cyan mb-4">{clusterSummary?.pods?.non_running_count ?? 0} pods affected</div>
          <SparklineChart color="#06B6D4" gradientId="lat" data={latencyData} labels={timeLabels} height={100} showTooltip />
        </motion.div>
      </motion.div>

      {/* Recent Events */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.35 }}>
        <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
          Recent Events
        </div>
        <div className="flex flex-col gap-2">
          {recentEvents.map((e, i) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.05 }}
              className="bg-bg-2 border border-border rounded-xl px-4 py-3 flex items-center gap-3 text-sm hover:border-border-2 transition-colors"
            >
              <Badge variant={e.severity} className="shrink-0">{e.label}</Badge>
              <span className="text-[#8A9BBB] shrink-0 font-mono text-xs">{e.service}</span>
              <span className="flex-1 text-[13px] text-[#E8EDF5]">{e.desc}</span>
              <span className="text-[11px] text-[#4A5B7A] font-mono shrink-0">{e.time}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}