from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from lerna_shared.detection import DetectionCheckResponse, DetectionEvidence


class BackendStatus(BaseModel):
    ok: bool
    endpoint: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    prometheus: BackendStatus
    loki: BackendStatus
    jaeger: BackendStatus
    overall_ok: bool


class ClusterMetrics(BaseModel):
    cpu_percentage: Optional[float] = None
    memory_percentage: Optional[float] = None
    cpu_available: bool = False
    memory_available: bool = False
    cpu_query: Optional[str] = None
    memory_query: Optional[str] = None
    cpu_reason: Optional[str] = None
    memory_reason: Optional[str] = None


class ClusterSummary(BaseModel):
    available: bool
    last_updated: Optional[str] = None
    reason: Optional[str] = None
    namespace_scope: Optional[str] = None
    nodes: Dict[str, Any] = {}
    deployments: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    pods: Dict[str, Any] = {}
    recent_events: List[Dict[str, Any]] = []
    metrics: ClusterMetrics = ClusterMetrics()


class AgentPromptUpdateRequest(BaseModel):
    prompt: str


class AgentPromptEntry(BaseModel):
    agent_id: str
    prompt: str


class AgentPromptsResponse(BaseModel):
    prompts: List[AgentPromptEntry]


class AgentPromptResetResponse(BaseModel):
    agent_id: str
    reset: bool


class AgentWorkflowResponse(BaseModel):
    workflow_id: str
    incident_id: str
    status: str
    accepted_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class OrchestratorChatRequest(BaseModel):
    message: str
    workflow_id: Optional[str] = None
    incident_id: Optional[str] = None


class OrchestratorChatResponse(BaseModel):
    message: str
    workflow_id: Optional[str] = None
