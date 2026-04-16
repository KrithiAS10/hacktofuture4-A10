"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ChevronDown, Wrench } from "lucide-react";
import { Badge, PageHeader } from "@/components/ui";
import {
  fetchAgentWorkflow,
  fetchAgentWorkflows,
  fetchLatestAgentWorkflow,
  type AgentWorkflowResponse,
} from "@/lib/observation-api";

type ToolCall = {
  id?: string;
  name?: string;
  arguments?: string;
  result?: string;
};

type StageOutput = {
  text?: string;
  tool_calls?: ToolCall[];
  started_at?: string;
  finished_at?: string;
};

function getWorkflowResult(workflow: AgentWorkflowResponse | null): Record<string, unknown> | null {
  if (!workflow?.result || typeof workflow.result !== "object") {
    return null;
  }
  return workflow.result as Record<string, unknown>;
}

function formatWorkflowCost(cost?: number | null) {
  if (typeof cost !== "number" || Number.isNaN(cost)) {
    return "Cost unavailable";
  }
  return `$${cost.toFixed(2)}`;
}

function getStageOutput(
  workflow: AgentWorkflowResponse | null,
  key: string,
): StageOutput | null {
  const result = getWorkflowResult(workflow);
  if (!result) return null;
  const value = result[key];
  if (!value || typeof value !== "object") return null;
  return value as StageOutput;
}

function formatStageLabel(stageKey: string) {
  return stageKey
    .split(/[_-]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getWorkflowStages(workflow: AgentWorkflowResponse | null) {
  const result = getWorkflowResult(workflow);
  if (!result) return [];
  return Object.keys(result).filter((key) => {
    const value = result[key];
    return value && typeof value === "object";
  });
}

export default function AgentWorkflowDetailPage() {
  const [workflow, setWorkflow] = useState<AgentWorkflowResponse | null>(null);
  const [workflowHistory, setWorkflowHistory] = useState<AgentWorkflowResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: number | null = null;

    const load = async () => {
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
          history.find((item) => item.workflow_id === storedWorkflowId) ?? null;

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
        setError(null);
      } catch {
        if (!active) return;
        setWorkflow(null);
        setWorkflowHistory([]);
        setError("Unable to load workflow details right now.");
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    timer = window.setInterval(() => {
      void load();
    }, 2500);

    return () => {
      active = false;
      if (timer) window.clearInterval(timer);
    };
  }, []);

  const stageCompletion = useMemo(() => {
    const completed = new Set<string>();
    for (const stage of getWorkflowStages(workflow)) {
      const output = getStageOutput(workflow, stage);
      if (output?.finished_at || output?.text) {
        completed.add(stage);
      }
    }
    return completed;
  }, [workflow]);

  const workflowStages = useMemo(() => getWorkflowStages(workflow), [workflow]);

  const activeStage = useMemo(() => {
    if (!workflow || workflow.status === "completed" || workflow.status === "failed") {
      return null;
    }
    if (workflow.current_stage) {
      return workflow.current_stage;
    }
    for (const stage of workflowStages) {
      if (!stageCompletion.has(stage)) return stage;
    }
    return null;
  }, [workflow, stageCompletion, workflowStages]);

  return (
    <div className="p-7 flex flex-col gap-6">
      <div className="flex items-center gap-3 text-[12px] text-[#8A9BBB]">
        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
        >
          <ArrowLeft size={13} />
          Back to Agents
        </Link>
      </div>

      <PageHeader
        title="Workflow History"
        subtitle="Browse recent runs and inspect each workflow in detail. Refreshes every 2.5 seconds."
      >
        <Badge
          variant={
            workflow?.status === "completed"
              ? "green"
              : workflow?.status === "failed"
                ? "red"
                : "blue"
          }
        >
          {workflow ? workflow.status.toUpperCase() : "LOADING"}
        </Badge>
      </PageHeader>

      {loading && (
        <div className="rounded-xl border border-border bg-bg-2 p-4 text-sm text-[#8A9BBB]">
          Loading workflow details...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.08)] p-4 text-sm text-lerna-red">
          {error}
        </div>
      )}

      {!loading && !error && workflowHistory.length === 0 && (
        <div className="rounded-xl border border-border bg-bg-2 p-4 text-sm text-[#8A9BBB]">
          No workflows have been recorded yet.
        </div>
      )}

      {workflowHistory.length > 0 && (
        <div className="rounded-2xl border border-border bg-bg-2 p-5">
          <div className="text-[11px] text-[#5c6d8c] font-mono tracking-wider mb-3">
            RECENT WORKFLOWS
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {workflowHistory.map((item) => {
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
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    selected
                      ? "border-lerna-blue bg-bg-3"
                      : "border-border bg-bg-3/50 hover:border-border-2"
                  }`}
                >
                  <div className="text-sm font-semibold text-white">{item.workflow_id}</div>
                  <div className="text-[12px] text-[#8A9BBB] mt-1">{item.incident_id}</div>
                  <div className="text-[11px] text-[#4A5B7A] font-mono mt-2">
                    {item.status.toUpperCase()} · {item.accepted_at}
                  </div>
                  <div className="text-[11px] text-[#8A9BBB] font-mono mt-1">
                    Cost: {formatWorkflowCost(item.cost)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {workflow && (
        <>
          <div className="rounded-2xl border border-border bg-bg-2 p-5">
            <div className="text-[11px] text-[#5c6d8c] font-mono tracking-wider mb-2">
              INCIDENT CONTEXT
            </div>
            <div className="text-sm text-[#E8EDF5]">
              Incident <strong>{workflow.incident_id}</strong> is being processed by
              workflow <strong>{workflow.workflow_id}</strong>.
            </div>
            <div className="text-[12px] text-[#8A9BBB] mt-2">
              Cost: {formatWorkflowCost(workflow.cost)}
              {" · "}
              Accepted: {workflow.accepted_at}
              {workflow.started_at ? ` · Started: ${workflow.started_at}` : ""}
              {workflow.finished_at ? ` · Finished: ${workflow.finished_at}` : ""}
              {activeStage ? ` · Current stage: ${activeStage}` : ""}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {workflowStages.map((stageKey) => {
              const output = getStageOutput(workflow, stageKey);
              const isCompleted = stageCompletion.has(stageKey);
              const isActive = activeStage === stageKey;
              const statusLabel = isCompleted
                ? "Completed"
                : isActive
                  ? "In Progress"
                  : "Pending";

              return (
                <div
                  key={stageKey}
                  className="rounded-2xl border border-border bg-bg-2 p-5"
                >
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div>
                      <div className="text-[11px] text-[#5c6d8c] font-mono tracking-wider">
                        STEP
                      </div>
                      <div className="text-lg font-semibold">{formatStageLabel(stageKey)}</div>
                    </div>
                    <Badge
                      variant={
                        isCompleted ? "green" : isActive ? "blue" : "amber"
                      }
                    >
                      {statusLabel}
                    </Badge>
                  </div>

                  <div className="text-[12px] text-[#8A9BBB] mb-3">
                    {output?.started_at ? `Started: ${output.started_at}` : "Not started yet"}
                    {output?.finished_at ? ` · Finished: ${output.finished_at}` : ""}
                  </div>

                  <div className="rounded-xl border border-border bg-bg-3 p-3 mb-3">
                    <div className="text-[11px] text-[#5c6d8c] font-mono tracking-wider mb-2">
                      AGENT RESPONSE
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-[12px] text-[#E8EDF5] font-mono">
                      {output?.text?.trim() || "No response yet."}
                    </pre>
                  </div>

                  <div className="rounded-xl border border-border bg-bg-3 p-3">
                    <div className="text-[11px] text-[#5c6d8c] font-mono tracking-wider mb-2 flex items-center gap-1.5">
                      <Wrench size={13} />
                      TOOL CALLS
                    </div>

                    {output?.tool_calls && output.tool_calls.length > 0 ? (
                      <div className="space-y-2">
                        {output.tool_calls.map((call, index) => (
                          <details
                            key={`${call.id ?? call.name ?? "tool"}-${index}`}
                            className="rounded-lg border border-border bg-bg-2"
                          >
                            <summary className="cursor-pointer list-none px-3 py-2 text-[12px] text-[#E8EDF5] flex items-center justify-between">
                              <span className="font-mono">
                                {call.name || "unknown_tool"}
                              </span>
                              <ChevronDown size={14} className="text-[#8A9BBB]" />
                            </summary>
                            <div className="px-3 pb-3 border-t border-border">
                              <div className="mt-2 text-[11px] text-[#5c6d8c] font-mono">
                                Arguments
                              </div>
                              <pre className="whitespace-pre-wrap break-words text-[12px] text-[#E8EDF5] font-mono mt-1">
                                {call.arguments || "(no arguments)"}
                              </pre>
                              <div className="mt-3 text-[11px] text-[#5c6d8c] font-mono">
                                Result
                              </div>
                              <pre className="whitespace-pre-wrap break-words text-[12px] text-[#E8EDF5] font-mono mt-1">
                                {call.result || "(no result payload captured)"}
                              </pre>
                            </div>
                          </details>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[12px] text-[#8A9BBB]">
                        No tool calls recorded for this step yet.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
