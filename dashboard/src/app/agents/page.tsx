"use client";
// src/app/agents/page.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  CircleCheckBig,
  CircleAlert,
  Edit3,
  RotateCcw,
  Save,
  X,
} from "lucide-react";
import { Badge, Button, PageHeader } from "@/components/ui";
import {
  fetchAgentPrompts,
  fetchAgentWorkflow,
  fetchAgentWorkflows,
  fetchLatestAgentWorkflow,
  resetAgentPrompt,
  updateAgentPrompt,
  type AgentWorkflowResponse,
} from "@/lib/observation-api";
import { formatDateTime } from "@/lib/datetime";
import { formatWorkflowApiCost } from "@/lib/workflow-ui";
import clsx from "clsx";

type AgentCardStatus = "running" | "processing" | "idle" | "monitoring";

type WorkflowStageOutput = {
  text?: string;
  started_at?: string;
  finished_at?: string;
};

type WorkflowAgentCard = {
  id: string;
  name: string;
  role: string;
  status: AgentCardStatus;
  currentTask: string;
  lastAction: string;
  metric: string;
  metricLabel: string;
  progress: number;
  emoji: string;
  accentColor: string;
  bgColor: string;
};

const statusConfig: Record<
  AgentCardStatus,
  { label: string; dotClass: string; textColor: string }
> = {
  running: {
    label: "Running",
    dotClass: "bg-lerna-green pulse-green",
    textColor: "text-lerna-green",
  },
  processing: {
    label: "Processing",
    dotClass: "bg-lerna-amber pulse-amber",
    textColor: "text-lerna-amber",
  },
  idle: {
    label: "Idle",
    dotClass: "bg-[#4A5B7A]",
    textColor: "text-[#4A5B7A]",
  },
  monitoring: {
    label: "Monitoring",
    dotClass: "bg-lerna-cyan pulse-blue",
    textColor: "text-lerna-cyan",
  },
};

const progressGradientDefaults: Record<string, string> = {
  filter: "from-lerna-green to-emerald-400",
  matcher: "from-[#F97316] to-[#FB923C]",
  diagnosis: "from-lerna-amber to-orange-400",
  planning: "from-lerna-purple to-lerna-purple2",
  executor: "from-lerna-blue to-lerna-cyan",
  validation: "from-lerna-cyan to-lerna-green",
};

const stageStyleDefaults: Record<
  string,
  {
    emoji: string;
    accentColor: string;
    bgColor: string;
    gradient: string;
    pipelineColor: string;
    pipelineText: string;
    pipelineBorder: string;
  }
> = {
  filter: {
    emoji: "🔍",
    accentColor: "#10B981",
    bgColor: "rgba(16,185,129,0.1)",
    gradient: "from-lerna-green to-emerald-400",
    pipelineColor: "rgba(16,185,129,0.15)",
    pipelineText: "text-lerna-green",
    pipelineBorder: "rgba(16,185,129,0.2)",
  },
  matcher: {
    emoji: "🧩",
    accentColor: "#F97316",
    bgColor: "rgba(249,115,22,0.1)",
    gradient: "from-[#F97316] to-[#FB923C]",
    pipelineColor: "rgba(249,115,22,0.15)",
    pipelineText: "text-[#FB923C]",
    pipelineBorder: "rgba(249,115,22,0.2)",
  },
  diagnosis: {
    emoji: "🧠",
    accentColor: "#F59E0B",
    bgColor: "rgba(245,158,11,0.1)",
    gradient: "from-lerna-amber to-orange-400",
    pipelineColor: "rgba(245,158,11,0.15)",
    pipelineText: "text-lerna-amber",
    pipelineBorder: "rgba(245,158,11,0.2)",
  },
  planning: {
    emoji: "📋",
    accentColor: "#A855F7",
    bgColor: "rgba(168,85,247,0.1)",
    gradient: "from-lerna-purple to-lerna-purple2",
    pipelineColor: "rgba(168,85,247,0.15)",
    pipelineText: "text-lerna-purple2",
    pipelineBorder: "rgba(168,85,247,0.2)",
  },
  executor: {
    emoji: "⚡",
    accentColor: "#3B82F6",
    bgColor: "rgba(59,130,246,0.1)",
    gradient: "from-lerna-blue to-lerna-cyan",
    pipelineColor: "rgba(59,130,246,0.15)",
    pipelineText: "text-lerna-blue2",
    pipelineBorder: "rgba(59,130,246,0.2)",
  },
  validation: {
    emoji: "✅",
    accentColor: "#06B6D4",
    bgColor: "rgba(6,182,212,0.1)",
    gradient: "from-lerna-cyan to-lerna-green",
    pipelineColor: "rgba(6,182,212,0.15)",
    pipelineText: "text-lerna-cyan",
    pipelineBorder: "rgba(6,182,212,0.2)",
  },
};

const defaultSystemPrompts: Record<string, string> = {
  filter:
    "You are the Filter Agent. Validate whether incoming signals represent real service-impacting incidents.",
  matcher:
    "You are the Incident Matcher Agent. Find similar past incidents and summarize the most relevant evidence and remediations.",
  diagnosis:
    "You are the Diagnosis Agent. Analyze telemetry and cluster state to identify likely root cause.",
  planning:
    "You are the Planning Agent. Propose safe remediation plans with trade-offs and rollback options.",
  executor:
    "You are the Executor Agent. Apply approved remediations safely with explicit scope control.",
  validation:
    "You are the Validation Agent. Verify remediation outcomes and close or reopen incidents based on evidence.",
};

function getWorkflowResult(workflow: AgentWorkflowResponse | null): Record<string, unknown> | null {
  if (!workflow?.result || typeof workflow.result !== "object") {
    return null;
  }
  return workflow.result as Record<string, unknown>;
}

function formatStageLabel(stageKey: string) {
  return stageKey
    .split(/[_-]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getWorkflowStageKeys(workflow: AgentWorkflowResponse | null) {
  const result = getWorkflowResult(workflow);
  if (!result) return [];
  return Object.keys(result).filter((key) => {
    const value = result[key];
    return value && typeof value === "object";
  });
}

function getStageOutput(
  workflow: AgentWorkflowResponse | null,
  stageKey: string,
): WorkflowStageOutput | null {
  const result = getWorkflowResult(workflow);
  if (!result) return null;
  const value = result[stageKey];
  if (!value || typeof value !== "object") {
    return null;
  }
  return value as WorkflowStageOutput;
}

export default function AgentsPage() {
  const [promptByAgent, setPromptByAgent] = useState<Record<string, string>>(
    {},
  );
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [draftPrompt, setDraftPrompt] = useState("");
  const [initialPrompt, setInitialPrompt] = useState("");
  const [savingAgentId, setSavingAgentId] = useState<string | null>(null);
  const [resettingAgentId, setResettingAgentId] = useState<string | null>(null);
  const [loadingPrompts, setLoadingPrompts] = useState(true);
  const [workflow, setWorkflow] = useState<AgentWorkflowResponse | null>(null);
  const [workflowHistory, setWorkflowHistory] = useState<AgentWorkflowResponse[]>([]);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);
  const [notice, setNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const workflowStageKeys = useMemo(() => getWorkflowStageKeys(workflow), [workflow]);
  const agentIds = useMemo(() => workflowStageKeys, [workflowStageKeys]);
  const agentNameById = useMemo(
    () => Object.fromEntries(agentIds.map((agentId) => [agentId, formatStageLabel(agentId)])),
    [agentIds],
  );

  useEffect(() => {
    let active = true;
    const loadPrompts = async () => {
      try {
        const response = await fetchAgentPrompts(agentIds);
        if (!active) return;
        const mapping: Record<string, string> = {};
        for (const item of response.prompts) {
          mapping[item.agent_id] = item.prompt;
        }
        setPromptByAgent(mapping);
        setNotice(null);
      } catch {
        if (!active) return;
        setError("Unable to load prompts from Redis right now.");
        setNotice({
          type: "error",
          text: "Using fallback prompts. Redis is currently unreachable.",
        });
      } finally {
        if (active) setLoadingPrompts(false);
      }
    };
    loadPrompts();
    return () => {
      active = false;
    };
  }, [agentIds]);

  useEffect(() => {
    let active = true;
    const loadWorkflow = async () => {
      try {
        const listResponse = await fetchAgentWorkflows();
        if (!active) return;
        const history = listResponse.workflows ?? [];
        setWorkflowHistory(history);

        const storedWorkflowId =
          typeof window !== "undefined"
            ? window.localStorage.getItem("lerna:lastWorkflowId")
            : null;
        let nextWorkflow =
          history.find((item) => item.workflow_id === storedWorkflowId) ??
          null;

        if (!nextWorkflow && storedWorkflowId) {
          try {
            nextWorkflow = await fetchAgentWorkflow(storedWorkflowId);
          } catch {
            nextWorkflow = null;
          }
        }

        if (!nextWorkflow) {
          nextWorkflow = history[0] ?? null;
        }

        if (!nextWorkflow) {
          try {
            nextWorkflow = await fetchLatestAgentWorkflow();
          } catch (err) {
            const status = (err as Error & { status?: number }).status;
            if (status !== 404) throw err;
          }
        }

        if (!active) return;
        setWorkflow(nextWorkflow);
        if (typeof window !== "undefined") {
          if (nextWorkflow?.workflow_id) {
            window.localStorage.setItem("lerna:lastWorkflowId", nextWorkflow.workflow_id);
          } else {
            window.localStorage.removeItem("lerna:lastWorkflowId");
          }
        }
      } catch {
        if (!active) return;
        setWorkflow(null);
        setWorkflowHistory([]);
      } finally {
        if (active) setLoadingWorkflow(false);
      }
    };

    void loadWorkflow();
    return () => {
      active = false;
    };
  }, []);

  const openEditor = (agentId: string) => {
    const currentPrompt =
      promptByAgent[agentId] ?? defaultSystemPrompts[agentId] ?? "";
    setEditingAgentId(agentId);
    setError(null);
    setDraftPrompt(currentPrompt);
    setInitialPrompt(currentPrompt);
  };

  const closeEditor = useCallback(() => {
    setEditingAgentId(null);
    setDraftPrompt("");
    setInitialPrompt("");
  }, []);

  const savePrompt = useCallback(async () => {
    if (!editingAgentId) return;
    try {
      setSavingAgentId(editingAgentId);
      const updated = await updateAgentPrompt(editingAgentId, draftPrompt);
      setPromptByAgent((prev) => ({
        ...prev,
        [updated.agent_id]: updated.prompt,
      }));
      setNotice({
        type: "success",
        text: `Saved prompt for ${agentNameById[editingAgentId] ?? editingAgentId}.`,
      });
      closeEditor();
      setError(null);
    } catch {
      setError("Failed to save prompt to Redis.");
      setNotice({
        type: "error",
        text: "Prompt save failed. Check backend and Redis connectivity.",
      });
    } finally {
      setSavingAgentId(null);
    }
  }, [editingAgentId, draftPrompt, agentNameById, closeEditor]);

  const resetPromptToDefault = async () => {
    if (!editingAgentId) return;
    try {
      setResettingAgentId(editingAgentId);
      await resetAgentPrompt(editingAgentId);
      setPromptByAgent((prev) => {
        const next = { ...prev };
        delete next[editingAgentId];
        return next;
      });
      setNotice({
        type: "success",
        text: `Reset prompt for ${agentNameById[editingAgentId] ?? editingAgentId}.`,
      });
      closeEditor();
      setError(null);
    } catch {
      setError("Failed to reset prompt in Redis.");
      setNotice({
        type: "error",
        text: "Reset failed. Could not update Redis.",
      });
    } finally {
      setResettingAgentId(null);
    }
  };

  const isBusy = Boolean(
    editingAgentId &&
    (savingAgentId === editingAgentId || resettingAgentId === editingAgentId),
  );
  const normalizedInitial = initialPrompt.trim();
  const normalizedDraft = draftPrompt.trim();
  const isDirty = editingAgentId
    ? normalizedDraft !== normalizedInitial
    : false;
  const canSave = Boolean(
    editingAgentId && isDirty && normalizedDraft.length > 0 && !isBusy,
  );

  const dynamicStageCards = useMemo(() => {
    if (!workflow || workflowStageKeys.length === 0) {
      return [];
    }

    return workflowStageKeys.map((stageKey, index) => {
      const stageOutput = getStageOutput(workflow, stageKey);
      const hasOutput = Boolean(stageOutput?.text || stageOutput?.finished_at);
      const isActive =
        workflow.status !== "completed" &&
        workflow.status !== "failed" &&
        workflow.current_stage === stageKey;
      const status: AgentCardStatus = isActive
        ? "processing"
        : hasOutput
          ? workflow.status === "completed"
            ? "monitoring"
            : "running"
          : "idle";
      const progress = Math.min(
        100,
        Math.round(((index + (hasOutput ? 1 : 0)) / workflowStageKeys.length) * 100),
      );
      const style = stageStyleDefaults[stageKey] ?? {
        emoji: "🤖",
        accentColor: "#8A9BBB",
        bgColor: "rgba(138,155,187,0.1)",
        gradient: "from-slate-500 to-slate-400",
        pipelineColor: "rgba(138,155,187,0.15)",
        pipelineText: "text-[#8A9BBB]",
        pipelineBorder: "rgba(138,155,187,0.2)",
      };

      return {
        id: stageKey,
        name: formatStageLabel(stageKey),
        role: `Workflow stage ${index + 1}`,
        status,
        currentTask: stageOutput?.text?.split(/\n/)[0] || (isActive
          ? `Running ${formatStageLabel(stageKey)}`
          : `Waiting for ${formatStageLabel(stageKey)}`),
        lastAction: stageOutput?.finished_at
          ? `Completed at ${formatDateTime(stageOutput.finished_at)}`
          : stageOutput?.started_at
            ? `Started at ${formatDateTime(stageOutput.started_at)}`
            : "No activity recorded yet",
        metric: `${progress}%`,
        metricLabel: "Progress",
        progress,
        emoji: style.emoji,
        accentColor: style.accentColor,
        bgColor: style.bgColor,
      } satisfies WorkflowAgentCard;
    });
  }, [workflow, workflowStageKeys]);

  const pipelineSteps = useMemo(
    () =>
      workflowStageKeys.map((stageKey) => {
        const style = stageStyleDefaults[stageKey] ?? {
          pipelineColor: "rgba(138,155,187,0.15)",
          pipelineText: "text-[#8A9BBB]",
          pipelineBorder: "rgba(138,155,187,0.2)",
        };
        return {
          id: stageKey,
          label: formatStageLabel(stageKey),
          color: style.pipelineColor,
          text: style.pipelineText,
          border: style.pipelineBorder,
        };
      }),
    [workflowStageKeys],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!editingAgentId) return;
      if (event.key === "Escape") closeEditor();
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        if (canSave) {
          void savePrompt();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editingAgentId, canSave, closeEditor, savePrompt]);

  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader
        title="Autonomous Agents"
        subtitle="Multi-agent remediation pipeline · Prompt tuning enabled"
      >
        <Badge variant={workflow ? "green" : "amber"}>
          ● {workflow ? workflow.status.toUpperCase() : "NO ACTIVE WORKFLOW"}
        </Badge>
        <Link
          href="/agents/workflow"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold border border-border-2 text-[#8A9BBB] hover:text-white hover:border-lerna-blue hover:bg-bg-4 transition-all duration-150"
        >
          View Detailed Workflow
        </Link>
      </PageHeader>

      {notice && (
        <div
          className={clsx(
            "rounded-lg px-3.5 py-2.5 border text-sm flex items-center gap-2",
            notice.type === "success"
              ? "text-lerna-green bg-[rgba(16,185,129,0.08)] border-[rgba(16,185,129,0.25)]"
              : "text-lerna-red bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.25)]",
          )}
        >
          {notice.type === "success" ? (
            <CircleCheckBig size={14} />
          ) : (
            <CircleAlert size={14} />
          )}
          {notice.text}
        </div>
      )}
      {error && !notice && (
        <div className="text-sm text-lerna-red bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.25)] rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Pipeline banner */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-gradient-to-r from-[rgba(59,130,246,0.08)] to-[rgba(168,85,247,0.08)] border border-border rounded-2xl px-5 py-4 flex items-center justify-between gap-4 flex-wrap shadow-[0_12px_28px_rgba(0,0,0,0.18)]"
      >
        <div>
          <div className="text-[10px] text-[#4A5B7A] font-mono tracking-widest mb-2">
            PIPELINE STATUS
          </div>
          <div className="flex items-center gap-0 flex-wrap">
            {pipelineSteps.map((step, i) => (
              <div key={step.id} className="flex items-center">
                <span
                  className={clsx(
                    "text-[12px] px-3 py-1.5 border font-mono font-semibold",
                    step.text,
                  )}
                  style={{
                    background: step.color,
                    borderColor: step.border,
                    borderRadius:
                      i === 0
                        ? "6px 0 0 6px"
                        : i === pipelineSteps.length - 1
                          ? "0 6px 6px 0"
                          : "0",
                  }}
                >
                  {step.label}
                </span>
                {i < pipelineSteps.length - 1 && (
                  <span className="text-[10px] text-[#4A5B7A] px-1.5">→</span>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="text-[13px] text-[#8A9BBB]">
          {workflow ? (
            <>
              Workflow{" "}
              <strong className="text-white">{workflow.workflow_id}</strong> ·
              Incident{" "}
              <strong className="text-white">{workflow.incident_id}</strong> ·
              API cost{" "}
              <strong className="text-white">{formatWorkflowApiCost(workflow)}</strong>
            </>
          ) : (
            <>
              No active workflow. Showing agent status with the last known history below.
            </>
          )}
        </div>
      </motion.div>

      {workflow && (
        <div className="bg-bg-3 border border-border rounded-2xl px-5 py-4 text-sm text-[#E8EDF5]">
          <div className="font-semibold mb-1">Live workflow attached</div>
          <div className="text-[#8A9BBB]">
            Status: <span className="text-white">{workflow.status}</span>
            {` · API cost ${formatWorkflowApiCost(workflow)}`}
            {workflow.started_at ? ` · started ${formatDateTime(workflow.started_at)}` : ""}
            {workflow.finished_at ? ` · finished ${formatDateTime(workflow.finished_at)}` : ""}
          </div>
        </div>
      )}

      {!loadingWorkflow && !workflow && workflowHistory.length === 0 && (
        <div className="bg-bg-3 border border-border rounded-2xl px-5 py-4 text-sm text-[#8A9BBB]">
          No workflows have been recorded yet.
        </div>
      )}

      {workflowHistory.length > 0 && (
        <div className="bg-bg-2 border border-border rounded-2xl px-5 py-4">
          <div className="text-[11px] text-[#4A5B7A] font-mono tracking-widest mb-3">
            RECENT WORKFLOWS
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {workflowHistory.slice(0, 6).map((item) => {
              const selected = workflow?.workflow_id === item.workflow_id;
              return (
                <button
                  key={item.workflow_id}
                  type="button"
                  onClick={() => {
                    setWorkflow(item);
                    if (typeof window !== "undefined") {
                      window.localStorage.setItem("lerna:lastWorkflowId", item.workflow_id);
                    }
                  }}
                  className={clsx(
                    "text-left rounded-xl border p-3 transition-colors",
                    selected
                      ? "border-lerna-blue bg-bg-3"
                      : "border-border bg-bg-3/50 hover:border-border-2",
                  )}
                >
                  <div className="text-sm text-white font-semibold">{item.workflow_id}</div>
                  <div className="text-[12px] text-[#8A9BBB] mt-1">{item.incident_id}</div>
                  <div className="text-[11px] text-[#4A5B7A] font-mono mt-2">
                    {item.status.toUpperCase()} · {formatDateTime(item.accepted_at)}
                  </div>
                  <div className="text-[11px] text-[#8A9BBB] font-mono mt-1">
                    API cost: {formatWorkflowApiCost(item)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {dynamicStageCards.map((agent, i) => {
          const displayStatus = agent.status;
          const status = statusConfig[displayStatus];
          const isActive = displayStatus === "processing";
          const currentTask = agent.currentTask;
          const lastAction = agent.lastAction;
          const progress = agent.progress;

          return (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, duration: 0.35 }}
              whileHover={{ y: -2 }}
              className={clsx(
                "bg-bg-2 border rounded-2xl p-6 transition-all duration-200 shadow-[0_10px_26px_rgba(0,0,0,0.2)]",
                isActive
                  ? "border-[rgba(59,130,246,0.4)]"
                  : "border-border hover:border-border-2",
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center text-xl"
                  style={{ background: agent.bgColor }}
                >
                  {agent.emoji}
                </div>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full shrink-0",
                      status.dotClass,
                    )}
                  />
                  <span className={status.textColor}>{status.label}</span>
                </div>
              </div>

              {/* Name */}
              <div className="font-bold text-[15px] mb-0.5">{agent.name}</div>
              <div className="text-[11px] text-[#4A5B7A] font-mono mb-4">
                {agent.role}
              </div>

              {/* Info rows */}
              <div className="space-y-0">
                <div className="flex justify-between py-2 border-b border-white/[0.04] text-[12px]">
                  <span className="text-[#4A5B7A]">Current Task</span>
                  <span className="font-mono text-[11px] text-right">
                    {currentTask}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-white/[0.04] text-[12px]">
                  <span className="text-[#4A5B7A]">Last Action</span>
                  <span
                    className="text-[11px] text-right"
                    style={{ color: agent.accentColor }}
                  >
                    {lastAction}
                  </span>
                </div>
                <div className="flex justify-between py-2 text-[12px]">
                  <span className="text-[#4A5B7A]">{agent.metricLabel}</span>
                  <span className="font-mono text-[11px]">{agent.metric}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-4 h-[3px] bg-bg-4 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{
                    delay: i * 0.08 + 0.3,
                    duration: 0.6,
                    ease: "easeOut",
                  }}
                  className={clsx(
                    "h-full rounded-full bg-gradient-to-r",
                    progressGradientDefaults[agent.id] ?? "from-slate-500 to-slate-400",
                  )}
                />
              </div>

              <div className="mt-4 pt-3 border-t border-white/[0.04]">
                <div className="text-[10px] text-[#4A5B7A] font-mono mb-2">
                  SYSTEM PROMPT
                </div>
                <div className="text-[12px] text-[#8A9BBB] leading-relaxed line-clamp-3 min-h-[42px] bg-bg-3/50 border border-white/[0.04] rounded-lg px-2.5 py-2">
                  {loadingPrompts
                    ? "Loading prompt..."
                    : (promptByAgent[agent.id] ??
                      defaultSystemPrompts[agent.id])}
                </div>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-[10px] text-[#4A5B7A] font-mono">
                    {promptByAgent[agent.id]
                      ? "Custom prompt"
                      : "Default prompt"}
                  </span>
                  <Button
                    variant="outline"
                    className="text-[11px] px-3 py-1.5"
                    onClick={() => openEditor(agent.id)}
                  >
                    <Edit3 size={12} />
                    Edit Prompt
                  </Button>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {editingAgentId && (
        <div className="fixed inset-0 z-[60] bg-black/55 backdrop-blur-sm flex items-center justify-center p-5">
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="w-full max-w-2xl bg-bg-2 border border-border rounded-2xl p-5 shadow-[0_24px_60px_rgba(0,0,0,0.45)]"
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="text-lg font-bold mb-1">Edit System Prompt</div>
                <div className="text-[12px] text-[#8A9BBB] font-mono">
                  {agentNameById[editingAgentId] ?? editingAgentId}
                </div>
              </div>
              <Button
                variant="ghost"
                className="px-2.5 py-1.5"
                onClick={closeEditor}
              >
                <X size={14} />
              </Button>
            </div>

            <textarea
              value={draftPrompt}
              onChange={(e) => setDraftPrompt(e.target.value)}
              rows={11}
              className="w-full bg-bg-3 border border-border-2 rounded-xl p-3.5 text-sm text-[#E8EDF5] outline-none focus:border-lerna-blue resize-y leading-relaxed font-mono"
            />
            <div className="mt-2 flex items-center justify-between text-[11px] text-[#4A5B7A] font-mono">
              <span>{draftPrompt.trim().length} chars</span>
              <span>{isDirty ? "Unsaved changes" : "No changes"}</span>
            </div>

            <div className="mt-4 flex items-center justify-between gap-2 flex-wrap border-t border-white/[0.05] pt-4">
              <Button
                variant="outline"
                onClick={resetPromptToDefault}
                disabled={
                  resettingAgentId === editingAgentId ||
                  savingAgentId === editingAgentId
                }
                className="text-lerna-amber border-lerna-amber/40 hover:border-lerna-amber"
              >
                <RotateCcw size={13} />
                {resettingAgentId === editingAgentId
                  ? "Resetting..."
                  : "Reset to default"}
              </Button>
              <div className="flex items-center gap-2 ml-auto">
                <Button variant="ghost" onClick={closeEditor}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={savePrompt}
                  className="min-w-[90px]"
                  disabled={!canSave}
                >
                  <Save size={13} />
                  {savingAgentId === editingAgentId ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
