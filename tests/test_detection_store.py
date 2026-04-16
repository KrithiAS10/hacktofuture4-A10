import json
import importlib.util
from pathlib import Path
import sys
import asyncio

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "detection-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

MODULE_PATH = Path(__file__).resolve().parents[1] / "detection-service" / "app" / "services" / "store.py"
SPEC = importlib.util.spec_from_file_location("detection_service_store", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
DetectionStateStore = MODULE.DetectionStateStore
MODULE.settings.retry_delay_seconds = 0


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.values = {}
        self.sorted_sets = {}

    async def aclose(self):
        return None

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def hset(self, key, mapping=None):
        self.hashes.setdefault(key, {}).update(mapping or {})

    async def expire(self, key, _ttl):
        return 1

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    async def zadd(self, key, mapping):
        self.sorted_sets.setdefault(key, {}).update(mapping)

    async def zrangebyscore(self, key, min=0, max=0):
        items = self.sorted_sets.get(key, {})
        return [member for member, score in items.items() if min <= score <= max]

    async def zrem(self, key, member):
        self.sorted_sets.get(key, {}).pop(member, None)

    async def delete(self, key):
        self.hashes.pop(key, None)


def test_detection_state_store_suppresses_matching_summary_hashes():
    store = DetectionStateStore()
    store._redis = FakeRedis()

    assert asyncio.run(store.should_emit("fp-1", "hash-1")) is True

    asyncio.run(store.mark_emitted("fp-1", "hash-1", "accepted"))

    assert asyncio.run(store.should_emit("fp-1", "hash-1")) is False
    assert asyncio.run(store.should_emit("fp-1", "hash-2")) is True


def test_detection_state_store_round_trips_retry_items():
    store = DetectionStateStore()
    fake_redis = FakeRedis()
    store._redis = fake_redis

    payload = {"incident_id": "inc-1", "summary": "payment crashloop"}
    asyncio.run(store.enqueue_retry("inc-1", payload, "agents unavailable"))
    retries = asyncio.run(store.due_retries())

    assert len(retries) == 1
    assert retries[0]["payload"] == payload
    assert json.loads(fake_redis.hashes["lerna:detection:retry:inc-1"]["payload"]) == payload

    asyncio.run(store.clear_retry("inc-1"))
    assert asyncio.run(store.due_retries()) == []
