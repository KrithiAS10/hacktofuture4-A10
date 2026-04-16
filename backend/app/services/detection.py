from __future__ import annotations

from app.models import DetectionCheckResponse
from app.services.observability import ObservabilityService
from lerna_shared.detection import build_detection_run_result


class DetectionService:
    def __init__(self, obs_service: ObservabilityService) -> None:
        self._obs = obs_service

    async def run_check(
        self,
        cluster_snapshot,
        log_query: str = "{}",
        log_limit: int = 150,
    ) -> DetectionCheckResponse:
        loki_raw = await self._obs.query_logs(query=log_query, limit=log_limit)
        return build_detection_run_result(loki_raw, cluster_snapshot).check
