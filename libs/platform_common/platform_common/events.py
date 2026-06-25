from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    event_version: int
    occurred_at: str
    producer: str
    correlation_id: str
    idempotency_key: str | None
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        producer: str,
        correlation_id: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        event_version: int = 1,
    ) -> "EventEnvelope":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            event_version=event_version,
            occurred_at=datetime.now(UTC).isoformat(),
            producer=producer,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            payload=payload,
        )

    def to_stream_fields(self) -> dict[str, str]:
        return {"event": json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)}


class RedisStreamPublisher:
    def __init__(self, redis: Redis, stream_name: str) -> None:
        self.redis = redis
        self.stream_name = stream_name

    async def publish(self, envelope: EventEnvelope) -> str:
        stream_id = await self.redis.xadd(self.stream_name, envelope.to_stream_fields())
        if isinstance(stream_id, bytes):
            return stream_id.decode("utf-8")
        return str(stream_id)

