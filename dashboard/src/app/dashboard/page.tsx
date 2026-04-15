'use client'
// src/app/dashboard/page.tsx
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, Bot, ChevronRight, Radio, Server } from 'lucide-react'
import Link from 'next/link'
import { Badge, PageHeader, StatCard } from '@/components/ui'
import { SparklineChart } from '@/components/charts/SparklineChart'
import {
  fetchClusterHealth,
  fetchClusterSummary,
  type ClusterHealthResponse,
  type ClusterSummaryResponse,
} from '@/lib/observation-api'
import { incidents as mockIncidents } from '@/lib/mock-data'
import clsx from 'clsx'

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
}
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] } },
}

const timeLabels = [
  '11:00',
  '11:30',
  '12:00',
  '12:30',
  '13:00',
  '13:30',
  '14:00',
  '14:30',
  '14:45',
  '15:00',
  '15:15',
  '15:30',
]
const latencyData = [120, 125, 118, 130, 142, 155, 160, 142, 148, 139, 135, 142]

const recentEvents: UiEvent[] = [
  {
    id: 'evt-1',
    severity: 'red' as const,
    label: 'Critical',
    service: 'payment-service',
    desc: 'High error rate detected (5.2% → 18.7%)',
    time: '2m ago',
  },
  {
    id: 'evt-2',
    severity: 'amber' as const,
    label: 'Warning',
    service: 'api-gateway',
    desc: 'P95 latency spike (180ms → 450ms)',
    time: '14m ago',
  },
  {
    id: 'evt-3',
    severity: 'green' as const,
    label: 'Resolved',
    service: 'auth-service',
    desc: 'Memory leak patched by Executor Agent',
    time: '38m ago',
  },
  {
    id: 'evt-4',
    severity: 'blue' as const,
    label: 'Info',
    service: 'user-service',
    desc: 'Auto-scaling triggered — added 4 replicas',
    time: '52m ago',
  },
]

type UiEvent = {
  id: string
  severity: 'red' | 'amber' | 'green' | 'blue'
  label: string
  service: string
  desc: string
  time: string
}

function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('animate-pulse rounded-md bg-bg-4/80', className)} />
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [clusterHealth, setClusterHealth] = useState<ClusterHealthResponse | null>(null)
  const [clusterSummary, setClusterSummary] = useState<ClusterSummaryResponse | null>(null)
  const [cpuHistory, setCpuHistory] = useState<number[]>([])
  const [memHistory, setMemHistory] = useState<number[]>([])

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [health, summary] = await Promise.all([fetchClusterHealth(), fetchClusterSummary()])
        if (!active) return
        setClusterHealth(health)
        setClusterSummary(summary)

        const metrics = summary.metrics
        if (metrics?.cpu_available && metrics.cpu_percentage != null) {
          const cpuPercentage = metrics.cpu_percentage
          setCpuHistory((prev) => [...prev.slice(-19), cpuPercentage])
        }
        if (metrics?.memory_available && metrics.memory_percentage != null) {
          const memoryPercentage = metrics.memory_percentage
          setMemHistory((prev) => [...prev.slice(-19), memoryPercentage])
        }
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
  const activeIncidents = mockIncidents.filter((i) => i.status !== 'resolved').length
  const cpuValue = clusterSummary?.metrics?.cpu_percentage
  const memValue = clusterSummary?.metrics?.memory_percentage
  const cpuAvailable = clusterSummary?.metrics?.cpu_available ?? false
  const memAvailable = clusterSummary?.metrics?.memory_available ?? false

  return (
    <div className="mx-auto flex max-w-[1360px] flex-col gap-8 px-5 py-8 md:px-8 md:py-10">
      <nav className="flex flex-wrap items-center gap-1.5 text-[12px] text-[#6b7c9e]" aria-label="Breadcrumb">
        <Link href="/dashboard" className="transition-colors hover:text-[#9aaccc]">
          Operations
        </Link>
        <ChevronRight size={14} className="shrink-0 opacity-60" aria-hidden />
        <span className="font-medium text-[#9aaccc]">Overview</span>
      </nav>

      <PageHeader
        title="Cluster overview"
        subtitle="Live signals from your observation layer and Kubernetes summary. Refreshes every 15 seconds."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={clusterHealth?.ok ? 'green' : 'red'}>
            {loading ? 'Syncing…' : clusterHealth?.ok ? 'Healthy' : 'Degraded'}
          </Badge>
          <Badge variant="blue" className="font-mono text-[10px] normal-case tracking-normal">
            {clusterHealth?.last_updated
              ? new Date(clusterHealth.last_updated).toLocaleString()
              : 'Awaiting data'}
          </Badge>
        </div>
      </PageHeader>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
      {loading ? (
        <>
          {[1, 2, 3, 4].map((k) => (
            <div
              key={k}
              className="rounded-xl border border-border bg-bg-2/90 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
            >
              <Skeleton className="mb-3 h-3 w-24" />
              <Skeleton className="h-8 w-28" />
              <Skeleton className="mt-3 h-3 w-full max-w-[200px]" />
            </div>
          ))}
        </>
      ) : (
        <>
          <motion.div variants={item}>
            <StatCard
              label="Cluster health"
              value={clusterHealth?.ok ? 'Good' : 'Check'}
              sub={`${nodesReady}/${nodesTotal} nodes ready · score ${score}`}
              valueColor={clusterHealth?.ok ? 'text-lerna-green' : 'text-lerna-red'}
              glow="blue"
              icon={<Activity size={18} className="text-lerna-green" />}
              iconBg="bg-[rgba(16,185,129,0.12)]"
            />
          </motion.div>

          <motion.div variants={item}>
            <StatCard
              label="Active incidents"
              value={`${activeIncidents}`}
              sub="From mock queue · wire to live incidents when ready"
              valueColor="text-lerna-red"
              icon={<AlertTriangle size={18} className="text-lerna-red" />}
              iconBg="bg-[rgba(239,68,68,0.12)]"
            />
          </motion.div>

          <motion.div variants={item}>
            <StatCard
              label="Services"
              value={`${Math.max(0, servicesTotal - servicesDown)}/${servicesTotal}`}
              sub={`${servicesDown} without ready endpoints`}
              valueColor={servicesDown === 0 ? 'text-lerna-blue2' : 'text-lerna-amber'}
              glow="blue"
              icon={<Server size={18} className="text-lerna-blue2" />}
              iconBg="bg-[rgba(59,130,246,0.12)]"
            />
          </motion.div>

          <motion.div variants={item}>
            <StatCard
              label="Observation"
              value={clusterSummary?.available ? 'Live' : 'Offline'}
              sub={
                clusterSummary?.available
                  ? 'Poller connected to cluster'
                  : clusterSummary?.reason ?? 'Poller unavailable'
              }
              valueColor={clusterSummary?.available ? 'text-lerna-purple2' : 'text-lerna-red'}
              glow="purple"
              icon={
                clusterSummary?.available ? (
                  <Radio size={18} className="text-lerna-purple2" />
                ) : (
                  <Bot size={18} className="text-lerna-red" />
                )
              }
              iconBg={
                clusterSummary?.available
                  ? 'bg-[rgba(168,85,247,0.12)]'
                  : 'bg-[rgba(239,68,68,0.12)]'
              }
            />
          </motion.div>

          <motion.div variants={item}>
            <div className="bg-bg-2 border border-border rounded-2xl p-5">
              <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">
                Cluster CPU Usage
              </div>
              <div className="text-xl font-black text-lerna-blue2 mb-4">
                {cpuAvailable && cpuValue != null ? `${cpuValue}%` : 'N/A'}
              </div>
              <SparklineChart
                color="#3B82F6"
                gradientId="cpu"
                data={cpuHistory}
                height={100}
                showTooltip
              />
            </div>
          </motion.div>
        </>
      )}
      </motion.div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12 xl:gap-8">
        <div className="flex flex-col gap-4 xl:col-span-7">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-sm font-semibold text-white">Workload signals</h2>
              <p className="mt-0.5 text-[12px] text-[#6b7c9e]">Trends for score, restarts, and pod state</p>
            </div>
          </div>
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-4 md:grid-cols-3"
          >
            <motion.div
              variants={item}
              className="rounded-xl border border-border bg-bg-2/90 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-colors hover:border-border-2"
            >
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5c6d8c]">
                Health score
              </div>
              <div className="mt-2 font-display text-xl font-semibold tabular-nums text-lerna-blue2">
                {Math.min(100, score)}%
              </div>
              <div className="mt-4">
                <SparklineChart color="#3B82F6" gradientId="cpu" baseValue={65} height={88} showTooltip />
              </div>
            </motion.div>
            <motion.div
              variants={item}
              className="rounded-xl border border-border bg-bg-2/90 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-colors hover:border-border-2"
            >
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5c6d8c]">
                Restarting pods
              </div>
              <div className="mt-2 font-display text-xl font-semibold tabular-nums text-lerna-purple2">
                {clusterSummary?.pods?.restarting_count ?? 0}
              </div>
              <div className="mt-4">
                <SparklineChart color="#A855F7" gradientId="mem" baseValue={55} height={88} showTooltip />
              </div>
            </motion.div>
            <motion.div
              variants={item}
              className="rounded-xl border border-border bg-bg-2/90 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-colors hover:border-border-2"
            >
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5c6d8c]">
                Non-running pods
              </div>
              <div className="mt-2 font-display text-xl font-semibold tabular-nums text-lerna-cyan">
                {clusterSummary?.pods?.non_running_count ?? 0}
              </div>
              <div className="mt-4">
                <SparklineChart
                  color="#06B6D4"
                  gradientId="lat"
                  data={latencyData}
                  labels={timeLabels}
                  height={88}
                  showTooltip
                />
              </div>
            </motion.div>
          </motion.div>
        </div>

        <div className="flex flex-col gap-4 xl:col-span-5">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-sm font-semibold text-white">Recent activity</h2>
              <p className="mt-0.5 text-[12px] text-[#6b7c9e]">Representative stream · connect to Loki / events next</p>
            </div>
            <Link
              href="/incidents"
              className="shrink-0 text-[12px] font-medium text-lerna-blue2 transition-colors hover:text-white"
            >
              View incidents →
            </Link>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.35 }}
            className="overflow-hidden rounded-xl border border-border bg-bg-2/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
          >
            <div className="hidden grid-cols-[minmax(0,88px)_minmax(0,1fr)_auto] gap-3 border-b border-border/80 px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5c6d8c] md:grid">
              <span>Severity</span>
              <span>Detail</span>
              <span className="text-right">Time</span>
            </div>
            <ul className="divide-y divide-border/60">
              {recentEvents.map((e, i) => (
                <motion.li
                  key={e.id}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.08 + i * 0.04 }}
                  className="px-4 py-3.5 transition-colors hover:bg-bg-4/30"
                >
                  <div className="flex flex-col gap-2 md:grid md:grid-cols-[minmax(0,88px)_minmax(0,1fr)_auto] md:items-center md:gap-3">
                    <Badge variant={e.severity} className="w-fit text-[10px]">
                      {e.label}
                    </Badge>
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] text-[#6b7c9e]">{e.service}</div>
                      <p className="mt-0.5 text-[13px] leading-snug text-[#e2e8f4]">{e.desc}</p>
                    </div>
                    <span className="shrink-0 font-mono text-[11px] text-[#5c6d8c] md:text-right">{e.time}</span>
                  </div>
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
