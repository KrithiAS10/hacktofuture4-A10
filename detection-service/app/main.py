from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.services.agent_client import AgentsClient
from app.services.cluster_snapshot import ClusterSnapshotService
from app.services.observability import ObservabilityService
from app.services.store import DetectionStateStore
from app.services.worker import DetectionWorker

_pkg_log = logging.getLogger("app")
_pkg_log.setLevel(logging.INFO)
if not _pkg_log.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _pkg_log.addHandler(_h)
    _pkg_log.propagate = False

obs_service = ObservabilityService()
snapshot_service = ClusterSnapshotService()
state_store = DetectionStateStore()
agents_client = AgentsClient()
worker = DetectionWorker(obs_service, snapshot_service, state_store, agents_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()
        await obs_service.close()
        await agents_client.close()
        await state_store.close()


app = FastAPI(title="Lerna Detection Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/status")
async def status():
    return worker.status()
