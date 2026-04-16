from fastapi.testclient import TestClient

from lerna_shared.detection import AgentTriggerResponse
from service_main import app, workflow_store


def test_post_incidents_returns_trigger_response(monkeypatch):
    payload = {
        "incident_id": "inc-123",
        "fingerprint": "fp-123",
        "detected_at": "2026-04-16T00:00:00Z",
        "service": "payment-service",
        "namespace": "lerna",
        "severity": "error",
        "summary": "application-error detected for payment-service",
        "evidence": [],
        "cluster_snapshot": None,
        "incident_class": "application-error",
        "dominant_signature": "fatal timeout",
        "correlation": {},
        "cost": 5.0,
    }

    async def fake_accept_incident(_payload, _store):
        return AgentTriggerResponse(accepted=True, workflow_id="wf-123", status="accepted")

    monkeypatch.setattr("service_main.accept_incident", fake_accept_incident)

    with TestClient(app) as client:
        response = client.post("/incidents", json=payload)

    assert response.status_code == 200
    assert response.json()["workflow_id"] == "wf-123"


def test_get_workflow_reads_store(monkeypatch):
    async def fake_get_workflow(_workflow_id):
        return {"workflow_id": "wf-123", "status": "completed"}

    monkeypatch.setattr(workflow_store, "get_workflow", fake_get_workflow)

    with TestClient(app) as client:
        response = client.get("/workflows/wf-123")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_post_incidents_can_use_langgraph_engine(monkeypatch):
    payload = {
        "incident_id": "inc-456",
        "fingerprint": "fp-456",
        "detected_at": "2026-04-16T00:00:00Z",
        "service": "checkout-service",
        "namespace": "lerna",
        "severity": "error",
        "summary": "application-error detected for checkout-service",
        "evidence": [],
        "cluster_snapshot": None,
        "incident_class": "application-error",
        "dominant_signature": "upstream timeout",
        "correlation": {},
        "cost": 5.0,
    }

    async def fake_accept_langgraph_incident(_payload, _store):
        return AgentTriggerResponse(accepted=True, workflow_id="lg-123", status="accepted")

    monkeypatch.setattr("service_main._USE_LANGGRAPH_ENGINE", True)
    monkeypatch.setattr("service_main.accept_langgraph_incident", fake_accept_langgraph_incident)

    with TestClient(app) as client:
        response = client.post("/incidents", json=payload)

    assert response.status_code == 200
    assert response.json()["workflow_id"] == "lg-123"


def test_post_incidents_rejects_when_daily_cost_limit_reached(monkeypatch):
    payload = {
        "incident_id": "inc-999",
        "fingerprint": "fp-999",
        "detected_at": "2026-04-16T00:00:00Z",
        "service": "payment-service",
        "namespace": "lerna",
        "severity": "error",
        "summary": "application-error detected for payment-service",
        "evidence": [],
        "cluster_snapshot": None,
        "incident_class": "application-error",
        "dominant_signature": "fatal timeout",
        "correlation": {},
        "cost": 5.0,
    }

    async def fake_get_workflow_for_incident(_incident_id):
        return None

    async def fake_get_max_daily_cost():
        return 10.0

    async def fake_get_daily_spend(day=None):  # pylint: disable=unused-argument
        return 10.0

    monkeypatch.setattr(workflow_store, "get_workflow_for_incident", fake_get_workflow_for_incident)
    monkeypatch.setattr(workflow_store, "get_max_daily_cost", fake_get_max_daily_cost)
    monkeypatch.setattr(workflow_store, "get_daily_spend", fake_get_daily_spend)

    with TestClient(app) as client:
        response = client.post("/incidents", json=payload)

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "DAILY_COST_LIMIT_REACHED"
