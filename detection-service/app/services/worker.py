from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.services.agent_client import AgentsClient
from app.services.cluster_snapshot import ClusterSnapshotService
from app.services.observability import ObservabilityService
from app.services.store import DetectionStateStore
from lerna_shared.detection import build_detection_run_result

logger = logging.getLogger(__name__)


class DetectionWorker:
    def __init__(
        self,
        obs_service: ObservabilityService,
        snapshot_service: ClusterSnapshotService,
        state_store: DetectionStateStore,
        agents_client: AgentsClient,
    ) -> None:
        self._obs_service = obs_service
        self._snapshot_service = snapshot_service
        self._state_store = state_store
        self._agents_client = agents_client
        self._task: Optional[asyncio.Task] = None
        self._last_result: Dict[str, Any] = {"status": "idle"}

    async def start(self) -> None:
        if self._task:
            return
        self._task = asyncio.create_task(self._run(), name="detection-worker")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def status(self) -> Dict[str, Any]:
        return self._last_result

    async def _run(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Detection worker tick failed", exc_info=True)
                self._last_result = {"status": "error", "reason": str(exc)}
            await asyncio.sleep(settings.poll_interval_seconds)

    async def _tick(self) -> None:
        execution_mode = await self._state_store.get_agents_execution_mode()
        if execution_mode == "paused":
            # Still observe signals for the operator UI; never auto-trigger agents or retries.
            snapshot = await self._snapshot_service.get_snapshot()
            if not snapshot.get("available"):
                reason = snapshot.get("reason")
                logger.warning("Detection: cluster snapshot unavailable (%s)", reason)
                self._last_result = {"status": "degraded", "reason": reason, "execution_mode": execution_mode}
                return
            loki_raw = await self._obs_service.query_logs(query=settings.log_query, limit=settings.log_limit)
            result = build_detection_run_result(loki_raw, snapshot)
            self._last_result = {
                "status": "paused",
                "execution_mode": execution_mode,
                "checked_at": result.check.checked_at,
                "has_error": result.check.has_error,
                "summary": result.check.summary,
                "incident_id": result.incident.incident_id if result.incident else None,
            }
            return

        await self._process_retries()
        snapshot = await self._snapshot_service.get_snapshot()
        if not snapshot.get("available"):
            reason = snapshot.get("reason")
            logger.warning("Detection: cluster snapshot unavailable (%s)", reason)
            self._last_result = {"status": "degraded", "reason": reason}
            return

        loki_raw = await self._obs_service.query_logs(query=settings.log_query, limit=settings.log_limit)
        result = build_detection_run_result(loki_raw, snapshot)
        self._last_result = {
            "status": "ok",
            "checked_at": result.check.checked_at,
            "has_error": result.check.has_error,
            "summary": result.check.summary,
            "incident_id": result.incident.incident_id if result.incident else None,
        }
        if not result.incident:
            return

        payload = result.incident.model_dump()
        summary_hash = hashlib.sha1(
            f"{result.incident.summary}:{result.incident.dominant_signature}".encode("utf-8")
        ).hexdigest()
        should_emit = await self._state_store.should_emit(result.incident.fingerprint, summary_hash)
        if not should_emit:
            logger.debug(
                "Detection: dedupe suppressing repeat fingerprint=%s",
                result.incident.fingerprint,
            )
            return

        inc = result.incident
        logger.info(
            "Detection: incident found id=%s class=%s service=%s namespace=%s severity=%s errors=%s",
            inc.incident_id,
            inc.incident_class,
            inc.service,
            inc.namespace,
            inc.severity,
            result.check.summary.get("error_count"),
        )

        try:
            response = await self._agents_client.trigger_incident(payload)
            await self._state_store.mark_emitted(result.incident.fingerprint, summary_hash, response.get("status", "accepted"))
            self._last_result["workflow_id"] = response.get("workflow_id")
            logger.info(
                "Detection: sent to agents incident_id=%s workflow_id=%s status=%s",
                result.incident.incident_id,
                response.get("workflow_id"),
                response.get("status"),
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            try:
                body = exc.response.json() if exc.response is not None else {}
            except Exception:  # pylint: disable=broad-except
                body = {}

            error_code = body.get("detail", {}).get("error")
            is_budget_reached = status_code == 429 and error_code == "DAILY_COST_LIMIT_REACHED"
            if is_budget_reached:
                logger.warning(
                    "Detection: daily budget reached; not retrying incident_id=%s spent=%s max=%s",
                    result.incident.incident_id,
                    body.get("detail", {}).get("spent_today"),
                    body.get("detail", {}).get("max_daily_cost"),
                )
                await self._state_store.mark_emitted(result.incident.fingerprint, summary_hash, "budget_exceeded")
                self._last_result = {"status": "budget_exceeded", "incident_id": result.incident.incident_id, "error": error_code}
                return

            logger.warning("Detection: failed to trigger agents workflow (HTTP %s)", status_code)
            await self._state_store.mark_emitted(result.incident.fingerprint, summary_hash, "queued")
            await self._state_store.enqueue_retry(result.incident.incident_id, payload, str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to trigger agents workflow", exc_info=True)
            await self._state_store.mark_emitted(result.incident.fingerprint, summary_hash, "queued")
            await self._state_store.enqueue_retry(result.incident.incident_id, payload, str(exc))

    async def _process_retries(self) -> None:
        retries = await self._state_store.due_retries()
        for item in retries:
            try:
                await self._agents_client.trigger_incident(item["payload"])
                await self._state_store.clear_retry(item["incident_id"])
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                try:
                    body = exc.response.json() if exc.response is not None else {}
                except Exception:  # pylint: disable=broad-except
                    body = {}

                error_code = body.get("detail", {}).get("error")
                is_budget_reached = status_code == 429 and error_code == "DAILY_COST_LIMIT_REACHED"
                if is_budget_reached:
                    await self._state_store.clear_retry(item["incident_id"])
                    logger.warning(
                        "Detection: daily budget reached; clearing retry for incident_id=%s",
                        item["incident_id"],
                    )
                    continue

                logger.warning("Retry handoff failed for %s (HTTP %s)", item["incident_id"], status_code, exc_info=True)
            except Exception:  # pylint: disable=broad-except
                logger.warning("Retry handoff failed for %s", item["incident_id"], exc_info=True)
