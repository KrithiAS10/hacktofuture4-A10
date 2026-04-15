// src/lib/mock-data.ts

export type Severity = 'critical' | 'warning' | 'info';
export type IncidentStatus = 'active' | 'investigating' | 'monitoring' | 'resolved';
export type AgentStatus = 'running' | 'processing' | 'idle' | 'monitoring';

export interface Incident {
  id: string;
  service: string;
  severity: Severity;
  priority: 'P1' | 'P2' | 'P3';
  status: IncidentStatus;
  title: string;
  description: string;
  timestamp: string;
  duration: string;
  assignedAgent: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  currentTask: string;
  lastAction: string;
  metric: string;
  metricLabel: string;
  progress: number;
  emoji: string;
  accentColor: string;
  bgColor: string;
}

export interface LogLine {
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const incidents: Incident[] = [
  {
    id: 'INC-2024-0891',
    service: 'payment-service',
    severity: 'critical',
    priority: 'P1',
    status: 'active',
    title: 'High Error Rate Detected',
    description: 'Error rate spiked from 2.1% to 18.7% — downstream database timeouts suspected',
    timestamp: '2 min ago',
    duration: '00:02:14',
    assignedAgent: 'Diagnosis Agent',
  },
  {
    id: 'INC-2024-0890',
    service: 'api-gateway',
    severity: 'warning',
    priority: 'P2',
    status: 'investigating',
    title: 'P95 Latency Spike',
    description: 'P95 latency 450ms exceeds SLO threshold of 200ms — auto-scaling triggered',
    timestamp: '14 min ago',
    duration: '00:14:33',
    assignedAgent: 'Planning Agent',
  },
  {
    id: 'INC-2024-0889',
    service: 'user-service',
    severity: 'warning',
    priority: 'P2',
    status: 'monitoring',
    title: 'Memory Utilization Critical',
    description: 'Memory utilization at 89% — GC pause times increasing, possible memory leak',
    timestamp: '31 min ago',
    duration: '00:31:07',
    assignedAgent: 'Filter Agent',
  },
  {
    id: 'INC-2024-0888',
    service: 'auth-service',
    severity: 'info',
    priority: 'P3',
    status: 'resolved',
    title: 'Memory Leak in JWT Validation',
    description: 'Memory leak in JWT validation resolved by Executor Agent — applied connection pool fix',
    timestamp: '38 min ago',
    duration: '00:12:44',
    assignedAgent: 'Executor Agent',
  },
  {
    id: 'INC-2024-0887',
    service: 'notification-service',
    severity: 'info',
    priority: 'P3',
    status: 'resolved',
    title: 'Queue Backlog Clearing',
    description: 'Notification queue backlog reached 12k messages, auto-scaled consumers resolved',
    timestamp: '1h ago',
    duration: '00:08:22',
    assignedAgent: 'Executor Agent',
  },
];

export const agents: Agent[] = [
  {
    id: 'filter',
    name: 'Filter Agent',
    role: 'Anomaly Detection & Triage',
    status: 'running',
    currentTask: 'Monitoring payment-svc',
    lastAction: 'Escalated INC-0891',
    metric: '2,847',
    metricLabel: 'Events/min',
    progress: 82,
    emoji: '🔍',
    accentColor: '#10B981',
    bgColor: 'rgba(16,185,129,0.1)',
  },
  {
    id: 'diagnosis',
    name: 'Diagnosis Agent',
    role: 'Root Cause Analysis',
    status: 'processing',
    currentTask: 'Analyzing INC-0891',
    lastAction: 'DB pool analysis done',
    metric: '87%',
    metricLabel: 'Confidence',
    progress: 65,
    emoji: '🧠',
    accentColor: '#F59E0B',
    bgColor: 'rgba(245,158,11,0.1)',
  },
  {
    id: 'planning',
    name: 'Planning Agent',
    role: 'Remediation Strategy',
    status: 'running',
    currentTask: 'Awaiting diagnosis result',
    lastAction: '2 fixes proposed',
    metric: '14',
    metricLabel: 'Plans today',
    progress: 30,
    emoji: '📋',
    accentColor: '#A855F7',
    bgColor: 'rgba(168,85,247,0.1)',
  },
  {
    id: 'executor',
    name: 'Executor Agent',
    role: 'Fix Application',
    status: 'idle',
    currentTask: 'Awaiting approval',
    lastAction: 'auth-svc fix applied',
    metric: '6',
    metricLabel: 'Fixes today',
    progress: 5,
    emoji: '⚡',
    accentColor: '#3B82F6',
    bgColor: 'rgba(59,130,246,0.1)',
  },
  {
    id: 'validation',
    name: 'Validation Agent',
    role: 'Post-Fix Verification',
    status: 'monitoring',
    currentTask: 'Watching auth-svc',
    lastAction: 'INC-0888 closed ✓',
    metric: '94.2%',
    metricLabel: 'Success rate',
    progress: 50,
    emoji: '✅',
    accentColor: '#06B6D4',
    bgColor: 'rgba(6,182,212,0.1)',
  },
];

export const incidentLogs: LogLine[] = [
  { time: '14:30:01.234', level: 'ERROR', message: 'payment-service: Connection timeout to db-primary:5432 (attempt 1/3)' },
  { time: '14:30:01.891', level: 'ERROR', message: 'payment-service: Connection timeout to db-primary:5432 (attempt 2/3)' },
  { time: '14:30:02.445', level: 'WARN',  message: 'Circuit breaker: threshold reached (18.7% error rate)' },
  { time: '14:30:02.891', level: 'INFO',  message: 'Filter Agent: Anomaly detected — escalating to Diagnosis Agent' },
  { time: '14:30:03.234', level: 'INFO',  message: 'Diagnosis Agent: Analyzing connection pool metrics...' },
  { time: '14:30:04.567', level: 'WARN',  message: 'db-pool: max_connections=100 reached, queueing requests' },
  { time: '14:30:05.123', level: 'ERROR', message: 'payment-service: Queue overflow — dropping 47 requests' },
  { time: '14:30:05.891', level: 'INFO',  message: 'Planning Agent: Proposed fix → increase pool size to 200' },
  { time: '14:30:06.445', level: 'INFO',  message: 'Planning Agent: Secondary fix → enable read replica routing' },
  { time: '14:30:07.234', level: 'WARN',  message: 'Awaiting approval: confidence score 0.87 — human review recommended' },
  { time: '14:30:07.890', level: 'INFO',  message: 'Executor Agent: Standing by for approval signal...' },
  { time: '14:30:08.123', level: 'ERROR', message: 'payment-service: 847 requests failed in last 60s' },
];

export const initialChatMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content: "👋 Hi! I'm Lerna, your autonomous SRE assistant. I have full visibility into your cluster, incidents, and agent pipeline.\n\nI can help you investigate incidents, explain root causes, apply fixes, run simulations, or query metrics. What's on your mind?",
    timestamp: '14:28:00',
  },
  {
    id: '2',
    role: 'user',
    content: "What's causing the payment-service incident right now?",
    timestamp: '14:30:22',
  },
  {
    id: '3',
    role: 'assistant',
    content: "I've analyzed **INC-2024-0891** and the Diagnosis Agent has identified the root cause with 87% confidence:\n\n**Primary:** Database connection pool exhaustion on `db-primary:5432`. The pool is capped at 100 connections, which was hit during a 340% traffic spike from the ongoing marketing campaign.\n\n**Proposed fix:** Increase pool size to 200 and route 68% of read queries to the replica. Should reduce error rate to <0.5% within 2 minutes of application. Want me to apply it?",
    timestamp: '14:30:24',
  },
];

export const cannedResponses = [
  "Applying fix to production now. Executor Agent is increasing the DB connection pool from 100 → 200 and enabling read replica routing. ETA: ~90 seconds. I'll notify you once Validation Agent confirms the error rate drops below 1%.",
  "Currently there are **3 active incidents**: INC-2024-0891 (P1 - payment-service), INC-2024-0890 (P2 - api-gateway), and INC-2024-0889 (P2 - user-service). The P1 is the most urgent and has a proposed fix ready.",
  "Cluster health score is **94/100**. All 32 nodes are responsive, CPU at 68%, memory at 74%. The minor deductions are due to the 3 active incidents. Overall SLO attainment this week is 99.91%.",
  "Sandbox simulation complete (12.3s runtime):\n\n• Error rate: 18.7% → **0.3%**\n• P95 latency: 892ms → **148ms**\n• Connection pool utilization: 100% → **52%**\n\nAll 14 health checks passed. Ready to apply to production?",
  "The Diagnosis Agent has identified 3 potential causes. DB pool exhaustion is the primary culprit (87% confidence). I recommend applying the pool-size fix first, then monitoring for 5 minutes before addressing the read-replica routing.",
];

export function generateTimeSeriesData(base: number, length: number, variance: number): number[] {
  const data = [base];
  for (let i = 1; i < length; i++) {
    const next = data[i - 1] + (Math.random() - 0.45) * variance;
    data.push(Math.max(10, Math.min(95, Math.round(next * 10) / 10)));
  }
  return data;
}